#!/usr/bin/env python3
"""Guía conversacional de Mimix con audio local y ElevenLabs Agents.

El proceso se ejecuta en la Jetson: toma el micrófono y parlante predeterminados,
y registra las tres herramientas permitidas: get_mimix_context, navigate_to y get_dialogue.
Nunca ejecuta URLs, JavaScript ni comandos de hardware solicitados por el LLM.
"""

from __future__ import annotations

import json
import logging
import os
import signal
from dataclasses import dataclass
from typing import Any

import requests
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import ClientTools, Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

from dialogue_manager import DialogueManager


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
    voice_gesture_url: str

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
            voice_gesture_url=os.getenv(
                "MIMIX_VOICE_GESTURE_URL", "http://127.0.0.1:8092/talk"
            ).rstrip("/"),
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


class VoiceGestureClient:
    """Solicita un gesto local de conversación cuando Wall-E responde."""

    def __init__(self, settings: Settings) -> None:
        self.url = settings.voice_gesture_url
        self.session = requests.Session()

    def trigger(self, response: str) -> None:
        # Estimación deliberadamente limitada: el ESP32 siempre termina en BASE.
        word_count = max(1, len(response.split()))
        duration_ms = min(max(word_count * 500, 5000), 10000)
        try:
            result = self.session.post(
                self.url,
                json={"duration_ms": duration_ms},
                timeout=0.5,
            )
            result.raise_for_status()
            LOGGER.info("Gesto conversacional solicitado (%s ms)", duration_ms)
        except requests.RequestException as error:
            # La voz sigue funcionando aunque ROS no se haya iniciado.
            LOGGER.warning("No se pudo solicitar el gesto conversacional: %s", error)

    def close(self) -> None:
        self.session.close()


class MimixGuide:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.web = MimixWebClient(settings)
        self.gestures = VoiceGestureClient(settings)
        self.dialogues = DialogueManager()
        self.conversation: Conversation | None = None
        self.session_started = False

    def on_agent_response(self, response: str) -> None:
        LOGGER.info("Wall-E: %s", response)
        self.gestures.trigger(response)

    @staticmethod
    def _client_tool_result(result: dict[str, Any]) -> str:
        """Serializa el resultado para el protocolo de Client Tools de ElevenLabs.

        El SDK reenvía este valor al agente a través de WebSocket. Enviar un
        diccionario Python directamente provoca que el servidor rechace el
        mensaje; una cadena JSON conserva todos los campos para el agente.
        """
        return json.dumps(result, ensure_ascii=False)

    def get_mimix_context(
        self, parameters: dict[str, Any] | None = None
    ) -> str:
        return self._client_tool_result(self.web.get_context(parameters))

    def navigate_to(self, parameters: dict[str, Any] | None = None) -> str:
        return self._client_tool_result(self.web.navigate_to(parameters))

    def get_dialogue(self, parameters: dict[str, Any] | None = None) -> str:
        return self._client_tool_result(self.dialogues.get_dialogue(parameters))

    def run(self) -> None:
        tools = ClientTools()
        # Estos nombres deben coincidir exactamente con las herramientas Client
        # configuradas en el panel de ElevenLabs.
        tools.register("get_mimix_context", self.get_mimix_context)
        tools.register("navigate_to", self.navigate_to)
        tools.register("get_dialogue", self.get_dialogue)

        client = ElevenLabs(api_key=self.settings.api_key)
        self.conversation = Conversation(
            client,
            self.settings.agent_id,
            requires_auth=bool(self.settings.api_key),
            audio_interface=DefaultAudioInterface(),
            client_tools=tools,
            callback_agent_response=self.on_agent_response,
            callback_agent_response_correction=lambda original, corrected: LOGGER.info(
                "Wall-E corrected: %s -> %s", original, corrected
            ),
            callback_user_transcript=lambda transcript: LOGGER.info("Student: %s", transcript),
        )

        LOGGER.info("Iniciando conversación de Wall-E con el agente %s", self.settings.agent_id)
        # La versión actual del SDK de ElevenLabs no acepta user_id como
        # argumento de start_session(). El identificador local se conserva
        # para futura telemetría, sin bloquear la conversación de voz.
        self.conversation.start_session()
        self.session_started = True
        conversation_id = self.conversation.wait_for_session_end()
        LOGGER.info("Conversación finalizada: %s", conversation_id)

    def stop(self) -> None:
        # No intentes detener la interfaz de audio si start_session falló
        # antes de inicializarla.
        if self.conversation and self.session_started:
            # El callback de audio y el bloque finally pueden intentar cerrar
            # la misma sesión. Solo el primer cierre debe tocar PyAudio.
            self.session_started = False
            try:
                self.conversation.end_session()
            except OSError as error:
                LOGGER.debug("La interfaz de audio ya estaba cerrada: %s", error)
        self.web.close()
        self.gestures.close()


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
