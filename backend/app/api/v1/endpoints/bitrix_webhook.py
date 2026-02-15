# ============================================
# Эндпоинты вебхука Битрикс24
# ============================================
"""
Приём входящих запросов от Битрикс24.
Генерация Magic Link и возврат URL обратно в CRM.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.services.bitrix24 import Bitrix24Client


router = APIRouter()


# ==========================================
# Pydantic-схемы для Битрикс24 вебхуков
# ==========================================

class BitrixWebhookRequest(BaseModel):
    """
    Входящий запрос от Битрикс24 (из бизнес-процесса или роботов).
    
    Битрикс24 может отправлять данные как JSON или form-data.
    Поддерживаем оба варианта.
    """
    lead_id: int = Field(..., description="ID сделки или лида в Битрикс24")
    patient_name: Optional[str] = Field(None, description="ФИО пациента")
    entity_type: str = Field("DEAL", description="Тип сущности: DEAL или LEAD")
    auth_token: Optional[str] = Field(None, description="Токен авторизации для проверки подлинности")


class BitrixWebhookResponse(BaseModel):
    """Ответ на запрос от Битрикс24."""
    success: bool
    survey_url: str = Field(..., description="Ссылка на прохождение опроса")
    expires_in_hours: int = Field(..., description="Срок действия ссылки в часах")
    message: str


class BitrixWebhookErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    success: bool = False
    error: str
    error_code: str


# ==========================================
# Эндпоинты
# ==========================================

@router.post(
    "/webhook",
    response_model=BitrixWebhookResponse,
    responses={
        401: {"model": BitrixWebhookErrorResponse},
        400: {"model": BitrixWebhookErrorResponse},
    },
    summary="Генерация ссылки на опрос (вебхук от Битрикс24)",
)
async def bitrix_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Принимает запрос от Битрикс24 (робот / бизнес-процесс / REST-событие).
    
    **Сценарий использования:**
    1. В Битрикс24 создаётся сделка (лид) с данными пациента.
    2. Робот/бизнес-процесс отправляет POST-запрос на этот эндпоинт.
    3. Эндпоинт генерирует JWT-токен и формирует Magic Link.
    4. Ссылка возвращается в Битрикс24.
    5. Битрикс24 отправляет ссылку пациенту (SMS, email, мессенджер).
    
    **Поддерживаемые форматы входных данных:**
    - `application/json` — стандартный JSON
    - `application/x-www-form-urlencoded` — форма (Битрикс24 по умолчанию)
    
    Args:
        request: HTTP-запрос
        
    Returns:
        URL для прохождения опроса
    """
    # Парсинг входных данных (Битрикс24 может отправлять form-data или JSON)
    content_type = request.headers.get("content-type", "")
    
    try:
        if "application/json" in content_type:
            raw_data = await request.json()
        else:
            # Битрикс24 обычно отправляет form-data
            form = await request.form()
            raw_data = dict(form)
    except Exception as e:
        logger.error(f"Ошибка парсинга данных вебхука: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно прочитать данные запроса",
        )
    
    # Fallback для действий Битрикс24, где удобно передавать параметры только в URL (query string).
    # Если в теле и в query есть одинаковые ключи, приоритет у тела.
    query_data = dict(request.query_params)
    if query_data:
        raw_data = {**query_data, **raw_data}
    
    logger.info(f"Получен вебхук от Битрикс24: lead_id={raw_data.get('lead_id', raw_data.get('LEAD_ID', 'N/A'))}")
    
    # Извлечение параметров (поддержка разных форматов имён полей)
    lead_id = _extract_int(raw_data, ["lead_id", "LEAD_ID", "deal_id", "DEAL_ID", "entity_id", "ENTITY_ID"])
    patient_name = _extract_str(raw_data, ["patient_name", "PATIENT_NAME", "name", "NAME", "fio", "FIO"])
    entity_type = _extract_str(raw_data, ["entity_type", "ENTITY_TYPE"]) or "DEAL"
    auth_token = _extract_str(raw_data, ["auth_token", "AUTH_TOKEN", "token", "TOKEN", "auth"])
    category_id = _extract_str(raw_data, ["category_id", "CATEGORY_ID", "CATEGORY"])
    
    # Проверяем, передал ли Битрикс имя как нераскрытый шаблон ({{...}})
    if patient_name and ("{{" in patient_name or "%7B%7B" in patient_name.upper()):
        logger.warning(f"Получено нераскрытое имя шаблона: {patient_name}. Будет загружено из CRM.")
        patient_name = None
    
    # Валидация обязательных полей
    if lead_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан ID сделки/лида (lead_id)",
        )
    
    # Проверка токена авторизации (обязательна в production)
    if settings.BITRIX24_INCOMING_TOKEN:
        if auth_token != settings.BITRIX24_INCOMING_TOKEN:
            logger.warning(f"Неверный auth_token в вебхуке от Битрикс24. IP: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен авторизации",
            )
    elif settings.ENVIRONMENT == "production" or not settings.DEBUG:
        logger.error("BITRIX24_INCOMING_TOKEN не настроен в production!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сервер не настроен для приёма вебхуков",
        )
    
    # Нормализация entity_type
    entity_type = entity_type.upper()
    if entity_type not in ("DEAL", "LEAD"):
        entity_type = "DEAL"

    # Проверка категории воронки (если настроена фильтрация)
    if settings.BITRIX24_CATEGORY_ID:
        resolved_category_id = category_id

        # Если category_id не пришел из робота, пробуем получить его из CRM по ID сделки.
        if not resolved_category_id and entity_type == "DEAL" and settings.BITRIX24_WEBHOOK_URL:
            try:
                bitrix_client = Bitrix24Client()
                deal_data = await bitrix_client.get_deal(lead_id)
                if deal_data:
                    resolved_category_id = str(deal_data.get("CATEGORY_ID", "")).strip() or None
                    if resolved_category_id:
                        logger.info(
                            f"category_id не передан в вебхуке, загружен из CRM: "
                            f"deal_id={lead_id}, category_id={resolved_category_id}"
                        )
            except Exception as e:
                logger.warning(f"Не удалось получить CATEGORY_ID из CRM для сделки {lead_id}: {e}")

        if not resolved_category_id:
            logger.warning(
                f"Сделка {lead_id} не содержит category_id, но фильтрация включена. "
                f"Добавьте {{{{CATEGORY_ID}}}} в параметры робота Битрикс24."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указана категория воронки (category_id)",
            )

        if str(resolved_category_id) != str(settings.BITRIX24_CATEGORY_ID):
            logger.info(
                f"Сделка {lead_id} из категории {resolved_category_id} пропущена. "
                f"Обрабатываются только сделки из категории {settings.BITRIX24_CATEGORY_ID}."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Эта воронка не обрабатывается. Разрешена только категория {settings.BITRIX24_CATEGORY_ID}.",
            )
    
    # Если имя пациента не передано (или было шаблоном) — получаем из CRM
    if not patient_name and settings.BITRIX24_WEBHOOK_URL:
        bitrix_client = Bitrix24Client()
        if entity_type == "DEAL":
            patient_name = await bitrix_client.get_patient_name_from_deal(lead_id)
        if patient_name:
            logger.info(f"Имя пациента загружено из CRM: {patient_name}")
        else:
            logger.warning(f"Не удалось получить имя пациента из CRM для сделки {lead_id}")
    
    # Генерация JWT токена
    token = create_access_token(
        lead_id=lead_id,
        patient_name=patient_name,
        entity_type=entity_type,
    )
    
    # Формирование URL для прохождения опроса
    survey_url = f"{settings.FRONTEND_URL}/?token={token}"
    
    logger.info(
        f"Сгенерирована ссылка для опроса: "
        f"lead_id={lead_id}, patient={patient_name}, "
        f"entity_type={entity_type}"
    )
    
    # Автоматическая отправка ссылки в комментарий сделки/лида в Битрикс24
    if settings.BITRIX24_WEBHOOK_URL:
        bitrix_client = Bitrix24Client()
        patient_display = patient_name or "Пациент"
        comment_html = (
            f"🔗 <b>Ссылка на опрос для пациента:</b> {patient_display}<br><br>"
            f"<a href=\"{survey_url}\">{survey_url}</a><br><br>"
            f"⏰ Действительна {settings.JWT_EXPIRATION_HOURS} часов."
        )
        sent = await bitrix_client.send_comment(
            entity_id=lead_id,
            entity_type=entity_type,
            comment=comment_html,
        )
        if sent:
            logger.info(f"Ссылка на опрос записана в комментарий сделки {lead_id} в Битрикс24")
        else:
            logger.warning(f"Не удалось записать ссылку в комментарий сделки {lead_id}")
        
        # Запись ссылки в пользовательское поле UF_CRM_OPROS_LINK (для отправки через SMS/WhatsApp)
        if entity_type == "DEAL":
            updated = await bitrix_client.update_deal_field(
                deal_id=lead_id,
                fields={"UF_CRM_OPROS_LINK": survey_url}
            )
            if updated:
                logger.info(f"Ссылка записана в поле UF_CRM_OPROS_LINK сделки {lead_id}")
            else:
                logger.warning(
                    f"Не удалось записать ссылку в поле UF_CRM_OPROS_LINK. "
                    f"Проверьте, что поле создано в настройках CRM."
                )
    
    return BitrixWebhookResponse(
        success=True,
        survey_url=survey_url,
        expires_in_hours=settings.JWT_EXPIRATION_HOURS,
        message=f"Ссылка на опрос сгенерирована. Действительна {settings.JWT_EXPIRATION_HOURS} часов.",
    )


