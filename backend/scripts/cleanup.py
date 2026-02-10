"""
Скрипт для очистки старых данных (выполняется по cron).
Соответствует требованиям 152-ФЗ: хранение персональных данных не более 24 часов.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.config import settings
from app.models.models import SurveySession


async def cleanup_old_data():
    """Удаление данных старше 24 часов."""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.DATA_RETENTION_HOURS)
    
    async with async_session_maker() as session:
        # 1. Получаем старые завершённые сессии
        result = await session.execute(
            select(SurveySession).where(
                SurveySession.status == "completed",
                # Учитываем и completed_at и started_at для надёжности
                (
                    (SurveySession.completed_at < cutoff_time) |
                    (
                        SurveySession.completed_at.is_(None) &
                        (SurveySession.started_at < cutoff_time)
                    )
                ),
            )
        )
        old_sessions = result.scalars().all()
        
        if not old_sessions:
            print(f"ℹ️ Нет данных для удаления (старше {settings.DATA_RETENTION_HOURS} часов)")
            return
        
        # Удаляем сессии — связанные записи удалятся каскадно
        for s in old_sessions:
            await session.delete(s)
        
        await session.commit()
        
        print(f"✅ Удалено {len(old_sessions)} сессий и связанных данных (каскадно)")


async def cleanup_expired_sessions():
    """Удаление незавершённых сессий с истёкшим токеном."""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.JWT_EXPIRE_HOURS)
    
    async with async_session_maker() as session:
        # Находим незавершённые сессии старше времени жизни токена
        result = await session.execute(
            select(SurveySession).where(
                SurveySession.completed_at.is_(None),
                SurveySession.status != "completed",
                SurveySession.started_at < cutoff_time
            )
        )
        expired_sessions = result.scalars().all()
        
        if not expired_sessions:
            print("ℹ️ Нет незавершённых сессий с истёкшим токеном")
            return
        
        # Удаляем сессии — связанные записи удалятся каскадно
        for s in expired_sessions:
            await session.delete(s)
        
        await session.commit()
        
        print(f"✅ Удалено {len(expired_sessions)} незавершённых сессий с истёкшим токеном")


async def main():
    """Основная функция."""
    print(f"🧹 Запуск очистки данных... ({datetime.utcnow().isoformat()})")
    
    await cleanup_old_data()
    await cleanup_expired_sessions()
    
    print("✅ Очистка завершена")


if __name__ == "__main__":
    asyncio.run(main())
