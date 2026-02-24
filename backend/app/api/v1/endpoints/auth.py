# ============================================
# Эндпоинты авторизации
# ============================================
"""
Валидация JWT токенов из Magic Link.
Поддерживает как короткие коды (из /s/{code}), так и прямые JWT (для обратной совместимости).
"""

import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis, RedisClient
from app.core.security import verify_token, create_access_token, generate_short_code
from app.core.log_utils import mask_name
from app.models import SurveySession
from app.schemas import TokenValidationResponse
from app.services.bitrix24 import Bitrix24Client

router = APIRouter()

# Паттерн короткого кода: только буквы и цифры, фиксированная длина
_SHORT_CODE_PATTERN = re.compile(r'^[a-zA-Z0-9]{12,24}$')


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Валидация токена из URL.
    
    Поддерживает два формата:
    - Короткий код (16 символов Base62) — новый формат из /s/{code}
    - Полный JWT токен — старый формат для обратной совместимости
    
    Проверяет:
    - Подпись токена (JWT)
    - Срок действия
    - Не в blacklist
    
    Returns:
        TokenValidationResponse с данными сессии
    """
    jwt_token = token  # По умолчанию считаем, что передан JWT
    
    # Определяем: это короткий код или JWT?
    # JWT всегда содержит точки (header.payload.signature), короткий код — нет
    if _SHORT_CODE_PATTERN.match(token) and '.' not in token:
        # Это короткий код — ищем JWT в Redis
        jwt_token = await redis.get_jwt_by_short_code(token)
        if jwt_token is None:
            logger.warning(f"Короткий код не найден или истёк: {token[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ссылка недействительна или срок её действия истёк",
            )
        logger.debug(f"Короткий код {token[:8]}... → JWT найден в Redis")
    
    # Декодирование и валидация JWT токена
    token_data = verify_token(jwt_token)
    
    if token_data is None:
        logger.warning("Попытка валидации невалидного токена")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ссылка недействительна или срок её действия истёк",
        )
    
    # Проверка в blacklist
    is_blacklisted = await redis.is_token_blacklisted(token_data.token_hash)
    if is_blacklisted:
        logger.warning(f"Токен в blacklist: lead_id={token_data.lead_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Эта ссылка уже была использована",
        )
    
    # Проверка существующей сессии
    stmt = select(SurveySession).where(
        SurveySession.token_hash == token_data.token_hash
    )
    result = await db.execute(stmt)
    existing_session = result.scalar_one_or_none()
    
    if existing_session:
        if existing_session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Опрос уже был завершён",
            )
        
        return TokenValidationResponse(
            valid=True,
            session_id=existing_session.id,
            patient_name=existing_session.patient_name,
            message="Сессия восстановлена",
            resolved_token=jwt_token if jwt_token != token else None,
        )
    
    # Если имя отсутствует в токене (компактный JWT) — загружаем из CRM
    patient_name = token_data.patient_name
    if not patient_name and settings.BITRIX24_WEBHOOK_URL:
        try:
            bitrix_client = Bitrix24Client()
            entity_type = token_data.entity_type or "DEAL"
            if entity_type == "DEAL":
                patient_name = await bitrix_client.get_patient_name_from_deal(token_data.lead_id)
            if patient_name:
                logger.info(f"Имя пациента загружено из CRM: {mask_name(patient_name)}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить имя из CRM: {e}")
    
    logger.info(f"Токен валиден: lead_id={token_data.lead_id}, patient={mask_name(patient_name)}")
    
    return TokenValidationResponse(
        valid=True,
        session_id=None,
        patient_name=patient_name,
        message="Токен действителен",
        resolved_token=jwt_token if jwt_token != token else None,
    )


@router.post("/generate-token")
async def generate_token(
    lead_id: int,
    patient_name: str = None,
    entity_type: str = "DEAL",
    redis: RedisClient = Depends(get_redis),
):
    """
    Генерация JWT токена для тестирования.
    
    ⚠️ ТОЛЬКО ДЛЯ РАЗРАБОТКИ! Недоступен в production.
    
    Args:
        lead_id: ID сделки/лида в Битрикс24
        patient_name: Имя пациента
        entity_type: Тип сущности (DEAL/LEAD)
        
    Returns:
        Короткий код, URL для прохождения опроса и полный JWT (для отладки)
    """
    from app.core.config import settings
    
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Этот эндпоинт доступен только в режиме разработки",
        )
    
    jwt_token = create_access_token(
        lead_id=lead_id,
        patient_name=patient_name,
        entity_type=entity_type,
    )
    
    # Генерация короткого кода и сохранение маппинга в Redis
    short_code = generate_short_code()
    await redis.save_short_code(short_code, jwt_token)
    
    return {
        "code": short_code,
        "url": f"{settings.FRONTEND_URL}/s/{short_code}",
        "expires_in_hours": settings.JWT_EXPIRATION_HOURS,
    }