@router.post(
    "/webhook/generate-link",
    response_model=BitrixWebhookResponse,
    summary="Альтернативный эндпоинт генерации ссылки",
)
async def generate_survey_link(
    data: BitrixWebhookRequest,
    request: Request,
):
    """
    Явный эндпоинт для генерации ссылки с JSON-телом.
    
    Удобнее для тестирования и интеграции через REST API Битрикс24.
    
    Args:
        data: Валидированные данные запроса
        
    Returns:
        URL для прохождения опроса
    """
    # Проверка токена авторизации (обязательна в production)
    if settings.BITRIX24_INCOMING_TOKEN:
        if data.auth_token != settings.BITRIX24_INCOMING_TOKEN:
            logger.warning(f"Неверный auth_token. IP: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен авторизации",
            )
    elif settings.ENVIRONMENT == "production" or not settings.DEBUG:
        logger.error("BITRIX24_INCOMING_TOKEN не настроен в production!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сервер не настроен для приёма вебхуков",
        )
    
    # Нормализация entity_type
    entity_type = data.entity_type.upper()
    if entity_type not in ("DEAL", "LEAD"):
        entity_type = "DEAL"
    
    # Генерация JWT токена
    token = create_access_token(
        lead_id=data.lead_id,
        patient_name=data.patient_name,
        entity_type=entity_type,
    )
    
    survey_url = f"{settings.FRONTEND_URL}/?token={token}"
    
    logger.info(
        f"Сгенерирована ссылка (generate-link): "
        f"lead_id={data.lead_id}, patient={data.patient_name}"
    )
    
    return BitrixWebhookResponse(
        success=True,
        survey_url=survey_url,
        expires_in_hours=settings.JWT_EXPIRATION_HOURS,
        message=f"Ссылка на опрос сгенерирована. Действительна {settings.JWT_EXPIRATION_HOURS} часов.",
    )


# ==========================================
# Вспомогательные функции парсинга
# ==========================================

def _extract_int(data: dict, keys: list) -> Optional[int]:
    """Извлечение целого числа из словаря по списку возможных ключей."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                continue
    return None


def _extract_str(data: dict, keys: list) -> Optional[str]:
    """Извлечение строки из словаря по списку возможных ключей."""
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None
