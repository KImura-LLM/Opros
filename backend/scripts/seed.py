"""
Seed скрипт для загрузки начальных данных в БД.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.models import SurveyConfig


async def seed_survey_config():
    """Загрузка JSON-структуры опросника в БД."""
    
    # Путь к файлу с конфигурацией
    config_path = Path(__file__).parent.parent / "data" / "survey_structure.json"
    
    if not config_path.exists():
        print(f"❌ Файл {config_path} не найден")
        return
    
    # Читаем JSON
    with open(config_path, "r", encoding="utf-8") as f:
        survey_data = json.load(f)
    
    async with async_session_maker() as session:
        # Проверяем, существует ли уже активная конфигурация
        result = await session.execute(
            select(SurveyConfig).where(SurveyConfig.is_active == True)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Деактивируем старую конфигурацию
            existing.is_active = False
            print(f"ℹ️ Деактивирована старая конфигурация: {existing.name} (v{existing.version})")
        
        # Создаём новую конфигурацию
        new_config = SurveyConfig(
            name=survey_data.get("title", "Опросник пациента"),
            description=survey_data.get("description"),
            version=survey_data.get("version", "1.0.0"),
            json_config=survey_data,
            is_active=True
        )
        
        session.add(new_config)
        await session.commit()
        
        print(f"✅ Загружена конфигурация: {new_config.name} (v{new_config.version})")


async def main():
    """Основная функция."""
    print("🌱 Запуск seed скрипта...")
    await seed_survey_config()
    print("✅ Seed завершён")


if __name__ == "__main__":
    asyncio.run(main())
