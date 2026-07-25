#!/usr/bin/env python3
"""Publica el prompt versionado de Wall-E en el agente de ElevenLabs.

El script conserva la configuración actual del prompt, incluidos los IDs de
herramientas Client. Solo sustituye el texto del prompt e inhabilita la
personalidad predeterminada para que las reglas de silencio tengan prioridad.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Mapping
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = Path(__file__).resolve().with_name("system_prompt.md")
API_BASE_URL = "https://api.elevenlabs.io/v1/convai/agents"


def read_dotenv(path: Path) -> dict[str, str]:
    """Lee pares KEY=VALUE sencillos sin reemplazar variables ya exportadas."""

    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def resolve_settings(env_file: Path) -> Mapping[str, str]:
    values = read_dotenv(env_file)
    return {
        "agent_id": os.getenv("MIMIX_ELEVENLABS_AGENT_ID") or values.get("MIMIX_ELEVENLABS_AGENT_ID", ""),
        "api_key": os.getenv("ELEVENLABS_API_KEY") or values.get("ELEVENLABS_API_KEY", ""),
    }


def build_payload(current_agent: Mapping[str, object], prompt: str) -> dict[str, object]:
    try:
        conversation_config = current_agent["conversation_config"]
        agent_config = conversation_config["agent"]  # type: ignore[index]
        current_prompt = agent_config["prompt"]  # type: ignore[index]
    except (KeyError, TypeError) as error:
        raise ValueError("La respuesta de ElevenLabs no contiene conversation_config.agent.prompt.") from error

    if not isinstance(current_prompt, dict):
        raise ValueError("La configuración actual del prompt no es un objeto JSON.")

    prompt_config = dict(current_prompt)
    prompt_config["prompt"] = prompt
    prompt_config["ignore_default_personality"] = True
    return {"conversation_config": {"agent": {"prompt": prompt_config}}}


def request_json(
    url: str,
    api_key: str,
    method: str,
    payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:  # nosec B310: endpoint fijo de ElevenLabs
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=REPOSITORY_ROOT / ".env")
    parser.add_argument("--dry-run", action="store_true", help="Valida credenciales y muestra el cambio sin publicar.")
    arguments = parser.parse_args()

    settings = resolve_settings(arguments.env_file)
    agent_id = settings["agent_id"].strip()
    api_key = settings["api_key"].strip()
    if not agent_id or not api_key:
        raise SystemExit(
            "Faltan MIMIX_ELEVENLABS_AGENT_ID o ELEVENLABS_API_KEY en el entorno o en .env."
        )

    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not prompt:
        raise SystemExit(f"El prompt está vacío: {PROMPT_PATH}")

    url = f"{API_BASE_URL}/{agent_id}"
    current_agent = request_json(url, api_key, "GET")
    payload = build_payload(current_agent, prompt)

    if arguments.dry_run:
        print(f"Validado: se actualizaría el prompt del agente {agent_id} sin modificar sus herramientas.")
        return

    request_json(url, api_key, "PATCH", payload)
    print(f"Prompt publicado en ElevenLabs para el agente {agent_id}.")


if __name__ == "__main__":
    main()
