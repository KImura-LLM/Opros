# ============================================
# 🏥 Опросник пациента - FastAPI Backend
# ============================================
"""
Главный модуль приложения FastAPI.
Точка входа для запуска сервера.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_client
from app.api.v1.router import api_router
from app.admin.setup import setup_admin
from app.core.middleware import RateLimitMiddleware


# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO",
)

# Добавляем логирование в файл для админки
import os
logs_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(logs_dir, exist_ok=True)
logger.add(
    os.path.join(logs_dir, "app.log"),
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    encoding="utf-8"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.
    Выполняется при старте и остановке.
    """
    logger.info("🚀 Запуск приложения Опросник пациента...")
    
    # Создание таблиц (только для разработки, в продакшене используем миграции)
    if settings.DEBUG:
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)  # Раскомментировать для сброса
            await conn.run_sync(Base.metadata.create_all)
        logger.info("📦 Таблицы базы данных созданы/проверены")
    
    yield
    
    logger.info("👋 Остановка приложения...")
    await redis_client.disconnect()
    await engine.dispose()


# Документация API управляется отдельным флагом, чтобы ее можно было
# включать на сервере без перевода всего приложения в DEBUG.
api_docs_enabled = settings.DEBUG or settings.ENABLE_API_DOCS

# Создание FastAPI приложения
app = FastAPI(
    title="Опросник пациента API",
    description="API для PWA-приложения сбора анамнеза пациентов",
    version="1.0.0",
    docs_url="/docs" if api_docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if api_docs_enabled else None,
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting на уровне приложения (дополняет nginx)
app.add_middleware(RateLimitMiddleware)

# Доверенные прокси — чтобы X-Forwarded-Proto корректно передавался
# и SQLAdmin генерировал https:// ссылки за Nginx
# Примечание: uvicorn 0.27 не поддерживает CIDR, используем "*"
# Безопасно — приложение доступно только через nginx (expose, не ports)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Настройка сессий для админ-панели
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="admin_session",
    max_age=3600,  # 1 час
    # lax — стандарт для admin-панелей: защищает от CSRF,
    # но не ломает redirect-цепочки POST→303→GET в браузерах
    same_site="lax",
    https_only=not settings.DEBUG,
)

# Подключение роутеров API
app.include_router(api_router, prefix="/api/v1")

# Настройка Admin панели
setup_admin(app)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """Кастомный ReDoc с фиксированной стабильной версией (без @next)"""
    if not app.openapi_url:
        raise HTTPException(status_code=404, detail="API docs are disabled")

    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Проверка работоспособности сервиса.
    Используется для healthcheck в Docker.
    """
    return {
        "status": "healthy",
        "service": "opros-backend",
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Корневой эндпоинт.
    """
    return {
        "message": "Опросник пациента API",
        "docs": "/docs" if api_docs_enabled else "Документация отключена",
    }
