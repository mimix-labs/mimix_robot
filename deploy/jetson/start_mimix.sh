#!/usr/bin/env bash
# Orquesta Mimix en una Jetson: Web, visión nativa, Chromium y voz opcional.

set -euo pipefail

JETSON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$JETSON_DIR/../.." && pwd)"
ENV_FILE="$ROBOT_DIR/.env"
LOG_DIR="$ROBOT_DIR/logs/jetson"
START_VOICE=false
START_BROWSER=true
PIDS=()

usage() {
  cat <<'EOF'
Uso: bash deploy/jetson/start_mimix.sh [--voice] [--no-browser]

  --voice       Inicia también el guía Wall-E.
  --no-browser  No abre Chromium; útil para diagnóstico remoto.
EOF
}

for argument in "$@"; do
  case "$argument" in
    --voice) START_VOICE=true ;;
    --no-browser) START_BROWSER=false ;;
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

start_process() {
  local name="$1"
  shift
  "$@" >"$LOG_DIR/$name.log" 2>&1 &
  PIDS+=("$!")
  echo "Iniciado $name (registro: $LOG_DIR/$name.log)"
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
  local attempts=50

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

  echo "La visión no publicó frames nativos a tiempo. Revisa $LOG_DIR/vision.log." >&2
  exit 1
}

run_web_server() {
  cd "$WEB_DIR"
  exec npm run start --prefix server
}

run_web_client() {
  cd "$WEB_DIR"
  exec npm run dev --prefix client -- --host 0.0.0.0
}

start_process "web-server" run_web_server
wait_for_url "http://127.0.0.1:4000/api/health" "Mimix Web backend"

start_process "web-client" run_web_client
wait_for_url "http://127.0.0.1:5173/" "Mimix Web client"

start_process "vision" bash "$ROBOT_DIR/services/vision/start_vision.sh"
wait_for_native_vision

if [[ "$START_BROWSER" == true ]]; then
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "No hay sesión gráfica (DISPLAY). Chromium no se abrirá; usa --no-browser para este modo." >&2
  else
    CHROMIUM_BIN="${MIMIX_CHROMIUM_BIN:-chromium}"
    CHROMIUM_PROFILE="${MIMIX_CHROMIUM_PROFILE_DIR:-/tmp/mimix-chromium}"
    if ! command -v "$CHROMIUM_BIN" >/dev/null 2>&1; then
      echo "No se encontró $CHROMIUM_BIN. Define MIMIX_CHROMIUM_BIN en $ENV_FILE." >&2
      exit 1
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
      "http://127.0.0.1:5173/?vision=robot"
  fi
fi

if [[ "$START_VOICE" == true ]]; then
  start_process "voice" bash "$ROBOT_DIR/services/speech_service/start_walle.sh"
fi

echo "Mimix Jetson está listo. Presiona Ctrl+C para detener los procesos iniciados."
wait
