# ============================================
# JWT утилиты
# ============================================
"""
Функции для работы с JWT токенами.
Используется для авторизации по Magic Link.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

from jose import JWTError, jwt
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings


class TokenPayload(BaseModel):
    """
    Структура данных в JWT токене.
    """
    lead_id: int  # ID сделки/лида в Битрикс24
    patient_name: Optional[str] = None  # Имя пациента для персонализации
    entity_type: str = "DEAL"  # Тип сущности: DEAL или LEAD
    exp: datetime  # Время истечения
    iat: datetime  # Время создания
    jti: str  # Уникальный ID токена (для инвалидации)


class TokenData(BaseModel):
    """
    Данные, извлечённые из токена после валидации.
    """
    lead_id: int
    patient_name: Optional[str] = None
    entity_type: str = "DEAL"
    token_hash: str  # Хэш для инвалидации


def create_access_token(
    lead_id: int,
    patient_name: Optional[str] = None,
    entity_type: str = "DEAL",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Создание JWT токена для Magic Link.
    
    Args:
        lead_id: ID сделки/лида в Битрикс24
        patient_name: Имя пациента
        entity_type: Тип сущности (DEAL/LEAD)
        expires_delta: Время жизни токена
        
    Returns:
        Закодированный JWT токен
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    # Генерация уникального ID токена (8 символов вместо 16 — экономия в JWT)
    jti = hashlib.sha256(
        f"{lead_id}:{now.isoformat()}:{settings.SECRET_KEY}".encode()
    ).hexdigest()[:8]
    
    # Компактный payload: короткие ключи для минимального размера токена
    payload = {
        "l": lead_id,           # lead_id
        "e": entity_type,       # entity_type
        "exp": expire,
        "iat": now,
        "jti": jti,
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    logger.info(f"Создан токен для lead_id={lead_id}, истекает {expire}")
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Валидация JWT токена.
    
    Args:
        token: JWT токен из URL
        
    Returns:
        TokenData если токен валиден, None если нет
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Извлечение данных (поддержка компактного и старого формата)
        lead_id = payload.get("l") or payload.get("lead_id")
        if lead_id is None:
            logger.warning("Токен не содержит lead_id")
            return None
        
        # Создание хэша для инвалидации
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        return TokenData(
            lead_id=lead_id,
            patient_name=payload.get("n") or payload.get("patient_name"),
            entity_type=payload.get("e") or payload.get("entity_type", "DEAL"),
            token_hash=token_hash,
        )
        
    except JWTError as e:
        logger.warning(f"Ошибка валидации токена: {e}")
        return None


def get_token_hash(token: str) -> str:
    """
    Получение хэша токена для инвалидации.
    
    Args:
        token: JWT токен
        
    Returns:
        SHA256 хэш токена
    """
    return hashlib.sha256(token.encode()).hexdigest()
