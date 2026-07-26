import json
import tempfile
import unittest
from pathlib import Path

from dialogue_manager import DialogueManager
from sync_elevenlabs_prompt import build_payload


SERVICE_DIR = Path(__file__).resolve().parents[1]


class DialogueManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = DialogueManager(SERVICE_DIR / "dialogues.json")

    def test_stage_science_dialogue_is_accent_insensitive_and_navigable(self) -> None:
        dialogue = self.manager.get_dialogue(
            {"keyword": "Wall-E, quiero aprender Ciencias"}
        )

        self.assertTrue(dialogue["found"])
        self.assertEqual(dialogue["id"], "demo_ciencias")
        self.assertEqual(dialogue["destination"], "science")
        self.assertEqual(
            dialogue["response"],
            "¡Perfecto! Vamos al mundo de Ciencias y a la misión de Química de tu izquierda.",
        )

    def test_more_specific_phrase_wins_over_a_shorter_keyword(self) -> None:
        dialogue = self.manager.get_dialogue(
            {"keyword": "Wall-E, quiero aprender matematicas"}
        )

        self.assertTrue(dialogue["found"])
        self.assertEqual(dialogue["id"], "demo_matematicas")
        self.assertEqual(dialogue["destination"], "mathematics")

    def test_invalid_destination_is_not_returned_to_the_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dialogues_path = Path(directory) / "dialogues.json"
            dialogues_path.write_text(
                json.dumps(
                    {
                        "dialogues": [
                            {
                                "id": "unsafe",
                                "keywords": ["haz algo"],
                                "destination": "serial://servo",
                                "response": "No se debe ejecutar.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            dialogue = DialogueManager(dialogues_path).get_dialogue(
                {"keyword": "Wall-E, haz algo"}
            )

        self.assertTrue(dialogue["found"])
        self.assertNotIn("destination", dialogue)


class ElevenLabsPromptPayloadTests(unittest.TestCase):
    def test_payload_preserves_registered_tool_ids_and_disables_interruptions(self) -> None:
        current_agent = {
            "conversation_config": {
                "conversation": {
                    "client_events": ["audio", "interruption", "agent_response"],
                },
                "agent": {
                    "prompt": {
                        "prompt": "previous prompt",
                        "tool_ids": ["tool_context", "tool_navigate", "tool_dialogue"],
                    }
                }
            }
        }

        payload = build_payload(current_agent, "new prompt")
        prompt = payload["conversation_config"]["agent"]["prompt"]
        client_events = payload["conversation_config"]["conversation"]["client_events"]

        self.assertEqual(prompt["prompt"], "new prompt")
        self.assertTrue(prompt["ignore_default_personality"])
        self.assertEqual(
            prompt["tool_ids"],
            ["tool_context", "tool_navigate", "tool_dialogue"],
        )
        self.assertEqual(client_events, ["audio", "agent_response"])

    def test_payload_keeps_other_events_when_interruption_was_already_disabled(self) -> None:
        current_agent = {
            "conversation_config": {
                "conversation": {"client_events": ["audio"]},
                "agent": {"prompt": {"prompt": "previous prompt"}},
            }
        }

        payload = build_payload(current_agent, "new prompt")

        self.assertEqual(
            payload["conversation_config"]["conversation"]["client_events"],
            ["audio"],
        )


if __name__ == "__main__":
    unittest.main()
