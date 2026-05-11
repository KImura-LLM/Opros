import unittest
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.ai_analysis.anonymizer import build_anonymized_payload


@dataclass
class FakeAnswer:
    node_id: str
    answer_data: dict
    duration_seconds: int | None = None


class AiAnonymizerTests(unittest.TestCase):
    def test_payload_contains_only_allowlisted_clinical_context(self) -> None:
        config = {
            "version": "2.0",
            "nodes": [
                {
                    "id": "complaint",
                    "type": "text_input",
                    "question_text": "Опишите жалобу",
                },
                {
                    "id": "pain",
                    "type": "single_choice",
                    "question_text": "Есть ли боль?",
                    "options": [{"value": "yes", "text": "Да"}],
                },
            ],
        }
        answers = [
            FakeAnswer(
                "complaint",
                {
                    "text": "болит горло",
                    "patient_name": "Иванов Иван",
                    "lead_id": 123,
                    "token_hash": "secret",
                },
                3,
            ),
            FakeAnswer("pain", {"selected": "yes"}, 1),
        ]

        payload = build_anonymized_payload(
            analysis_case_id="case-123",
            survey_config_id=7,
            config_json=config,
            answers=answers,
            completed_at=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )

        payload_text = str(payload)
        self.assertIn("case-123", payload_text)
        self.assertIn("болит горло", payload_text)
        self.assertIn("Да", payload_text)
        self.assertNotIn("Иванов", payload_text)
        self.assertNotIn("lead_id", payload_text)
        self.assertNotIn("token_hash", payload_text)
        self.assertNotIn("session_id", payload)

    def test_free_text_is_truncated(self) -> None:
        config = {"version": "2.0", "nodes": [{"id": "free", "type": "text_input", "question_text": "Жалоба"}]}
        payload = build_anonymized_payload(
            analysis_case_id="case-123",
            survey_config_id=1,
            config_json=config,
            answers=[FakeAnswer("free", {"text": "а" * 2000})],
        )
        answer_text = payload["answers"][0]["answer"]
        self.assertLessEqual(len(answer_text), 1501)
        self.assertTrue(answer_text.endswith("…"))


if __name__ == "__main__":
    unittest.main()
