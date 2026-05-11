"""OpenRouter OpenAI-compatible client for Opros AI analysis."""

import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.services.ai_analysis.prompt import build_messages, build_response_format
from app.services.ai_analysis.schemas import AiAnalysisResponse


class OpenRouterClientError(Exception):
    """Безопасная ошибка клиента OpenRouter без секретов и payload."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


class OpenRouterClient:
    """Минимальный async-клиент OpenRouter Chat Completions."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.model = model or settings.OPENROUTER_MODEL
        self.timeout_seconds = timeout_seconds or settings.OPENROUTER_TIMEOUT_SECONDS
        self.transport = transport

    async def analyze(self, payload: dict[str, Any]) -> AiAnalysisResponse:
        """Отправляет обезличенный payload и возвращает валидированный JSON."""
        if not self.api_key:
            raise OpenRouterClientError("missing_api_key", "OPENROUTER_API_KEY is not configured", retryable=False)
        try:
            self.api_key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise OpenRouterClientError(
                "invalid_api_key",
                "OPENROUTER_API_KEY contains invalid non-ASCII characters",
                retryable=False,
            ) from exc

        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(payload),
            "temperature": 0.2,
            "max_tokens": 2200,
            "response_format": build_response_format(),
        }
        if settings.AI_ANALYSIS_ZDR_REQUIRED:
            request_body["provider"] = {"zdr": True}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Opros AI Analysis",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )
        except httpx.TimeoutException as exc:
            raise OpenRouterClientError("timeout", "OpenRouter request timed out", retryable=True) from exc
        except httpx.RequestError as exc:
            raise OpenRouterClientError("request_error", "OpenRouter request failed", retryable=True) from exc

        if response.status_code == 429:
            raise OpenRouterClientError("rate_limited", "OpenRouter rate limit", retryable=True)
        if 500 <= response.status_code < 600:
            raise OpenRouterClientError("server_error", f"OpenRouter server error {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise OpenRouterClientError("http_error", f"OpenRouter HTTP error {response.status_code}", retryable=False)

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise OpenRouterClientError("invalid_response_json", "OpenRouter returned invalid JSON", retryable=True) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterClientError("empty_response", "OpenRouter response has no message content", retryable=True) from exc

        if isinstance(content, dict):
            parsed_content = content
        elif isinstance(content, str) and content.strip():
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError as exc:
                raise OpenRouterClientError("invalid_model_json", "AI response is not valid JSON", retryable=True) from exc
        else:
            raise OpenRouterClientError("empty_response", "AI response content is empty", retryable=True)

        try:
            return AiAnalysisResponse.model_validate(parsed_content)
        except ValidationError as exc:
            raise OpenRouterClientError("schema_validation_failed", "AI response does not match schema", retryable=True) from exc
