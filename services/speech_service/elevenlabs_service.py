#!/usr/bin/env python3
"""Guía conversacional de Mimix con audio local y ElevenLabs Agents.

El proceso se ejecuta en la Jetson: toma el micrófono y parlante predeterminados,
y registra únicamente las dos herramientas permitidas para la primera versión.
Nunca ejecuta URLs, JavaScript ni comandos de hardware solicitados por el LLM.
"""

from __future__ import annotations

import logging
import os
import signal
from dataclasses import dataclass
from typing import Any

import requests
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import ClientTools, Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


logging.basicConfig(
    level=os.getenv("MIMIX_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("mimix.speech")


@dataclass(frozen=True)
class Settings:
    agent_id: str
    api_key: str | None
    web_url: str
    bridge_token: str | None
    robot_id: str

    @classmethod
    def from_environment(cls) -> "Settings":
        agent_id = os.getenv("MIMIX_ELEVENLABS_AGENT_ID", "").strip()
        if not agent_id:
            raise RuntimeError("MIMIX_ELEVENLABS_AGENT_ID is required")
        return cls(
            agent_id=agent_id,
            api_key=os.getenv("ELEVENLABS_API_KEY") or None,
            web_url=os.getenv("MIMIX_WEB_URL", "http://127.0.0.1:4000").rstrip("/"),
            bridge_token=os.getenv("MIMIX_ROBOT_BRIDGE_TOKEN") or None,
            robot_id=os.getenv("MIMIX_ROBOT_ID", "robot-dev-001"),
        )


class MimixWebClient:
    """Cliente del contrato local entre el guía de voz y Mimix Web."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        if settings.bridge_token:
            self.session.headers["X-Mimix-Robot-Token"] = settings.bridge_token

    def get_context(self, _parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(f"{self.settings.web_url}/api/robot/context", timeout=3)
        response.raise_for_status()
        return response.json()

    def navigate_to(self, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        destination = (parameters or {}).get("destination")
        if destination not in {"world", "mathematics", "science"}:
            return {
                "accepted": False,
                "message": "Solo están disponibles world, mathematics o science.",
            }

        response = self.session.post(
            f"{self.settings.web_url}/api/robot/commands",
            json={"action": "navigate_to", "destination": destination},
            timeout=3,
        )
        if response.status_code == 409:
            return {
                "accepted": False,
                "message": "Mimix Web no está abierto todavía. Pide abrir la plataforma primero.",
            }
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self.session.close()


class MimixGuide:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.web = MimixWebClient(settings)
        self.conversation: Conversation | None = None

    def run(self) -> None:
        tools = ClientTools()
        # Estos nombres deben coincidir exactamente con las herramientas Client
        # configuradas en el panel de ElevenLabs.
        tools.register("get_mimix_context", self.web.get_context)
        tools.register("navigate_to", self.web.navigate_to)

        client = ElevenLabs(api_key=self.settings.api_key)
        self.conversation = Conversation(
            client,
            self.settings.agent_id,
            requires_auth=bool(self.settings.api_key),
            audio_interface=DefaultAudioInterface(),
            client_tools=tools,
            callback_agent_response=lambda response: LOGGER.info("Wall-E: %s", response),
            callback_agent_response_correction=lambda original, corrected: LOGGER.info(
                "Wall-E corrected: %s -> %s", original, corrected
            ),
            callback_user_transcript=lambda transcript: LOGGER.info("Student: %s", transcript),
        )

        LOGGER.info("Iniciando conversación de Wall-E con el agente %s", self.settings.agent_id)
        self.conversation.start_session(user_id=self.settings.robot_id)
        conversation_id = self.conversation.wait_for_session_end()
        LOGGER.info("Conversación finalizada: %s", conversation_id)

    def stop(self) -> None:
        if self.conversation:
            self.conversation.end_session()
        self.web.close()


GUIDE: MimixGuide | None = None


def stop_service(_signal: int, _frame: Any) -> None:
    if GUIDE:
        GUIDE.stop()


def main() -> None:
    global GUIDE
    settings = Settings.from_environment()
    GUIDE = MimixGuide(settings)
    signal.signal(signal.SIGINT, stop_service)
    signal.signal(signal.SIGTERM, stop_service)
    try:
        GUIDE.run()
    finally:
        GUIDE.stop()


if __name__ == "__main__":
    main()
