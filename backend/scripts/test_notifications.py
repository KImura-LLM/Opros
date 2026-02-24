# ============================================
# Тестовый скрипт для проверки отправки
# ============================================
"""
Скрипт для тестирования отправки уведомлений через различные каналы.

Использование:
    python backend/scripts/test_notifications.py --channel telegram --chat-id 123456789
    python backend/scripts/test_notifications.py --channel url-shortener --url "https://example.com/long-url"
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.services.telegram_notifier import send_telegram_message, send_survey_link_telegram
from app.services.url_shortener import shorten_url


async def test_telegram(chat_id: str):
    """Тест отправки в Telegram"""
    print(f"\n🔹 Тестирование Telegram Bot API")
    print(f"   Chat ID: {chat_id}")
    print(f"   Token: {settings.TELEGRAM_BOT_TOKEN[:10]}..." if settings.TELEGRAM_BOT_TOKEN else "   Token: НЕ НАСТРОЕН")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("   ❌ TELEGRAM_BOT_TOKEN не установлен в .env")
        return
    
    test_message = (
        "🧪 <b>Тестовое сообщение</b>\n\n"
        "Это тест отправки уведомлений из системы Опросник.\n\n"
        "✅ Если вы видите это сообщение — интеграция работает!"
    )
    
    success = await send_telegram_message(chat_id=chat_id, text=test_message)
    
    if success:
        print("   ✅ Сообщение успешно отправлено!")
    else:
        print("   ❌ Ошибка при отправке")


async def test_url_shortener(url: str, provider: str = None):
    """Тест сокращения URL"""
    provider = provider or settings.URL_SHORTENER_PROVIDER
    
    print(f"\n🔹 Тестирование сокращения URL")
    print(f"   Провайдер: {provider}")
    print(f"   Оригинальная ссылка: {url}")
    
    short_url = await shorten_url(url, provider=provider)
    
    print(f"   Короткая ссылка: {short_url}")
    
    if short_url != url:
        print(f"   ✅ Ссылка успешно сокращена! (экономия: {len(url) - len(short_url)} символов)")
    else:
        print(f"   ⚠️  Ссылка не сокращена (используется оригинал)")


async def test_survey_link_telegram(chat_id: str):
    """Тест отправки ссылки на опрос в Telegram"""
    print(f"\n🔹 Тестирование отправки ссылки на опрос")
    
    test_url = f"{settings.FRONTEND_URL}/s/testCode1234abcd"
    
    success = await send_survey_link_telegram(
        chat_id=chat_id,
        patient_name="Иван Иванович Тестовый",
        survey_url=test_url,
    )
    
    if success:
        print("   ✅ Ссылка на опрос отправлена!")
    else:
        print("   ❌ Ошибка при отправке")


async def main():
    parser = argparse.ArgumentParser(description="Тестирование каналов отправки уведомлений")
    parser.add_argument(
        "--channel",
        choices=["telegram", "url-shortener", "survey-telegram", "all"],
        default="all",
        help="Канал для тестирования",
    )
    parser.add_argument("--chat-id", help="Telegram Chat ID (для telegram)")
    parser.add_argument("--url", help="URL для сокращения (для url-shortener)")
    parser.add_argument("--provider", choices=["bitly", "clckru"], help="Провайдер сокращения URL")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ КАНАЛОВ ОТПРАВКИ УВЕДОМЛЕНИЙ")
    print("=" * 60)
    
    if args.channel in ("telegram", "all"):
        if args.chat_id:
            await test_telegram(args.chat_id)
        else:
            print("\n⚠️  Для теста Telegram укажите --chat-id")
    
    if args.channel in ("survey-telegram", "all"):
        if args.chat_id:
            await test_survey_link_telegram(args.chat_id)
        else:
            print("\n⚠️  Для теста отправки опроса укажите --chat-id")
    
    if args.channel in ("url-shortener", "all"):
        test_url = args.url or f"{settings.FRONTEND_URL}/s/testLongCode1234"
        await test_url_shortener(test_url, args.provider)
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
