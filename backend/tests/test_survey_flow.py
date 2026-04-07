import time
import unittest
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import delete

from app.core.database import async_session_maker
from app.core.redis import redis_client
from app.core.config import settings
from app.main import app
from app.models import AuditLog, SurveyAnswer, SurveySession
from app.schemas.schemas import SurveyCompleteRequest


def _choose_answer(node: dict) -> dict:
    node_type = node.get("type")
    options = node.get("options") or []
    first_value = None
    if options:
        first = options[0]
        first_value = first.get("value") or first.get("id") or first.get("text")

    if node_type == "single_choice":
        return {"selected": first_value}
    if node_type in {"multi_choice", "multi_choice_with_input"}:
        return {"selected": [first_value] if first_value is not None else []}
    if node_type in {"scale_1_10", "slider"}:
        return {"value": node.get("min_value", 1)}
    if node_type == "text_input":
        return {"text": "Тестовый ответ"}
    if node_type == "number_input":
        return {"value": node.get("min_value", 1)}
    if node_type == "body_map":
        return {"locations": ["test_location"], "intensity": 5}
    if node_type == "consent_screen":
        return {"selected": True}
    if node_type == "info_screen":
        return {}
    raise AssertionError(f"Неизвестный тип узла: {node_type}")


class SurveyFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )
        self.created_session_ids: list[UUID] = []
        self.created_lead_ids: list[int] = []
        self._original_bitrix_webhook_url = settings.BITRIX24_WEBHOOK_URL
        settings.BITRIX24_WEBHOOK_URL = ""

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

        async with async_session_maker() as db:
            if self.created_session_ids:
                await db.execute(delete(AuditLog).where(AuditLog.session_id.in_(self.created_session_ids)))
                await db.execute(delete(SurveyAnswer).where(SurveyAnswer.session_id.in_(self.created_session_ids)))
                await db.execute(delete(SurveySession).where(SurveySession.id.in_(self.created_session_ids)))
                await db.commit()

        await redis_client.connect()
        for session_id in self.created_session_ids:
            await redis_client.delete_survey_progress(str(session_id))
        settings.BITRIX24_WEBHOOK_URL = self._original_bitrix_webhook_url

    async def test_progress_restores_after_redis_loss(self) -> None:
        started = await self._start_session()
        session_id = started["session_id"]
        token = started["token"]
        headers = {"X-Session-Token": token}
        config = started["survey_config"]
        nodes = {node["id"]: node for node in config["nodes"]}

        current_node = config["start_node"]
        answered_nodes: list[str] = []
        for _ in range(2):
            response = await self.client.post(
                "/api/v1/survey/answer",
                json={
                    "session_id": session_id,
                    "node_id": current_node,
                    "answer_data": _choose_answer(nodes[current_node]),
                    "duration_seconds": 1,
                },
                headers=headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            answered_nodes.append(current_node)
            current_node = response.json()["next_node"]
            self.assertIsNotNone(current_node)

        await redis_client.connect()
        await redis_client.delete_survey_progress(session_id)

        progress_response = await self.client.get(
            f"/api/v1/survey/progress/{session_id}",
            headers=headers,
        )
        self.assertEqual(progress_response.status_code, 200, progress_response.text)

        progress_payload = progress_response.json()
        self.assertEqual(progress_payload["current_node"], current_node)
        for node_id in answered_nodes:
            self.assertIn(node_id, progress_payload["answers"])

    def test_complete_request_requires_paired_final_payload(self) -> None:
        with self.assertRaises(ValueError):
            SurveyCompleteRequest(
                session_id="550e8400-e29b-41d4-a716-446655440000",
                final_node_id="finish_question",
            )

        payload = SurveyCompleteRequest(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            final_node_id="finish_question",
            final_answer_data={"selected": "yes"},
            duration_seconds=4,
        )
        self.assertEqual(payload.final_node_id, "finish_question")
        self.assertEqual(payload.final_answer_data, {"selected": "yes"})

    async def _start_session(self) -> dict:
        lead_id = int(time.time() * 1000) % 1000000000
        self.created_lead_ids.append(lead_id)

        generate_response = await self.client.post(
            f"/api/v1/auth/generate-token?lead_id={lead_id}&patient_name=Тест+автотест&entity_type=DEAL"
        )
        self.assertEqual(generate_response.status_code, 200, generate_response.text)
        short_code = generate_response.json()["code"]

        validate_response = await self.client.get(f"/api/v1/auth/validate?token={short_code}")
        self.assertEqual(validate_response.status_code, 200, validate_response.text)
        token = validate_response.json().get("resolved_token") or short_code

        start_response = await self.client.post(
            "/api/v1/survey/start",
            json={"token": token, "consent_given": True},
        )
        self.assertEqual(start_response.status_code, 200, start_response.text)
        payload = start_response.json()
        self.created_session_ids.append(UUID(payload["session_id"]))
        expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
        ttl_seconds = (expires_at - datetime.now(timezone.utc)).total_seconds()
        self.assertGreater(ttl_seconds, settings.SESSION_TTL - 120)
        self.assertLessEqual(ttl_seconds, settings.SESSION_TTL + 120)

        return {
            "session_id": payload["session_id"],
            "token": token,
            "survey_config": payload["survey_config"],
        }


if __name__ == "__main__":
    unittest.main()
