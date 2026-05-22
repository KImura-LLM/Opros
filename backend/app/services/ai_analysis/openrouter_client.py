"""OpenRouter OpenAI-compatible client for Opros AI analysis."""

import json
import re
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


def _safe_validation_summary(exc: ValidationError, *, limit: int = 5) -> str:
    """Summarize schema errors without including model output values."""
    parts: list[str] = []
    for error in exc.errors(include_input=False, include_context=False)[:limit]:
        loc = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
        error_type = error.get("type", "validation_error")
        parts.append(f"{loc}:{error_type}")
    if exc.error_count() > limit:
        parts.append(f"...+{exc.error_count() - limit}")
    return "; ".join(parts)


def _safe_json_profile(content: str) -> str:
    """Return non-content diagnostics for invalid model JSON."""
    text = content.strip()
    if not text:
        return "empty_after_strip"
    first = text[0]
    if first == "{":
        first_kind = "object"
    elif first == "[":
        first_kind = "array"
    elif first == "`":
        first_kind = "fence"
    elif first == "<":
        first_kind = "tag"
    elif first.isalpha():
        first_kind = "letter"
    else:
        first_kind = "other"
    return (
        f"chars={len(text)}; first={first_kind}; "
        f"open_braces={text.count('{')}; close_braces={text.count('}')}; "
        f"has_root_keys={int('overall_priority' in text and 'summary' in text and 'limitations' in text)}"
    )


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
            "max_tokens": 3500,
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
            parsed_content = self._parse_model_json(content)
        else:
            raise OpenRouterClientError("empty_response", "AI response content is empty", retryable=True)

        try:
            return AiAnalysisResponse.model_validate(parsed_content)
        except ValidationError as exc:
            summary = _safe_validation_summary(exc)
            message = "AI response does not match schema"
            if summary:
                message = f"{message}: {summary}"
            raise OpenRouterClientError("schema_validation_failed", message, retryable=True) from exc

    @staticmethod
    def _parse_model_json(content: str) -> dict[str, Any]:
        """
        Parse model JSON without logging or storing raw content.

        Some OpenRouter models occasionally ignore response_format partially and
        wrap the object in Markdown fences or short prose. We still accept a
        single valid JSON object, but reject responses where no complete object
        can be decoded.
        """
        text = content.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            try:
                parsed = json.loads(fenced.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        decoder = json.JSONDecoder()
        expected_root_keys = {
            "overall_priority",
            "summary",
            "red_flags",
            "key_findings",
            "doctor_recommendations",
            "limitations",
        }
        candidates: list[dict[str, Any]] = []
        for start_index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, end_index = decoder.raw_decode(text[start_index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and expected_root_keys.issubset(parsed.keys()):
                return parsed
            if isinstance(parsed, dict) and expected_root_keys.intersection(parsed.keys()):
                candidates.append(parsed)

        if candidates:
            return max(candidates, key=lambda item: len(expected_root_keys.intersection(item.keys())))

        raise OpenRouterClientError(
            "invalid_model_json",
            f"AI response is not valid JSON: {_safe_json_profile(content)}",
            retryable=True,
        )
