# ============================================
# Эндпоинты авторизации
# ============================================
"""
Валидация JWT токенов из Magic Link.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.core.redis import get_redis, RedisClient
from app.core.security import verify_token, get_token_hash, create_access_token
from app.models import SurveyConfig, SurveySession
from app.schemas import TokenValidationRequest, TokenValidationResponse

router = APIRouter()


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Валидация JWT токена из URL.
    
    Проверяет:
    - Подпись токена
    - Срок действия
    - Не в blacklist
    
    Returns:
        TokenValidationResponse с данными сессии
    """
    # Декодирование и валидация токена
    token_data = verify_token(token)
    
    if token_data is None:
        logger.warning(f"Невалидный токен: {token[:20]}...")
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
        )
    
    logger.info(f"Токен валиден: lead_id={token_data.lead_id}, patient={token_data.patient_name}")
    
    return TokenValidationResponse(
        valid=True,
        session_id=None,
        patient_name=token_data.patient_name,
        message="Токен действителен",
    )


@router.post("/generate-token")
async def generate_token(
    lead_id: int,
    patient_name: str = None,
    entity_type: str = "DEAL",
):
    """
    Генерация JWT токена для тестирования.
    
    ⚠️ ТОЛЬКО ДЛЯ РАЗРАБОТКИ! В продакшене этот эндпоинт должен быть защищён
    или вызываться только из Битрикс24.
    
    Args:
        lead_id: ID сделки/лида в Битрикс24
        patient_name: Имя пациента
        entity_type: Тип сущности (DEAL/LEAD)
        
    Returns:
        JWT токен и URL для прохождения опроса
    """
    from app.core.config import settings
    
    token = create_access_token(
        lead_id=lead_id,
        patient_name=patient_name,
        entity_type=entity_type,
    )
    
    return {
        "token": token,
        "url": f"{settings.FRONTEND_URL}/?token={token}",
        "expires_in_hours": settings.JWT_EXPIRATION_HOURS,
    }
