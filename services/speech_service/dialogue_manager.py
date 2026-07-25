"""Diálogos deterministas que el agente de voz puede solicitar."""

from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("mimix.speech.dialogues")


class DialogueManager:
    """Carga los diálogos locales y expone solo la siguiente acción permitida."""

    ALLOWED_DESTINATIONS = frozenset({"world", "mathematics", "science"})

    def __init__(self, dialogues_path: Path | None = None) -> None:
        self.dialogues_path = dialogues_path or Path(__file__).resolve().parent / "dialogues.json"
        self.dialogues: list[dict[str, Any]] = []
        self._reload()

    @staticmethod
    def _normalise(text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text.casefold())
        return "".join(character for character in decomposed if not unicodedata.combining(character))

    def _reload(self) -> None:
        try:
            data = json.loads(self.dialogues_path.read_text(encoding="utf-8"))
            dialogues = data.get("dialogues", [])
            if not isinstance(dialogues, list):
                raise ValueError("'dialogues' debe ser una lista.")
            self.dialogues = [dialogue for dialogue in dialogues if isinstance(dialogue, dict)]
            LOGGER.info("Diálogos cargados: %d entradas", len(self.dialogues))
        except Exception:
            LOGGER.exception("No se pudieron cargar los diálogos desde %s", self.dialogues_path)
            self.dialogues = []

    def get_dialogue(self, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Devuelve el diálogo más específico que aparece en el mensaje recibido."""

        keyword = str((parameters or {}).get("keyword") or "").strip()
        normalized_keyword = self._normalise(keyword)
        if not normalized_keyword:
            return {"found": False, "response": ""}

        matches: list[tuple[int, int, dict[str, Any]]] = []
        for dialogue_index, dialogue in enumerate(self.dialogues):
            for phrase in dialogue.get("keywords", []):
                normalized_phrase = self._normalise(str(phrase).strip())
                if normalized_phrase and normalized_phrase in normalized_keyword:
                    matches.append((len(normalized_phrase), -dialogue_index, dialogue))

        if not matches:
            LOGGER.info("Ningún diálogo coincide con: %s", keyword)
            return {"found": False, "response": ""}

        _, _, dialogue = max(matches, key=lambda match: (match[0], match[1]))
        response = dialogue.get("response")
        if not isinstance(response, str) or not response.strip():
            LOGGER.warning("Diálogo inválido sin respuesta: %s", dialogue.get("id"))
            return {"found": False, "response": ""}

        result: dict[str, Any] = {
            "found": True,
            "id": str(dialogue.get("id") or ""),
            "response": response,
        }
        destination = dialogue.get("destination")
        if destination in self.ALLOWED_DESTINATIONS:
            result["destination"] = destination
        elif destination is not None:
            LOGGER.warning("Destino ignorado para %s: %r", dialogue.get("id"), destination)

        LOGGER.info("Diálogo encontrado: %s -> %s", result["id"], keyword)
        return result
