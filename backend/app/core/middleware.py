# ============================================
# Middleware безопасности
# ============================================
"""
Rate limiting и другие middleware для защиты API.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.redis import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting на уровне приложения через Redis.
    Дополняет nginx rate limiting для случаев обхода прокси.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем healthcheck и статику
        path = request.url.path
        if path in ("/health", "/", "/openapi.json") or path.startswith("/admin/statics"):
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
            # Админ-панель — защита от brute-force
            limit = 30
            window = 60
        else:
            # Остальные API — стандартный лимит
            limit = settings.RATE_LIMIT_PER_MINUTE
            window = 60
        
        try:
            allowed, remaining = await redis_client.check_rate_limit(
                identifier=f"{client_ip}:{path.split('/')[1]}",
                limit=limit,
                window=window,
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit превышен: IP={client_ip}, path={path}"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Слишком много запросов. Попробуйте позже."},
                    headers={"Retry-After": str(window)},
                )
        except Exception as e:
            # Если Redis недоступен — пропускаем (не блокируем запросы)
            logger.debug(f"Rate limit check failed (Redis): {e}")
        
        response = await call_next(request)
        return response
