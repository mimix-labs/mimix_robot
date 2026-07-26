#!/usr/bin/env bash
# Orquesta Mimix en una Jetson: Web, visión, ROS y voz.

set -euo pipefail

JETSON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$JETSON_DIR/../.." && pwd)"
ENV_FILE="$ROBOT_DIR/.env"
LOG_DIR="$ROBOT_DIR/logs/jetson"
START_VOICE=false
START_ROS=false
START_BROWSER=true
PHYSICAL_MODE=false
SKIP_ROS_BUILD=false
VISION_READY=false
PIDS=()

usage() {
  cat <<'EOF'
Uso: bash deploy/jetson/start_mimix.sh [--voice] [--ros] [--physical] [--no-browser] [--skip-ros-build]

  --voice           Inicia el guía Wall-E junto con el stack (uso excepcional).
  --ros             Inicia ROS en modo seguro (dry_run=true, desarmado).
  --physical        Inicia Web, visión y ROS físico; no abre ElevenLabs.
  --no-browser      No abre Chromium; útil para diagnóstico remoto.
  --skip-ros-build  No reconstruye el workspace ROS antes de iniciarlo.

Para preparar el robot sin abrir una sesión de ElevenLabs:
  bash deploy/jetson/start_mimix.sh --physical

Para abrir voz solo al comenzar la conversación:
  bash deploy/jetson/start_voice.sh
EOF
}

for argument in "$@"; do
  case "$argument" in
    --voice) START_VOICE=true ;;
    --ros) START_ROS=true ;;
    --physical)
      START_ROS=true
      PHYSICAL_MODE=true
      ;;
    --no-browser) START_BROWSER=false ;;
    --skip-ros-build) SKIP_ROS_BUILD=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Opción no reconocida: $argument" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Falta $ENV_FILE. Copia .env.example a .env y configura la Jetson." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

