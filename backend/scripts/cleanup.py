"""
Скрипт для очистки старых данных (выполняется по cron).
Соответствует требованиям 152-ФЗ: хранение персональных данных не более 24 часов.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.core.database import async_session_maker
from app.core.config import settings
from app.models.models import SurveySession, SurveyAnswer, AuditLog


async def cleanup_old_data():
    """Удаление данных старше 24 часов."""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.DATA_RETENTION_HOURS)
    
    async with async_session_maker() as session:
        # 1. Получаем старые сессии
        result = await session.execute(
            select(SurveySession.id).where(
                SurveySession.completed_at < cutoff_time
            )
        )
        old_session_ids = [row[0] for row in result.fetchall()]
        
        if not old_session_ids:
            print(f"ℹ️ Нет данных для удаления (старше {settings.DATA_RETENTION_HOURS} часов)")
            return
        
        # 2. Удаляем ответы старых сессий
        await session.execute(
            delete(SurveyAnswer).where(
                SurveyAnswer.session_id.in_(old_session_ids)
            )
        )
        
        # 3. Удаляем audit logs старых сессий
        await session.execute(
            delete(AuditLog).where(
                AuditLog.session_id.in_(old_session_ids)
            )
        )
        
        # 4. Удаляем сами сессии
        await session.execute(
            delete(SurveySession).where(
                SurveySession.id.in_(old_session_ids)
            )
        )
        
        await session.commit()
        
        print(f"✅ Удалено {len(old_session_ids)} сессий и связанных данных")


async def cleanup_expired_sessions():
    """Удаление незавершённых сессий с истёкшим токеном."""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=settings.JWT_EXPIRE_HOURS)
    
    async with async_session_maker() as session:
        # Находим незавершённые сессии старше времени жизни токена
        result = await session.execute(
            select(SurveySession.id).where(
                SurveySession.completed_at.is_(None),
                SurveySession.started_at < cutoff_time
            )
        )
        expired_session_ids = [row[0] for row in result.fetchall()]
        
        if not expired_session_ids:
            print("ℹ️ Нет незавершённых сессий с истёкшим токеном")
            return
        
        # Удаляем связанные данные
        await session.execute(
            delete(SurveyAnswer).where(
                SurveyAnswer.session_id.in_(expired_session_ids)
            )
        )
        
        await session.execute(
            delete(AuditLog).where(
                AuditLog.session_id.in_(expired_session_ids)
            )
        )
        
        await session.execute(
            delete(SurveySession).where(
                SurveySession.id.in_(expired_session_ids)
            )
        )
        
        await session.commit()
        
        print(f"✅ Удалено {len(expired_session_ids)} незавершённых сессий с истёкшим токеном")


async def main():
    """Основная функция."""
    print(f"🧹 Запуск очистки данных... ({datetime.utcnow().isoformat()})")
    
    await cleanup_old_data()
    await cleanup_expired_sessions()
    
    print("✅ Очистка завершена")


if __name__ == "__main__":
    asyncio.run(main())
