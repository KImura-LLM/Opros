import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.models import SurveyRoutingCondition, SurveyRoutingRule
from app.services.survey_routing import (
    compare_condition,
    normalize_bitrix_category_id,
    resolve_clinic_key_from_deal,
    rule_matches,
)


def condition(field_id: str, operator: str, value=None) -> SurveyRoutingCondition:
    return SurveyRoutingCondition(
        crm_field_id=field_id,
        operator=operator,
        value=value,
    )


def rule(logic: str, conditions: list[SurveyRoutingCondition]) -> SurveyRoutingRule:
    item = SurveyRoutingRule(
        clinic_key="novosibirsk",
        name="test",
        survey_config_id=1,
        condition_logic=logic,
        priority=100,
    )
    item.conditions = conditions
    return item


class SurveyRoutingConditionTests(unittest.TestCase):
    def test_equals_operator(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "equals", "42"), {"UF": "42"}))
        self.assertFalse(compare_condition(condition("UF", "equals", "42"), {"UF": "43"}))

    def test_not_equals_operator(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "not_equals", "42"), {"UF": "43"}))
        self.assertFalse(compare_condition(condition("UF", "not_equals", "42"), {"UF": "42"}))

    def test_contains_operator_is_case_insensitive(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "contains", "невро"), {"UF": "Неврология"}))

    def test_not_contains_operator(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "not_contains", "травма"), {"UF": "Неврология"}))
        self.assertFalse(compare_condition(condition("UF", "not_contains", "невро"), {"UF": "Неврология"}))

    def test_is_filled_and_is_empty(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "is_filled"), {"UF": "значение"}))
        self.assertFalse(compare_condition(condition("UF", "is_filled"), {"UF": "   "}))
        self.assertTrue(compare_condition(condition("UF", "is_empty"), {"UF": []}))
        self.assertFalse(compare_condition(condition("UF", "is_empty"), {"UF": ["x"]}))

    def test_multi_value_field_matches_any_item(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "equals", "3959"), {"UF": ["", "3959"]}))

    def test_dict_value_uses_bitrix_value_key(self) -> None:
        self.assertTrue(compare_condition(condition("UF", "equals", "3959"), {"UF": {"VALUE": "3959"}}))

    def test_rule_matches_and_logic(self) -> None:
        item = rule(
            "AND",
            [
                condition("A", "equals", "1"),
                condition("B", "contains", "foo"),
            ],
        )
        self.assertTrue(rule_matches(item, {"A": "1", "B": "foobar"}))
        self.assertFalse(rule_matches(item, {"A": "1", "B": "bar"}))

    def test_rule_matches_or_logic(self) -> None:
        item = rule(
            "OR",
            [
                condition("A", "equals", "1"),
                condition("B", "equals", "2"),
            ],
        )
        self.assertTrue(rule_matches(item, {"A": "0", "B": "2"}))
        self.assertFalse(rule_matches(item, {"A": "0", "B": "0"}))

    def test_resolves_clinic_from_category(self) -> None:
        clinic_key, reason_code = resolve_clinic_key_from_deal({"CATEGORY_ID": "1"})
        self.assertEqual(clinic_key, "kemerovo")
        self.assertEqual(reason_code, "clinic_resolved")

    def test_unknown_category_goes_to_test_clinic(self) -> None:
        clinic_key, reason_code = resolve_clinic_key_from_deal({"CATEGORY_ID": "99"})
        self.assertEqual(clinic_key, "test")
        self.assertEqual(reason_code, "unknown_clinic")

    def test_normalizes_numeric_category(self) -> None:
        self.assertEqual(normalize_bitrix_category_id("03"), "3")


if __name__ == "__main__":
    unittest.main()
