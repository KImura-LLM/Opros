# ============================================
# Конфигурация приложения
# ============================================
"""
Настройки приложения из переменных окружения.
Использует Pydantic Settings для валидации.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Настройки приложения.
    Все значения загружаются из переменных окружения или .env файла.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Общие настройки
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    
    # База данных PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "opros_user"
    POSTGRES_PASSWORD: str = "opros_password"
    POSTGRES_DB: str = "opros_db"
    
    @property
    def DATABASE_URL(self) -> str:
        """Формирование URL подключения к PostgreSQL."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    @property
    def REDIS_URL(self) -> str:
        """Формирование URL подключения к Redis."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # Сессии
    SESSION_TTL: int = 86400  # 24 часа в секундах
    
    # JWT
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 48
    
    # Битрикс24
    BITRIX24_WEBHOOK_URL: str = ""  # Исходящий вебхук (для отправки данных В Битрикс24)
    BITRIX24_INCOMING_TOKEN: str = ""  # Токен для проверки входящих запросов ОТ Битрикс24
    BITRIX24_ALLOWED_CATEGORIES: str = ""  # Разрешённые ID воронок через запятую (например "19,25"). Пусто = все воронки.
    BITRIX24_DEFAULT_RESPONSIBLE_ID: int = 0  # Дефолтный ответственный для дела, если не удалось получить из сделки (0 = не задавать)
    
    @property
    def ALLOWED_CATEGORY_IDS(self) -> List[str]:
        """Парсинг списка разрешённых воронок."""
        if not self.BITRIX24_ALLOWED_CATEGORIES:
            return []
        return [c.strip() for c in self.BITRIX24_ALLOWED_CATEGORIES.split(",") if c.strip()]
    
    # Сокращение URL (для SMS)
    BITLY_ACCESS_TOKEN: str = ""  # Токен Bit.ly API (опционально)
    URL_SHORTENER_PROVIDER: str = "clckru"  # 'bitly' или 'clckru'
    
    # Telegram Bot (для отправки уведомлений)
    TELEGRAM_BOT_TOKEN: str = ""  # Токен бота от @BotFather (опционально)
    
    # CORS
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Парсинг списка разрешённых origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",")]
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Логи и данные (для очистки по 152-ФЗ)
    AUDIT_LOG_RETENTION_HOURS: int = 24
    DATA_RETENTION_HOURS: int = 24  # Хранение персональных данных
    
    @property
    def JWT_EXPIRE_HOURS(self) -> int:
        """Alias для JWT_EXPIRATION_HOURS."""
        return self.JWT_EXPIRATION_HOURS


@lru_cache()
def get_settings() -> Settings:
    """
    Получение настроек приложения (с кэшированием).
    Проверяет критические настройки безопасности в production.
    """
    s = Settings()
    
    # Проверка критических настроек безопасности — ВСЕГДА, не только в production
    insecure_defaults = []
    
    if s.SECRET_KEY == "change-me-in-production":
        insecure_defaults.append("SECRET_KEY")
    if s.JWT_SECRET_KEY == "jwt-secret-change-me":
        insecure_defaults.append("JWT_SECRET_KEY")
    if s.ADMIN_PASSWORD == "admin":
        insecure_defaults.append("ADMIN_PASSWORD")
    if s.ADMIN_USERNAME == "admin":
        insecure_defaults.append("ADMIN_USERNAME")
    if s.POSTGRES_PASSWORD == "opros_password":
        insecure_defaults.append("POSTGRES_PASSWORD")
    
    if insecure_defaults:
        if s.ENVIRONMENT == "production" or not s.DEBUG:
            raise ValueError(
                f"КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ: В production используются дефолтные значения: "
                f"{', '.join(insecure_defaults)}. "
                f"Установите безопасные значения в переменных окружения или .env файле."
            )
        else:
            import warnings
            warnings.warn(
                f"⚠️ ВНИМАНИЕ: Используются небезопасные дефолтные значения: "
                f"{', '.join(insecure_defaults)}. "
                f"Обязательно замените перед деплоем в production!",
                stacklevel=2,
            )
    
    return s


# Глобальный экземпляр настроек
settings = get_settings()