WEB_DIR="${MIMIX_WEB_DIR:-$ROBOT_DIR/../mimix_web}"
if [[ "$WEB_DIR" != /* ]]; then
  WEB_DIR="$ROBOT_DIR/$WEB_DIR"
fi

if [[ ! -f "$WEB_DIR/package.json" ]]; then
  echo "No se encontró mimix_web en $WEB_DIR. Define MIMIX_WEB_DIR en $ENV_FILE." >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

ROS_WORKSPACE="$ROBOT_DIR/ros_ws"
ROS_SETUP="/opt/ros/jazzy/setup.bash"
WEB_URL="${MIMIX_WEB_URL:-http://127.0.0.1:4000}"
SERIAL_PORT="${MIMIX_SERIAL_PORT:-}"
SERIAL_BAUD="${MIMIX_SERIAL_BAUD:-115200}"

discover_esp32_serial_port() {
  local candidate
  local -a matches=()

  for candidate in /dev/serial/by-id/*Espressif*; do
    [[ -e "$candidate" ]] || continue
    matches+=("$candidate")
  done

  if (( ${#matches[@]} == 1 )); then
    printf '%s\n' "${matches[0]}"
    return 0
  fi

  return 1
}

prepare_local_display() {
  if [[ -n "${DISPLAY:-}" || ! -S /tmp/.X11-unix/X0 ]]; then
    return
  fi

  export DISPLAY=:0
  echo "DISPLAY no estaba definido; se usará el escritorio local :0."
}

start_process() {
  local name="$1"
  shift
  "$@" >"$LOG_DIR/$name.log" 2>&1 &
  PIDS+=("$!")
  echo "Iniciado $name (registro: $LOG_DIR/$name.log)"
}

ensure_last_process_is_running() {
  local name="$1"
  local pid="${PIDS[${#PIDS[@]} - 1]}"

  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "El proceso $name terminó al iniciar. Revisa $LOG_DIR/$name.log." >&2
    tail -n 30 "$LOG_DIR/$name.log" >&2 || true
    exit 1
  fi
}

stop_processes() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}

trap stop_processes EXIT INT TERM

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-50}"

  while (( attempts > 0 )); do
    if curl --silent --fail "$url" >/dev/null 2>&1; then
      return
    fi
    sleep 0.2
    attempts=$((attempts - 1))
  done

  echo "No respondió $label en $url. Revisa $LOG_DIR." >&2
  exit 1
}

ensure_port_is_free() {
  local port="$1"

  if command -v fuser >/dev/null 2>&1; then
    if fuser -s "${port}/tcp"; then
      echo "El puerto local ${port} ya está en uso. Cierra el ROS antiguo antes de continuar:" >&2
      echo "  fuser -v ${port}/tcp" >&2
      exit 1
    fi
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    if ss -ltnH "sport = :${port}" | grep -q .; then
      echo "El puerto local ${port} ya está en uso. Cierra el ROS antiguo antes de continuar." >&2
      exit 1
    fi
    return
  fi

  echo "No se encontró fuser ni ss para comprobar el puerto ${port}." >&2
  exit 1
}

validate_ros_configuration() {
  if [[ ! -f "$ROS_SETUP" ]]; then
    echo "No se encontró ROS Jazzy en $ROS_SETUP." >&2
    exit 1
  fi

  if [[ ! -d "$ROS_WORKSPACE/src" ]]; then
    echo "No se encontró el workspace ROS en $ROS_WORKSPACE." >&2
    exit 1
  fi

  if [[ "$PHYSICAL_MODE" == true ]]; then
    if [[ -z "$SERIAL_PORT" ]]; then
      if SERIAL_PORT="$(discover_esp32_serial_port)"; then
        echo "ESP32-C3 detectada automáticamente en $SERIAL_PORT"
      else
        echo "No se encontró una única ESP32-C3 en /dev/serial/by-id/." >&2
        echo "Conecta la C3 o define MIMIX_SERIAL_PORT en $ENV_FILE." >&2
        exit 1
      fi
    fi
    if [[ ! -e "$SERIAL_PORT" ]]; then
      echo "No existe el puerto ESP32 configurado: $SERIAL_PORT" >&2
      exit 1
    fi
  fi
}

source_ros_setup() {
  local setup_file="$1"
  local setup_status=0

  # Los scripts de entorno de ROS Jazzy consultan algunas variables opcionales
  # antes de inicializarlas. El lanzador usa `set -u`, por lo que se desactiva
  # solo mientras se carga cada script de ROS.
  set +u
  # shellcheck disable=SC1090
  source "$setup_file" || setup_status=$?
  set -u
  return "$setup_status"
}

build_ros_workspace() {
  source_ros_setup "$ROS_SETUP"
  cd "$ROS_WORKSPACE"
  colcon build --symlink-install
}

wait_for_native_vision() {
  local attempts=100
  local status

  while (( attempts > 0 )); do
    status="$(curl --silent --fail http://127.0.0.1:4000/api/vision/status 2>/dev/null || true)"
    if [[ "$status" == *'"source":"jetson-native"'* ]]; then
      return
    fi
    sleep 0.2
    attempts=$((attempts - 1))
  done

  echo "Aviso: la visión no publicó frames nativos. Se continuará sin bloquear voz ni ROS." >&2
  echo "Revisa $LOG_DIR/vision.log para corregir cámara o MediaPipe." >&2
  return 1
}

run_web_server() {
  cd "$WEB_DIR"
  exec npm run start --prefix server
}

run_web_client() {
  cd "$WEB_DIR"
  exec npm run dev --prefix client -- --host 0.0.0.0
}

run_ros() {
  local dry_run=true
  local armed=false
  local -a launch_args

  if [[ "$PHYSICAL_MODE" == true ]]; then
    dry_run=false
    armed=true
  fi

  source_ros_setup "$ROS_SETUP"
  source_ros_setup "$ROS_WORKSPACE/install/setup.bash"
  launch_args=(
    "web_url:=$WEB_URL"
    "serial_port:=$SERIAL_PORT"
    "serial_baud:=$SERIAL_BAUD"
    "dry_run:=$dry_run"
    "armed:=$armed"
  )
  if [[ -n "${MIMIX_ROBOT_BRIDGE_TOKEN:-}" ]]; then
    launch_args+=("bridge_token:=$MIMIX_ROBOT_BRIDGE_TOKEN")
  fi
  exec ros2 launch mimix_bringup robot.launch.py "${launch_args[@]}"
}

start_process "web-server" run_web_server
wait_for_url "http://127.0.0.1:4000/api/health" "Mimix Web backend"

start_process "web-client" run_web_client
wait_for_url "http://127.0.0.1:5173/" "Mimix Web client"

start_process "vision" bash "$ROBOT_DIR/services/vision/start_vision.sh"
ensure_last_process_is_running "vision"
if wait_for_native_vision; then
  VISION_READY=true
fi

if [[ "$START_BROWSER" == true ]]; then
  prepare_local_display
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "No hay sesión gráfica (DISPLAY). Chromium no se abrirá; usa --no-browser para este modo." >&2
  else
    CHROMIUM_BIN="${MIMIX_CHROMIUM_BIN:-chromium}"
    CHROMIUM_PROFILE="${MIMIX_CHROMIUM_PROFILE_DIR:-/tmp/mimix-chromium}"
    if ! command -v "$CHROMIUM_BIN" >/dev/null 2>&1; then
      echo "No se encontró $CHROMIUM_BIN. Define MIMIX_CHROMIUM_BIN en $ENV_FILE." >&2
      exit 1
    fi
    BROWSER_URL="http://127.0.0.1:5173/"
    # En la demostración física el navegador se conecta al canal nativo desde
    # el inicio. Si la cámara tarda en enumerarse, EventSource y MJPEG se
    # reconectan cuando el supervisor de visión logra abrirla.
    if [[ "$VISION_READY" == true || "$PHYSICAL_MODE" == true ]]; then
      BROWSER_URL+="?vision=robot"
    fi
    start_process "chromium" "$CHROMIUM_BIN" \
      --user-data-dir="$CHROMIUM_PROFILE" \
      --use-gl=angle \
      --use-angle=vulkan \
      --disable-gpu-sandbox \
      --ignore-gpu-blocklist \
      --enable-gpu-rasterization \
      --no-first-run \
      --no-default-browser-check \
      "$BROWSER_URL"
  fi
fi

if [[ "$START_ROS" == true ]]; then
  validate_ros_configuration
  ensure_port_is_free 8092
  if [[ "$SKIP_ROS_BUILD" == false ]]; then
    echo "Reconstruyendo ROS..."
    build_ros_workspace
  fi
  start_process "ros" run_ros
  wait_for_url "http://127.0.0.1:8092/health" "puente de gestos ROS" 300
fi

if [[ "$START_VOICE" == true ]]; then
  start_process "voice" bash "$ROBOT_DIR/services/speech_service/start_walle.sh"
  ensure_last_process_is_running "voice"
fi

if [[ "$PHYSICAL_MODE" == true ]]; then
  echo "Mimix está listo: Web, visión y gestos físicos activos; la voz está detenida."
  echo "Cuando vayas a conversar, ejecuta: bash deploy/jetson/start_voice.sh"
elif [[ "$START_ROS" == true ]]; then
  echo "Mimix está listo: ROS activo en simulación segura (dry_run=true, desarmado)."
else
  echo "Mimix Jetson está listo. Presiona Ctrl+C para detener los procesos iniciados."
fi
wait
