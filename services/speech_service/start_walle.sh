#!/usr/bin/env bash
# Inicia el guía Wall-E con la configuración local de la Jetson.

set -euo pipefail

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$SERVICE_DIR/../.." && pwd)"
ENV_FILE="$ROBOT_DIR/.env"
PYTHON_BIN="$SERVICE_DIR/.venv/bin/python"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Falta $ENV_FILE. Copia .env.example a .env y configura ElevenLabs." >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Falta el entorno de voz. Ejecuta: cd $SERVICE_DIR && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

configure_pulse_device() {
  local device_type="$1"
  local device_name="$2"
  local setter="$3"

  [[ -z "$device_name" ]] && return

  if ! command -v pactl >/dev/null 2>&1; then
    echo "Aviso: pactl no está disponible; se usarán los dispositivos de audio actuales." >&2
    return
  fi

  if ! pactl list short "$device_type" | awk '{print $2}' | grep -Fxq "$device_name"; then
    echo "No se encontró $device_type configurado: $device_name" >&2
    exit 1
  fi

  pactl "$setter" "$device_name"
}

configure_pulse_device "sources" "${MIMIX_AUDIO_INPUT_SOURCE:-}" "set-default-source"
configure_pulse_device "sinks" "${MIMIX_AUDIO_OUTPUT_SINK:-}" "set-default-sink"

echo "Iniciando Wall-E. Presiona Ctrl+C para detenerlo."
exec "$PYTHON_BIN" "$SERVICE_DIR/elevenlabs_service.py"
