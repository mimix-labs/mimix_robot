#!/usr/bin/env bash
# Abre la sesión de voz de ElevenLabs solo cuando va a usarse.

set -euo pipefail

JETSON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$JETSON_DIR/../.." && pwd)"
VOICE_RUNNER="$ROBOT_DIR/services/speech_service/start_walle.sh"

if [[ ! -f "$VOICE_RUNNER" ]]; then
  echo "No se encontró el iniciador de voz: $VOICE_RUNNER" >&2
  exit 1
fi

if ! curl --silent --fail http://127.0.0.1:8092/health >/dev/null; then
  echo "El puente ROS de gestos no está listo en :8092. Inicia primero:" >&2
  echo "  bash deploy/jetson/start_mimix.sh --physical" >&2
  exit 1
fi

echo "Abriendo sesión de voz de Wall-E. Presiona Ctrl+C al terminar para cerrarla."
exec bash "$VOICE_RUNNER"
