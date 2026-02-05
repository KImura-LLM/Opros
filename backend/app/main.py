# ============================================
# 🏥 Опросник пациента - FastAPI Backend
# ============================================
"""
Главный модуль приложения FastAPI.
Точка входа для запуска сервера.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from starlette.middleware.sessions import SessionMiddleware
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router
from app.admin.setup import setup_admin


# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO",
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
    await engine.dispose()


# Создание FastAPI приложения
app = FastAPI(
    title="Опросник пациента API",
    description="API для PWA-приложения сбора анамнеза пациентов",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
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

# Настройка сессий для админ-панели
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="admin_session",
    max_age=3600,  # 1 час
)

# Подключение роутеров API
app.include_router(api_router, prefix="/api/v1")

# Настройка Admin панели
setup_admin(app)


if settings.DEBUG:
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://unpkg.com/redoc@2.0.0-rc.77/bundles/redoc.standalone.js",
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
        "docs": "/docs" if settings.DEBUG else "Документация отключена в production",
    }
