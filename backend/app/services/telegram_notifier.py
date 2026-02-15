# ============================================
# Telegram Notifier - Отправка уведомлений
# ============================================
"""
Сервис для отправки уведомлений пациентам через Telegram Bot API.

Использование:
1. Создайте бота через @BotFather в Telegram
2. Получите токен бота
3. Добавьте в .env: TELEGRAM_BOT_TOKEN=your_bot_token
4. В Битрикс24 создайте поле UF_CRM_TELEGRAM_ID для хранения Telegram ID пациентов
"""

import httpx
from typing import Optional
from loguru import logger

from app.core.config import settings


async def send_telegram_message(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
) -> bool:
    """
    Отправка текстового сообщения через Telegram Bot API.
    
    Args:
        chat_id: Telegram ID пользователя или группы
        text: Текст сообщения (поддерживается HTML или Markdown)
        parse_mode: Режим форматирования ('HTML', 'Markdown', или None)
        disable_web_page_preview: Отключить превью ссылок
        
    Returns:
        True если сообщение отправлено успешно
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен, пропуск отправки")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Telegram сообщение отправлено: chat_id={chat_id}")
                return True
            else:
                logger.error(f"Ошибка Telegram API: {result}")
                return False
                
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP ошибка при отправке в Telegram: "
            f"status={e.response.status_code}, text={e.response.text}"
        )
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке в Telegram: {e}")
        return False


async def send_survey_link_telegram(
    chat_id: str | int,
    patient_name: str,
    survey_url: str,
) -> bool:
    """
    Отправка ссылки на опрос в Telegram с форматированием.
    
    Args:
        chat_id: Telegram ID пациента
        patient_name: Имя пациента
        survey_url: Ссылка на опрос
        
    Returns:
        True если отправлено успешно
    """
    message = (
        f"👋 Здравствуйте, <b>{patient_name}</b>!\n\n"
        f"Пожалуйста, пройдите медицинский опрос перед приёмом:\n\n"
        f"🔗 <a href=\"{survey_url}\">Перейти к опросу</a>\n\n"
        f"⏱ Это займёт 3-5 минут.\n\n"
        f"Спасибо!"
    )
    
    return await send_telegram_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


async def get_telegram_id_from_bitrix(deal_id: int) -> Optional[str]:
    """
    Получение Telegram ID пациента из пользовательского поля сделки в Битрикс24.
    
    Требуется создать поле UF_CRM_TELEGRAM_ID в настройках CRM.
    
    Args:
        deal_id: ID сделки
        
    Returns:
        Telegram ID или None
    """
    from app.services.bitrix24 import Bitrix24Client
    
    bitrix_client = Bitrix24Client()
    deal_data = await bitrix_client.get_deal(deal_id)
    
    if not deal_data:
        logger.warning(f"Не удалось получить данные сделки {deal_id} из Битрикс24")
        return None
    
    telegram_id = deal_data.get("UF_CRM_TELEGRAM_ID")
    
    if telegram_id:
        logger.info(f"Telegram ID получен из сделки {deal_id}: {telegram_id}")
        return str(telegram_id).strip()
    
    logger.debug(f"У сделки {deal_id} не заполнен Telegram ID")
    return None


# ==========================================
# Интеграция с вебхук-эндпоинтом
# ==========================================
"""
Добавьте в backend/app/api/v1/endpoints/bitrix_webhook.py после генерации ссылки:

# Отправка в Telegram (если настроен Telegram ID)
telegram_id = await get_telegram_id_from_bitrix(lead_id)
if telegram_id:
    from app.services.telegram_notifier import send_survey_link_telegram
    
    sent = await send_survey_link_telegram(
        chat_id=telegram_id,
        patient_name=patient_name or "Пациент",
        survey_url=survey_url,
    )
    
    if sent:
        logger.info(f"Ссылка отправлена пациенту в Telegram: {telegram_id}")
"""


# ==========================================
# Создание Telegram бота - инструкция
# ==========================================
"""
1. Откройте Telegram и найдите @BotFather
2. Отправьте команду: /newbot
3. Следуйте инструкциям:
   - Введите имя бота (например, "Клиника Здоровье Опрос")
   - Введите username (например, "zdorovie_opros_bot")
4. Скопируйте токен, который выдаст BotFather
5. Добавьте в .env:
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

6. Чтобы получить Telegram ID пациента:
   Вариант А: Пациент отправляет /start боту, бот сохраняет chat_id в CRM
   Вариант Б: Используйте бота @userinfobot — пациент отправляет ему любое сообщение, 
              бот отвечает с его ID

7. Сохраните ID в поле UF_CRM_TELEGRAM_ID в карточке контакта в Битрикс24
"""
