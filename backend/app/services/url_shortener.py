# ============================================
# URL Shortener - Сокращение ссылок
# ============================================
"""
Сервис для сокращения URL через внешние сервисы.
Используется для отправки ссылок в SMS (ограничение по длине).

Поддерживаемые провайдеры:
- Bit.ly (требуется API токен)
- Clck.ru (бесплатный, без регистрации)
"""

import httpx
from typing import Optional
from loguru import logger

from app.core.config import settings


async def shorten_url_bitly(long_url: str) -> str:
    """
    Сокращение URL через Bit.ly API.
    
    Требуется токен доступа: https://bitly.com/a/sign_up
    Добавьте в .env: BITLY_ACCESS_TOKEN=your_token_here
    
    Args:
        long_url: Полная ссылка для сокращения
        
    Returns:
        Короткая ссылка или оригинал при ошибке
    """
    bitly_token = getattr(settings, "BITLY_ACCESS_TOKEN", None)
    
    if not bitly_token:
        logger.debug("BITLY_ACCESS_TOKEN не настроен, пропуск сокращения")
        return long_url
    
    api_url = "https://api-ssl.bitly.com/v4/shorten"
    headers = {
        "Authorization": f"Bearer {bitly_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "long_url": long_url,
        "domain": "bit.ly",  # можно использовать кастомный домен
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            short_link = data.get("link")
            
            if short_link:
                logger.info(f"URL сокращён через Bit.ly: {long_url} -> {short_link}")
                return short_link
            
            logger.warning(f"Bit.ly не вернул короткую ссылку: {data}")
            return long_url
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка Bit.ly API (HTTP {e.response.status_code}): {e.response.text}")
        return long_url
    except Exception as e:
        logger.error(f"Ошибка при сокращении через Bit.ly: {e}")
        return long_url


async def shorten_url_clckru(long_url: str) -> str:
    """
    Сокращение URL через clck.ru (Яндекс).
    
    Бесплатный сервис, не требует регистрации и API-ключа.
    Подходит для российских проектов.
    
    Args:
        long_url: Полная ссылка для сокращения
        
    Returns:
        Короткая ссылка или оригинал при ошибке
    """
    api_url = "https://clck.ru/--"
    
    params = {"url": long_url}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            
            short_link = response.text.strip()
            
            # Проверка, что ответ выглядит как ссылка
            if short_link.startswith("http://clck.ru/") or short_link.startswith("https://clck.ru/"):
                logger.info(f"URL сокращён через clck.ru: {long_url} -> {short_link}")
                return short_link
            
            logger.warning(f"Неожиданный ответ clck.ru: {short_link}")
            return long_url
            
    except Exception as e:
        logger.error(f"Ошибка при сокращении через clck.ru: {e}")
        return long_url


async def shorten_url(long_url: str, provider: str = "clckru") -> str:
    """
    Универсальная функция сокращения URL.
    
    Args:
        long_url: Полная ссылка
        provider: Провайдер ('bitly' или 'clckru')
        
    Returns:
        Короткая ссылка
    """
    if provider == "bitly":
        return await shorten_url_bitly(long_url)
    else:
        return await shorten_url_clckru(long_url)


# ==========================================
# Пример использования
# ==========================================
"""
from app.services.url_shortener import shorten_url

# В эндпоинте генерации ссылки:
survey_url = f"{settings.FRONTEND_URL}/?token={token}"
short_url = await shorten_url(survey_url, provider="clckru")

# Записать в Битрикс24:
await bitrix_client.update_deal_field(
    deal_id=lead_id,
    fields={"UF_CRM_OPROS_LINK": short_url}
)
"""
