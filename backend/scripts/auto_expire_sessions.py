#!/usr/bin/env python3
# ============================================
# Скрипт автоматической очистки истекших сессий
# ============================================
"""
Периодически завершает сессии, время которых истекло.
Запускается как фоновая задача или через cron.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import async_session_maker
from app.models import SurveySession


async def cleanup_expired_sessions() -> int:
    """
    Завершает истекшие сессии (меняет статус на 'abandoned').
    
    Returns:
        Количество завершённых сессий
    """
    async with async_session_maker() as db:
        try:
            # Находим все незавершённые сессии с истёкшим временем
            now = datetime.now(timezone.utc)
            
            stmt = select(SurveySession).where(
                SurveySession.status == "in_progress",
                SurveySession.expires_at.isnot(None),
                SurveySession.expires_at < now
            )
            
            result = await db.execute(stmt)
            expired_sessions = result.scalars().all()
            
            if not expired_sessions:
                logger.info("Нет истёкших сессий для очистки")
                return 0
            
            # Обновляем статус
            session_ids = [s.id for s in expired_sessions]
            
            update_stmt = (
                update(SurveySession)
                .where(SurveySession.id.in_(session_ids))
                .values(
                    status="abandoned",
                    completed_at=now
                )
            )
            
            await db.execute(update_stmt)
            await db.commit()
            
            count = len(expired_sessions)
            logger.info(f"Автоматически завершено {count} истёкших сессий")
            
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке истёкших сессий: {e}")
            await db.rollback()
            return 0


async def run_periodic_cleanup(interval_minutes: int = 15):
    """
    Запускает периодическую очистку.
    
    Args:
        interval_minutes: Интервал между проверками в минутах
    """
    logger.info(f"Запуск периодической очистки истёкших сессий (каждые {interval_minutes} мин)")
    
    while True:
        try:
            await cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Критическая ошибка в процессе очистки: {e}")
        
        # Ждём до следующей проверки
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    # Запуск как отдельный процесс
    asyncio.run(run_periodic_cleanup(interval_minutes=15))
