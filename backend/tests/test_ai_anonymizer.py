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
            "analysis_rules": [
                {
                    "name": "Системное правило",
                    "message": "СИСТЕМНЫЙ АНАЛИЗ НЕ ДОЛЖЕН УЙТИ В ИИ",
                    "triggers": [{"node_id": "pain", "option_value": "yes"}],
                }
            ],
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
                    "patient_name": "PATIENT_SECRET_NAME",
                    "lead_id": 123,
                    "token_hash": "secret",
                    "system_analysis": "SYSTEM_ANALYSIS_SENTINEL",
                    "analysis_rules": "ANALYSIS_RULES_SENTINEL",
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
        self.assertNotIn("PATIENT_SECRET_NAME", payload_text)
        self.assertNotIn("lead_id", payload_text)
        self.assertNotIn("token_hash", payload_text)
        self.assertNotIn("СИСТЕМНЫЙ АНАЛИЗ НЕ ДОЛЖЕН УЙТИ В ИИ", payload_text)
        self.assertNotIn("SYSTEM_ANALYSIS_SENTINEL", payload_text)
        self.assertNotIn("ANALYSIS_RULES_SENTINEL", payload_text)
        self.assertNotIn("analysis_rules", payload_text)
        self.assertNotIn("system_analysis", payload_text)
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
