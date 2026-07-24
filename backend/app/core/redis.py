# ============================================
# Redis клиент
# ============================================
"""
Настройка подключения к Redis для хранения сессий и кэширования.
"""

import redis.asyncio as redis
from typing import Optional
import json
from loguru import logger

from app.core.config import settings


class RedisClient:
    """
    Асинхронный клиент Redis для работы с сессиями опроса.
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Установка соединения с Redis."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("🔴 Подключение к Redis установлено")
    
    async def disconnect(self) -> None:
        """Закрытие соединения с Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("🔴 Соединение с Redis закрыто")
    
    @property
    def client(self) -> redis.Redis:
        """Получение клиента Redis."""
        if self._redis is None:
            raise RuntimeError("Redis не подключен. Вызовите connect() сначала.")
        return self._redis
    
    # ==========================================
    # Методы для работы с сессиями опроса
    # ==========================================
    
    async def save_survey_progress(
        self,
        session_id: str,
        progress_data: dict,
        ttl: int = None,
    ) -> None:
        """
        Сохранение прогресса опроса.
        
        Args:
            session_id: ID сессии опроса
            progress_data: Данные прогресса (текущий узел, ответы, история)
            ttl: Время жизни в секундах (по умолчанию из настроек)
        """
        await self.connect()
        key = f"survey:progress:{session_id}"
        ttl = ttl or settings.SESSION_TTL
        
        await self.client.setex(
            key,
            ttl,
            json.dumps(progress_data, ensure_ascii=False),
        )
        logger.debug("Прогресс сессии сохранён")
    
    async def get_survey_progress(self, session_id: str) -> Optional[dict]:
        """
        Получение прогресса опроса.
        
        Args:
            session_id: ID сессии опроса
            
        Returns:
            Данные прогресса или None если сессия не найдена
        """
        await self.connect()
        key = f"survey:progress:{session_id}"
        
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def delete_survey_progress(self, session_id: str) -> None:
        """
        Удаление прогресса опроса (после завершения).
        
        Args:
            session_id: ID сессии опроса
        """
        await self.connect()
        key = f"survey:progress:{session_id}"
        await self.client.delete(key)
        logger.debug("Прогресс сессии удалён")
    
    # ==========================================
    # Методы для Rate Limiting
    # ==========================================
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = None,
        window: int = 60,
    ) -> tuple[bool, int]:
        """
        Проверка rate limit для IP или токена.
        
        Args:
            identifier: IP адрес или токен
            limit: Максимальное количество запросов
            window: Временное окно в секундах
            
        Returns:
            (allowed: bool, remaining: int)
        """
        await self.connect()
        limit = limit or settings.RATE_LIMIT_PER_MINUTE
        key = f"ratelimit:{identifier}"
        
        current = await self.client.get(key)
        
        if current is None:
            await self.client.setex(key, window, 1)
            return True, limit - 1
        
        current = int(current)
        if current >= limit:
            return False, 0
        
        await self.client.incr(key)
        return True, limit - current - 1
    
    # ==========================================
    # Методы для инвалидации токенов
    # ==========================================
    
    async def invalidate_token(self, token_hash: str, ttl: int = None) -> None:
        """
        Инвалидация токена (добавление в blacklist).
        
        Args:
            token_hash: Хэш токена
            ttl: Время хранения в blacklist
        """
        await self.connect()
        key = f"token:blacklist:{token_hash}"
        ttl = ttl or settings.SESSION_TTL
        await self.client.setex(key, ttl, "1")
        logger.info("Токен добавлен в blacklist")
    
    async def is_token_blacklisted(self, token_hash: str) -> bool:
        """
        Проверка, находится ли токен в blacklist.
        
        Args:
            token_hash: Хэш токена
            
        Returns:
            True если токен в blacklist
        """
        await self.connect()
        key = f"token:blacklist:{token_hash}"
        return await self.client.exists(key) > 0

    # ==========================================
    # Методы для коротких ссылок (short code → JWT)
    # ==========================================

    async def save_short_code(
        self,
        short_code: str,
        jwt_token: str,
        ttl: int = None,
    ) -> None:
        """
        Сохранение маппинга короткого кода на JWT токен.
        
        Args:
            short_code: Короткий код для URL (16 символов Base62)
            jwt_token: Полный JWT токен
            ttl: Время жизни в секундах (по умолчанию = JWT_EXPIRATION_HOURS)
        """
        await self.connect()
        key = f"link:{short_code}"
        if ttl is None:
            ttl = settings.JWT_EXPIRATION_HOURS * 3600
        
        await self.client.setex(key, ttl, jwt_token)
        logger.debug(f"Сохранён короткий код {short_code} (TTL={ttl}с)")

    async def get_jwt_by_short_code(self, short_code: str) -> Optional[str]:
        """
        Получение JWT токена по короткому коду.
        
        Args:
            short_code: Короткий код из URL
            
        Returns:
            JWT токен или None если код не найден / истёк
        """
        await self.connect()
        key = f"link:{short_code}"
        return await self.client.get(key)


# Глобальный экземпляр клиента
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Dependency для получения Redis клиента.
    """
    await redis_client.connect()
    return redis_client
