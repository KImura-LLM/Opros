import json
import importlib.util
import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

if "loguru" not in sys.modules:
    dummy_logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        debug=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )
    sys.modules["loguru"] = types.SimpleNamespace(logger=dummy_logger)

survey_engine_path = BACKEND_DIR / "app" / "services" / "survey_engine.py"
spec = importlib.util.spec_from_file_location("survey_engine_test_module", survey_engine_path)
survey_engine_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(survey_engine_module)
SurveyEngine = survey_engine_module.SurveyEngine


class SurveyEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = BACKEND_DIR / "data" / "survey_structure_v2.json"
        cls.real_config = json.loads(config_path.read_text(encoding="utf-8-sig"))

    def test_real_config_uses_default_transition_for_welcome_screen(self) -> None:
        engine = SurveyEngine(self.real_config)

        next_node = engine.get_next_node("welcome", {}, {})

        self.assertEqual(next_node, "body_location")

    def test_real_config_honors_contains_branching_rule(self) -> None:
        engine = SurveyEngine(self.real_config)

        next_node = engine.get_next_node(
            "pain_character",
            {"selected": ["no_pain"]},
            {},
        )

        self.assertEqual(next_node, "free_complaint")

    def test_numeric_conditions_support_greater_or_equal(self) -> None:
        config = {
            "start_node": "severity",
            "nodes": [
                {
                    "id": "severity",
                    "type": "slider",
                    "required": True,
                    "logic": [
                        {"condition": "value >= 7", "next_node": "urgent"},
                        {"default": True, "next_node": "routine"},
                    ],
                },
                {"id": "urgent", "type": "info_screen", "required": False, "is_final": True},
                {"id": "routine", "type": "info_screen", "required": False, "is_final": True},
            ],
        }
        engine = SurveyEngine(config)

        next_node = engine.get_next_node("severity", {"value": 7}, {})

        self.assertEqual(next_node, "urgent")

    def test_cross_node_conditions_use_previous_answers(self) -> None:
        config = {
            "start_node": "screening",
            "nodes": [
                {
                    "id": "screening",
                    "type": "multi_choice",
                    "required": True,
                    "logic": [{"default": True, "next_node": "follow_up"}],
                },
                {
                    "id": "follow_up",
                    "type": "info_screen",
                    "required": False,
                    "logic": [
                        {
                            "condition": "screening.selected contains 'cough'",
                            "next_node": "respiratory",
                        },
                        {"default": True, "next_node": "general"},
                    ],
                },
                {"id": "respiratory", "type": "text_input", "required": False, "is_final": True},
                {"id": "general", "type": "text_input", "required": False, "is_final": True},
            ],
        }
        engine = SurveyEngine(config)

        next_node = engine.get_next_node(
            "follow_up",
            {},
            {"screening": {"selected": ["cough", "fever"]}},
        )

        self.assertEqual(next_node, "respiratory")

    def test_progress_ignores_info_screens(self) -> None:
        config = {
            "start_node": "welcome",
            "nodes": [
                {
                    "id": "welcome",
                    "type": "info_screen",
                    "required": False,
                    "logic": [{"default": True, "next_node": "question"}],
                },
                {
                    "id": "question",
                    "type": "single_choice",
                    "required": True,
                    "logic": [{"default": True, "next_node": "final"}],
                },
                {"id": "final", "type": "text_input", "required": False, "is_final": True},
            ],
        }
        engine = SurveyEngine(config)

        progress_before_first_answer = engine.calculate_dynamic_progress("question", ["welcome"])
        progress_after_first_answer = engine.calculate_dynamic_progress("final", ["welcome", "question"])

        self.assertEqual(progress_before_first_answer, 0.0)
        self.assertEqual(progress_after_first_answer, 50.0)

    def test_progress_counts_skipped_questions_by_next_position(self) -> None:
        config = {
            "start_node": "q1",
            "nodes": [
                {"id": "q1", "type": "single_choice", "required": True},
                {"id": "skipped_1", "type": "single_choice", "required": True},
                {"id": "skipped_2", "type": "single_choice", "required": True},
                {"id": "q2", "type": "text_input", "required": True},
                {"id": "q3", "type": "text_input", "required": True},
            ],
        }
        engine = SurveyEngine(config)

        progress_after_skip = engine.calculate_dynamic_progress("q2", ["q1"])

        self.assertEqual(progress_after_skip, 60.0)


if __name__ == "__main__":
    unittest.main()
