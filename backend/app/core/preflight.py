"""Fail-fast проверки production-конфигурации без вывода значений секретов."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PreflightResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_https_url(value: str | None) -> bool:
    parsed = urlparse((value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def check_production_environment(env: Mapping[str, str]) -> PreflightResult:
    """Проверяет только наличие и свойства значений, но никогда не возвращает их."""
    errors: list[str] = []
    warnings: list[str] = []

    if env.get("ENVIRONMENT", "").strip().lower() != "production":
        errors.append("ENVIRONMENT должен быть production")
    if _is_true(env.get("DEBUG")):
        errors.append("DEBUG должен быть false")

    secret_fields = ("SECRET_KEY", "JWT_SECRET_KEY")
    for field in secret_fields:
        value = env.get(field, "")
        if len(value) < 32 or "change-me" in value.lower() or "replace-me" in value.lower():
            errors.append(f"{field} должен содержать не менее 32 символов")
    if env.get("SECRET_KEY") and env.get("SECRET_KEY") == env.get("JWT_SECRET_KEY"):
        errors.append("SECRET_KEY и JWT_SECRET_KEY должны различаться")
    if env.get("JWT_ALGORITHM", "").strip().upper() != "HS256":
        errors.append("JWT_ALGORITHM должен быть HS256 для поддерживаемой production-конфигурации")

    if env.get("ADMIN_USERNAME", "").strip().lower() in {"", "admin"}:
        errors.append("ADMIN_USERNAME должен быть задан и не равен admin")
    for field, minimum in (
        ("ADMIN_PASSWORD", 16),
        ("POSTGRES_PASSWORD", 16),
        ("REDIS_PASSWORD", 16),
        ("BITRIX24_INCOMING_TOKEN", 24),
    ):
        value = env.get(field, "")
        if len(value) < minimum or "change-me" in value.lower() or "replace-me" in value.lower():
            errors.append(f"{field} должен содержать не менее {minimum} символов")

    if not _is_https_url(env.get("FRONTEND_URL")):
        errors.append("FRONTEND_URL должен быть абсолютным HTTPS URL")

    origins = [
        origin.strip()
        for origin in env.get("CORS_ORIGINS_STR", "").split(",")
        if origin.strip()
    ]
    if not origins:
        errors.append("CORS_ORIGINS_STR должен содержать хотя бы один origin")
    elif any(
        origin == "*"
        or not _is_https_url(origin)
        or urlparse(origin).hostname in {"localhost", "127.0.0.1"}
        for origin in origins
    ):
        errors.append("CORS_ORIGINS_STR должен содержать только production HTTPS origins")

    if _is_true(env.get("AI_ANALYSIS_ENABLED")):
        if not env.get("OPENROUTER_API_KEY"):
            errors.append("OPENROUTER_API_KEY обязателен при AI_ANALYSIS_ENABLED=true")
        if not _is_true(env.get("AI_ANALYSIS_ZDR_REQUIRED")):
            warnings.append("Для медицинских данных рекомендуется AI_ANALYSIS_ZDR_REQUIRED=true")

    if not env.get("BITRIX24_WEBHOOK_URL"):
        warnings.append("BITRIX24_WEBHOOK_URL не задан: исходящая CRM-интеграция отключена")

    return PreflightResult(tuple(errors), tuple(warnings))
