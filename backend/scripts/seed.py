"""
Seed скрипт для загрузки начальных данных в БД.

Использование:
    python -m scripts.seed           # Загрузка v2 (по умолчанию)
    python -m scripts.seed --v1      # Загрузка v1
    python -m scripts.seed --v2      # Загрузка v2
    python -m scripts.seed --all     # Загрузка обеих версий (v2 активна)
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.models import SurveyConfig

# Маппинг версий на файлы
SURVEY_FILES = {
    "v1": "survey_structure.json",
    "v2": "survey_structure_v2.json",
}


async def seed_survey_config(version: str = "v2", activate: bool = True):
    """
    Загрузка JSON-структуры опросника в БД.
    
    Args:
        version: Версия опросника ("v1" или "v2")
        activate: Сделать эту конфигурацию активной
    """
    filename = SURVEY_FILES.get(version)
    if not filename:
        print(f"❌ Неизвестная версия: {version}. Доступны: {', '.join(SURVEY_FILES.keys())}")
        return
    
    # Путь к файлу с конфигурацией
    config_path = Path(__file__).parent.parent / "data" / filename
    
    if not config_path.exists():
        print(f"❌ Файл {config_path} не найден")
        return
    
    # Читаем JSON
    with open(config_path, "r", encoding="utf-8") as f:
        survey_data = json.load(f)
    
    async with async_session_maker() as session:
        if activate:
            # Деактивируем все текущие активные конфигурации
            result = await session.execute(
                select(SurveyConfig).where(SurveyConfig.is_active == True)
            )
            existing_configs = result.scalars().all()
            
            for existing in existing_configs:
                existing.is_active = False
                print(f"ℹ️ Деактивирована конфигурация: {existing.name} (v{existing.version})")
        
        # Проверяем, нет ли уже такой версии в БД
        result = await session.execute(
            select(SurveyConfig).where(
                SurveyConfig.version == survey_data.get("version", "1.0")
            )
        )
        existing_version = result.scalar_one_or_none()
        
        if existing_version:
            # Обновляем существующую конфигурацию
            existing_version.name = survey_data.get("name", "Опросник пациента")
            existing_version.description = survey_data.get("description")
            existing_version.json_config = survey_data
            existing_version.is_active = activate
            print(f"🔄 Обновлена конфигурация: {existing_version.name} (v{existing_version.version})")
        else:
            # Создаём новую конфигурацию
            new_config = SurveyConfig(
                name=survey_data.get("name", "Опросник пациента"),
                description=survey_data.get("description"),
                version=survey_data.get("version", "1.0"),
                json_config=survey_data,
                is_active=activate,
            )
            session.add(new_config)
            print(f"✅ Загружена конфигурация: {new_config.name} (v{new_config.version})")
        
        await session.commit()


async def main():
    """Основная функция с поддержкой аргументов командной строки."""
    args = sys.argv[1:]
    
    if "--all" in args:
        # Загружаем обе версии, v2 активна
        print("🌱 Загрузка всех версий опросника...")
        await seed_survey_config(version="v1", activate=False)
        await seed_survey_config(version="v2", activate=True)
    elif "--v1" in args:
        print("🌱 Загрузка опросника v1...")
        await seed_survey_config(version="v1", activate=True)
    else:
        # По умолчанию — v2
        print("🌱 Загрузка опросника v2...")
        await seed_survey_config(version="v2", activate=True)
    
    print("✅ Seed завершён")


if __name__ == "__main__":
    asyncio.run(main())
