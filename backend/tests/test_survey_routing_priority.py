import sys
import unittest
from pathlib import Path

from fastapi import HTTPException, status


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.api.v1.endpoints.survey_routing import _ensure_priority_available


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDb:
    def __init__(self, value):
        self.value = value
        self.executed = False

    async def execute(self, query):
        self.executed = True
        return FakeResult(self.value)


class SurveyRoutingPriorityTests(unittest.IsolatedAsyncioTestCase):
    async def test_priority_available_when_no_existing_rule(self) -> None:
        db = FakeDb(None)

        await _ensure_priority_available(db, "novosibirsk", 10)

        self.assertTrue(db.executed)

    async def test_duplicate_priority_returns_clear_conflict_error(self) -> None:
        db = FakeDb(123)

        with self.assertRaises(HTTPException) as context:
            await _ensure_priority_available(db, "novosibirsk", 10)

        self.assertEqual(context.exception.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            context.exception.detail,
            "Приоритет 10 уже используется в этой клинике. Измените приоритет правила.",
        )


if __name__ == "__main__":
    unittest.main()
