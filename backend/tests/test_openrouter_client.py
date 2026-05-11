import unittest

import httpx

from app.services.ai_analysis.openrouter_client import OpenRouterClient, OpenRouterClientError


VALID_AI_JSON = {
    "overall_priority": "yellow",
    "summary": "Нужна очная оценка жалоб.",
    "red_flags": [],
    "key_findings": [
        {
            "title": "Боль",
            "priority": "yellow",
            "description": "Пациент отметил боль.",
            "evidence": [{"node_id": "pain", "question": "Боль?", "answer": "Да"}],
        }
    ],
    "doctor_recommendations": [{"priority": "yellow", "text": "Уточнить длительность."}],
    "limitations": "Основано только на анкете.",
}


class OpenRouterClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_response_is_validated(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["authorization"], "Bearer test-key")
            return httpx.Response(200, json={"choices": [{"message": {"content": VALID_AI_JSON}}]})

        client = OpenRouterClient(
            api_key="test-key",
            base_url="https://openrouter.test/api/v1",
            model="test-model",
            transport=httpx.MockTransport(handler),
        )

        result = await client.analyze({"analysis_case_id": "case", "answers": []})
        self.assertEqual(result.overall_priority, "yellow")
        self.assertEqual(result.key_findings[0].evidence[0].node_id, "pain")

    async def test_http_429_is_retryable_without_exposing_api_key(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "rate limit"})

        client = OpenRouterClient(
            api_key="secret-key",
            base_url="https://openrouter.test/api/v1",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(OpenRouterClientError) as ctx:
            await client.analyze({"analysis_case_id": "case", "answers": []})

        self.assertEqual(ctx.exception.code, "rate_limited")
        self.assertTrue(ctx.exception.retryable)
        self.assertNotIn("secret-key", ctx.exception.safe_message)

    async def test_invalid_model_json_fails_safely(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

        client = OpenRouterClient(
            api_key="test-key",
            base_url="https://openrouter.test/api/v1",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(OpenRouterClientError) as ctx:
            await client.analyze({"analysis_case_id": "case", "answers": []})

        self.assertEqual(ctx.exception.code, "invalid_model_json")


if __name__ == "__main__":
    unittest.main()
