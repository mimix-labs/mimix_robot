#!/usr/bin/env bash
# Inicia la visión nativa de Mimix en la Jetson.

set -euo pipefail

VISION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_DIR="$(cd "$VISION_DIR/../.." && pwd)"
ENV_FILE="$ROBOT_DIR/.env"
PYTHON_BIN="$VISION_DIR/.venv/bin/python"

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

echo "Iniciando visión nativa de Mimix. Presiona Ctrl+C para detenerla."
exec "$PYTHON_BIN" "$VISION_DIR/vision_service.py"
