# ============================================
# Middleware безопасности
# ============================================
"""
Rate limiting и другие middleware для защиты API.
"""

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.redis import redis_client


def _rate_limit_bucket(path: str) -> str:
    """
    Группирует лимиты достаточно крупно для защиты, но не смешивает
    независимые админские разделы в один общий `/api` bucket.
    """
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "root"
    if parts[0] == "api" and len(parts) >= 3:
        return ":".join(parts[:3])
    return parts[0]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting на уровне приложения через Redis.
    Дополняет nginx rate limiting для случаев обхода прокси.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем healthcheck и статику
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or path in ("/health", "/health/live", "/health/ready", "/", "/openapi.json")
            or path.startswith("/admin/statics")
        ):
            return await call_next(request)
        
        # Определяем IP клиента
        client_ip = (
            request.headers.get("X-Real-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        
        # Определяем лимит в зависимости от типа эндпоинта
        if path.startswith("/api/v1/bitrix"):
            # Вебхуки Битрикс24 — строгий лимит
            limit = 30
            window = 60
        elif path.startswith("/api/v1/auth"):
            # Авторизация — защита от brute-force
            limit = 20
            window = 60
        elif path.startswith("/admin"):
            # Админ-панель делает несколько параллельных запросов на страницы,
            # действия и служебные эндпоинты; brute-force защищает /api/v1/auth.
            limit = 180
            window = 60
        elif path.startswith("/api/v1/reports"):
            # Просмотр/экспорт отчёта из админки может быстро открыть preview,
            # polling AI-статуса и несколько export endpoints.
            limit = 180
            window = 60
        elif path.startswith(("/api/v1/editor", "/api/v1/routing")):
            # Визуальный редактор и маршрутизатор грузят справочники, структуру,
            # правила и CRM-поля серией запросов из админского UI.
            limit = 180
            window = 60
        else:
            # Остальные API — стандартный лимит
            limit = settings.RATE_LIMIT_PER_MINUTE
            window = 60
        
        try:
            allowed, remaining = await redis_client.check_rate_limit(
                identifier=f"{client_ip}:{_rate_limit_bucket(path)}",
                limit=limit,
                window=window,
            )
            
            if not allowed:
                logger.warning(f"Rate limit превышен для bucket={_rate_limit_bucket(path)}")
                headers = {"Retry-After": str(window)}
                origin = request.headers.get("Origin")
                if origin in settings.CORS_ORIGINS:
                    headers["Access-Control-Allow-Origin"] = origin
                    headers["Access-Control-Allow-Credentials"] = "true"
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Слишком много запросов. Попробуйте позже."},
                    headers=headers,
                )
        except Exception as e:
            # Если Redis недоступен — пропускаем (не блокируем запросы)
            logger.debug(f"Rate limit check failed (Redis): {type(e).__name__}")
        
        response = await call_next(request)
        return response
