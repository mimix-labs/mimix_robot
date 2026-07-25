#!/usr/bin/env bash
# Inicia la visión nativa de Mimix en la Jetson.

set -euo pipefail

VISION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$VISION_DIR/../.." && pwd)"
ENV_FILE="$ROBOT_DIR/.env"

if [[ -n "${MIMIX_VISION_PYTHON:-}" ]]; then
  PYTHON_BIN="$MIMIX_VISION_PYTHON"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  # Conserva el mismo intérprete del entorno activado desde el que se lanzó
  # Mimix. Es el que también se usa al ejecutar vision_service.py a mano.
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
else
  PYTHON_BIN="$VISION_DIR/.venv/bin/python"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Falta $ENV_FILE. Copia .env.example a .env y configura la cámara." >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Falta el entorno de visión. Ejecuta la instalación indicada en $VISION_DIR/README.md" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

VISION_PID=""

stop_vision() {
  if [[ -n "$VISION_PID" ]]; then
    kill "$VISION_PID" 2>/dev/null || true
    wait "$VISION_PID" 2>/dev/null || true
  fi
  exit 0
}

trap stop_vision INT TERM

echo "Iniciando visión nativa de Mimix con $PYTHON_BIN. Presiona Ctrl+C para detenerla."
while true; do
  "$PYTHON_BIN" "$VISION_DIR/vision_service.py" &
  VISION_PID="$!"

  if wait "$VISION_PID"; then
    echo "La visión se detuvo; reintentando en 2 segundos." >&2
  else
    echo "La visión no pudo iniciar; reintentando en 2 segundos." >&2
  fi
  VISION_PID=""
  sleep 2
done
