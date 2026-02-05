# ============================================
# Подключение к базе данных
# ============================================
"""
Настройка SQLAlchemy Async для работы с PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings


# Создание асинхронного движка
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Логирование SQL запросов в debug режиме
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
    pool_pre_ping=True,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Базовый класс для моделей
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии базы данных.
    Используется в FastAPI эндпоинтах.
    
    Пример использования:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
