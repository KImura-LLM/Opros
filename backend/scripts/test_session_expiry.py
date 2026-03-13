"""
Тестовый скрипт для проверки автоматического истечения сессий.

Создаёт сессию с коротким временем истечения для тестирования.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import async_session_maker
from app.models.models import SurveySession
from sqlalchemy import select


async def create_test_session_with_short_expiry():
    """Создаёт тестовую сессию с истечением через 2 минуты."""
    async with async_session_maker() as db:
        # Создаём тестовую сессию
        session = SurveySession(
            lead_id=999999,
            patient_name="Тест - Короткая сессия",
            survey_config_id=1,
            token_hash="test_short_expiry",
            status="in_progress",
            consent_given=True,
            consent_timestamp=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            # Истекает через 2 минуты
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        print("✅ Создана тестовая сессия:")
        print(f"   ID: {session.id}")
        print(f"   Пациент: {session.patient_name}")
        print(f"   Создана: {session.started_at}")
        print(f"   Истекает: {session.expires_at}")
        print(f"   Статус: {session.status}")
        print("\n⏰ Сессия истечёт через 2 минуты")
        print("   Дождитесь следующего запуска фоновой очистки (каждые 15 мин)")
        print("   Или запустите вручную: docker compose exec backend python -m scripts.auto_expire_sessions")
        
        return session.id


async def check_session_status(session_id: str):
    """Проверяет статус сессии."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(SurveySession).where(SurveySession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            print(f"❌ Сессия {session_id} не найдена")
            return
        
        print(f"\n📊 Статус сессии {session_id}:")
        print(f"   Пациент: {session.patient_name}")
        print(f"   Статус: {session.status}")
        print(f"   Создана: {session.started_at}")
        print(f"   Истекает: {session.expires_at}")
        
        if session.expires_at:
            time_left = session.expires_at - datetime.now(timezone.utc)
            if time_left.total_seconds() > 0:
                print(f"   Осталось: {int(time_left.total_seconds())} секунд")
            else:
                print(f"   ⚠️ Истекла {abs(int(time_left.total_seconds()))} секунд назад")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Тест автоматического истечения сессий")
    parser.add_argument("--create", action="store_true", help="Создать тестовую сессию")
    parser.add_argument("--check", type=str, help="Проверить статус сессии по ID")
    
    args = parser.parse_args()
    
    if args.create:
        asyncio.run(create_test_session_with_short_expiry())
    elif args.check:
        asyncio.run(check_session_status(args.check))
    else:
        parser.print_help()
