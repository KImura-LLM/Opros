import sys
import importlib.util
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

report_generator_path = BACKEND_DIR / "app" / "services" / "report_generator.py"
spec = importlib.util.spec_from_file_location("report_generator_test_module", report_generator_path)
report_generator_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(report_generator_module)
ReportGenerator = report_generator_module.ReportGenerator


class ReportGeneratorFormattingTests(unittest.TestCase):
    def test_formats_body_locations_from_shared_mapping(self) -> None:
        generator = ReportGenerator({"nodes": []})

        self.assertEqual(
            generator._format_body_locations(["head", "unknown_location"]),
            "Голова, unknown_location",
        )

    def test_pain_location_mapping_is_consistent_across_report_formats(self) -> None:
        generator = ReportGenerator({"nodes": []})
        answers = {"pain_details": {"locations": ["head"], "intensity": 7}}

        html = generator._generate_pain_details(answers)
        readable = generator._generate_readable_pain_details(answers)
        text = generator._generate_text_pain_details(answers)

        self.assertIn("Голова", html)
        self.assertIn("Голова", readable)
        self.assertIn("Голова", text)

    def test_html_report_escapes_patient_answers_and_name(self) -> None:
        generator = ReportGenerator(
            {
                "nodes": [
                    {
                        "id": "free_complaint",
                        "type": "text_input",
                        "question_text": "Комментарий",
                    }
                ]
            }
        )

        report = generator.generate_readable_html_report(
            '<script>alert("patient")</script>',
            {"free_complaint": {"text": '<img src=x onerror=alert("x")>'}},
        )

        self.assertIn("&lt;script&gt;alert(&quot;patient&quot;)&lt;/script&gt;", report)
        self.assertIn("&lt;img src=x onerror=alert(&quot;x&quot;)&gt;", report)
        self.assertNotIn("<script>alert", report)
        self.assertNotIn("<img src=x", report)

    def test_ai_block_is_above_system_analysis_and_escapes_html(self) -> None:
        generator = ReportGenerator(
            {
                "nodes": [
                    {
                        "id": "pain",
                        "type": "single_choice",
                        "question_text": "Есть боль?",
                        "options": [{"value": "yes", "text": "Да"}],
                    }
                ],
                "analysis_rules": [
                    {
                        "name": "Rule based",
                        "message": "Проверить боль",
                        "color": "red",
                        "triggers": [{"node_id": "pain", "option_value": "yes"}],
                    }
                ],
            }
        )
        ai_result = {
            "overall_priority": "red",
            "summary": '<script>alert("ai")</script>',
            "red_flags": [
                {
                    "title": "Красный флаг",
                    "description": "<b>опасно</b>",
                    "evidence": [{"node_id": "pain", "question": "Есть боль?", "answer": "Да"}],
                }
            ],
            "key_findings": [],
            "doctor_recommendations": [],
            "limitations": "Только анкета",
        }

        report = generator.generate_readable_html_report(
            "Пациент",
            {"pain": {"selected": "yes"}},
            ai_analysis=ai_result,
        )

        self.assertLess(report.index("ИИ-анализ для врача"), report.index("СИСТЕМНЫЙ АНАЛИЗ ДЛЯ ВРАЧА"))
        self.assertIn("Красные флаги", report)
        self.assertIn("&lt;script&gt;alert(&quot;ai&quot;)&lt;/script&gt;", report)
        self.assertIn("&lt;b&gt;опасно&lt;/b&gt;", report)
        self.assertIn("Есть боль?: <strong>Да</strong>", report)
        self.assertNotIn("[pain]", report)
        self.assertNotIn("<script>alert", report)

    def test_text_report_contains_ai_and_system_sections(self) -> None:
        generator = ReportGenerator(
            {
                "nodes": [
                    {
                        "id": "pain",
                        "type": "single_choice",
                        "question_text": "Есть боль?",
                        "options": [{"value": "yes", "text": "Да"}],
                    }
                ],
                "analysis_rules": [
                    {
                        "message": "Rule-based warning",
                        "color": "yellow",
                        "triggers": [{"node_id": "pain", "option_value": "yes"}],
                    }
                ],
            }
        )
        ai_result = {
            "overall_priority": "yellow",
            "summary": "AI summary",
            "red_flags": [],
            "key_findings": [
                {
                    "title": "Боль",
                    "priority": "yellow",
                    "description": "Есть жалоба",
                    "evidence": [{"node_id": "pain", "question": "Есть боль?", "answer": "Да"}],
                }
            ],
            "doctor_recommendations": [{"priority": "yellow", "text": "Уточнить детали"}],
            "limitations": "Только анкета",
        }

        report = generator.generate_text_report(
            "Пациент",
            {"pain": {"selected": "yes"}},
            ai_analysis=ai_result,
        )

        self.assertLess(report.index("ИИ-АНАЛИЗ ДЛЯ ВРАЧА"), report.index("СИСТЕМНЫЙ АНАЛИЗ ДЛЯ ВРАЧА"))
        self.assertIn("РЕКОМЕНДАЦИИ ВРАЧУ", report)
        self.assertIn("Основание: Есть боль? — Да", report)
        self.assertNotIn("[pain]", report)
        self.assertIn("Rule-based warning", report)

    def test_ai_block_hides_bracket_garbage_limitations(self) -> None:
        generator = ReportGenerator({"nodes": []})
        ai_result = {
            "overall_priority": "yellow",
            "summary": "AI summary",
            "red_flags": [],
            "key_findings": [],
            "doctor_recommendations": [],
            "limitations": "}]}]" * 80,
        }

        html = generator.generate_readable_html_report("Пациент", {}, ai_analysis=ai_result)
        text = generator.generate_text_report("Пациент", {}, ai_analysis=ai_result)

        self.assertIn("ИИ-анализ является вспомогательным инструментом", html)
        self.assertNotIn("}]}]}]}", html)
        self.assertNotIn("}]}]}]}", text)


if __name__ == "__main__":
    unittest.main()
