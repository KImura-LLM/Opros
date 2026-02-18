# ============================================
# Эндпоинты опроса
# ============================================
"""
API для прохождения опроса.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from datetime import timedelta

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis, RedisClient
from app.core.security import verify_token, get_token_hash
from app.core.log_utils import mask_name
from app.models import SurveyConfig, SurveySession, SurveyAnswer, AuditLog
from app.schemas import (
    SurveyStartRequest,
    SurveyStartResponse,
    SurveyAnswerRequest,
    SurveyAnswerResponse,
    SurveyProgressResponse,
    SurveyCompleteRequest,
    SurveyCompleteResponse,
    SurveyConfigResponse,
)
from app.services.survey_engine import SurveyEngine
from app.services.report_generator import ReportGenerator
from app.services.bitrix24 import Bitrix24Client

router = APIRouter()


# ==========================================
# Вспомогательная функция проверки владения сессией
# ==========================================

async def verify_session_owner(
    session: SurveySession,
    request: Request,
    redis: RedisClient,
) -> None:
    """
    Проверяет, что запрос исходит от владельца сессии.
    Использует token из заголовка X-Session-Token для проверки token_hash.
    
    Raises:
        HTTPException: Если токен не предоставлен или не совпадает
    """
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: отсутствует токен сессии",
        )
    
    # Проверяем, что хэш токена совпадает с хэшем, привязанным к сессии
    provided_hash = get_token_hash(session_token)
    if provided_hash != session.token_hash:
        logger.warning(
            f"Попытка доступа к чужой сессии {session.id}: "
            f"ожидаемый hash={session.token_hash[:8]}..., "
            f"предоставленный hash={provided_hash[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён: токен не принадлежит данной сессии",
        )


@router.get("/config", response_model=SurveyConfigResponse)
async def get_survey_config(
    db: AsyncSession = Depends(get_db),
):
    """
    Получение активной конфигурации опросника.
    
    Returns:
        JSON-структура опросника
    """
    stmt = select(SurveyConfig).where(SurveyConfig.is_active == True).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активный опросник не найден",
        )
    
    return SurveyConfigResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        version=config.version,
        json_config=config.json_config,
    )


@router.post("/start", response_model=SurveyStartResponse)
async def start_survey(
    data: SurveyStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Начало прохождения опроса.
    
    Создаёт сессию после подтверждения согласия на обработку ПДн.
    
    Args:
        data: Токен и согласие на обработку данных
        
    Returns:
        ID сессии и конфигурация опросника
    """
    # Валидация токена
    token_data = verify_token(data.token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )
    
    # Проверка согласия
    if not data.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо дать согласие на обработку персональных данных",
        )
    
    # Проверка blacklist
    if await redis.is_token_blacklisted(token_data.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ссылка уже была использована",
        )
    
    # Получение активного конфига
    stmt = select(SurveyConfig).where(SurveyConfig.is_active == True).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активный опросник не найден",
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
                detail="Опрос уже завершён",
            )
        
        # Восстановление сессии
        progress = await redis.get_survey_progress(str(existing_session.id))
        
        return SurveyStartResponse(
            session_id=existing_session.id,
            patient_name=existing_session.patient_name,
            survey_config=config.json_config,
            message="Сессия восстановлена. Продолжайте с того места, где остановились.",
        )
    
    # Создание новой сессии
    # Если имя отсутствует в токене (компактный JWT) — загружаем из CRM
    patient_name = token_data.patient_name
    if not patient_name and settings.BITRIX24_WEBHOOK_URL:
        try:
            bitrix_client = Bitrix24Client()
            entity_type = token_data.entity_type or "DEAL"
            if entity_type == "DEAL":
                patient_name = await bitrix_client.get_patient_name_from_deal(token_data.lead_id)
            if patient_name:
                logger.info(f"Имя пациента загружено из CRM при старте опроса: {mask_name(patient_name)}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить имя из CRM: {e}")
    
    # Получаем реальный IP клиента (учитываем прокси nginx)
    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    user_agent = request.headers.get("user-agent")
    
    # Установка времени истечения сессии (2 часа с момента создания)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    
    session = SurveySession(
        lead_id=token_data.lead_id,
        entity_type=token_data.entity_type,
        patient_name=patient_name,
        survey_config_id=config.id,
        token_hash=token_data.token_hash,
        status="in_progress",
        consent_given=True,
        consent_timestamp=datetime.now(timezone.utc),
        expires_at=expires_at,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    
    db.add(session)
    await db.flush()
    
    # Логирование
    audit_log = AuditLog(
        session_id=session.id,
        action="survey_started",
        details={"consent_given": True},
        ip_address=client_ip,
    )
    db.add(audit_log)
    await db.commit()
    
    # Инициализация прогресса в Redis
    start_node = config.json_config.get("start_node", "welcome")
    await redis.save_survey_progress(
        str(session.id),
        {
            "current_node": start_node,
            "answers": {},
            "history": [start_node],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    logger.info(f"Создана сессия {session.id} для lead_id={token_data.lead_id}")
    
    return SurveyStartResponse(
        session_id=session.id,
        patient_name=token_data.patient_name,
        survey_config=config.json_config,
        message="Опрос начат",
        expires_at=expires_at,
    )


@router.post("/answer", response_model=SurveyAnswerResponse)
async def submit_answer(
    data: SurveyAnswerRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Сохранение ответа на вопрос.
    
    Args:
        data: ID сессии, ID вопроса и ответ
        
    Returns:
        Следующий узел и прогресс
    """
    # Получение сессии
    stmt = select(SurveySession).where(SurveySession.id == data.session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    
    # Проверка владения сессией
    await verify_session_owner(session, request, redis)
    
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Опрос уже завершён",
        )
    
    # Проверка истечения срока сессии
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        session.status = "abandoned"
        await db.commit()
        
        logger.warning(f"Сессия {session.id} автоматически завершена по истечении времени")
        
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Время прохождения опроса истекло. Сессия была автоматически завершена.",
        )
    
    # Получение конфига
    stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    # Получение прогресса из Redis
    progress = await redis.get_survey_progress(str(session.id))
    if not progress:
        progress = {
            "current_node": config.json_config.get("start_node", "welcome"),
            "answers": {},
            "history": [],
        }
    
    # Сохранение ответа в БД
    existing_answer = await db.execute(
        select(SurveyAnswer).where(
            SurveyAnswer.session_id == session.id,
            SurveyAnswer.node_id == data.node_id,
        )
    )
    existing = existing_answer.scalar_one_or_none()
    
    if existing:
        existing.answer_data = data.answer_data
        existing.updated_at = datetime.now(timezone.utc)
    else:
        answer = SurveyAnswer(
            session_id=session.id,
            node_id=data.node_id,
            answer_data=data.answer_data,
        )
        db.add(answer)
    
    await db.commit()
    
    # Определение следующего узла через Survey Engine
    engine = SurveyEngine(config.json_config)
    next_node = engine.get_next_node(data.node_id, data.answer_data, progress["answers"])
    
    # Обновление прогресса
    progress["answers"][data.node_id] = data.answer_data
    progress["current_node"] = next_node
    if next_node and next_node not in progress["history"]:
        progress["history"].append(next_node)
    
    await redis.save_survey_progress(str(session.id), progress)
    
    # Расчёт прогресса в процентах
    # Используем эвристику, так как точную длину пути в ветвящемся опросе предсказать сложно
    is_finished = False
    if next_node:
        next_node_obj = engine.get_node(next_node)
        if next_node_obj and next_node_obj.get("is_final"):
            is_finished = True
    elif next_node is None:
        is_finished = True

    if is_finished:
        progress_percent = 100.0
    else:
        # Оценка средней длины пути зависит от версии опросника
        # v1 ≈ 5–7 узлов, v2 ≈ 12–18 узлов (с ветвлениями)
        total_nodes = len(config.json_config.get("nodes", []))
        # Исключаем info_screen из подсчёта, средний путь ~60% от общего числа узлов
        countable = [n for n in config.json_config.get("nodes", []) if n.get("type") != "info_screen"]
        ESTIMATED_PATH_LENGTH = max(5, int(len(countable) * 0.6))
        completed = len(progress["answers"])
        progress_percent = min(95.0, (completed / ESTIMATED_PATH_LENGTH) * 100)
    
    return SurveyAnswerResponse(
        success=True,
        next_node=next_node,
        progress=round(progress_percent, 1),
    )


@router.get("/progress/{session_id}", response_model=SurveyProgressResponse)
async def get_progress(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Получение текущего прогресса опроса.
    
    Args:
        session_id: ID сессии
        
    Returns:
        Текущий узел, ответы и история
    """
    # Проверка сессии
    stmt = select(SurveySession).where(SurveySession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    
    # Проверка владения сессией
    await verify_session_owner(session, request, redis)
    
    # Получение прогресса из Redis
    progress = await redis.get_survey_progress(str(session_id))
    
    if not progress:
        # Получение конфига для start_node
        stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        start_node = config.json_config.get("start_node", "welcome") if config else "welcome"
        
        progress = {
            "current_node": start_node,
            "answers": {},
            "history": [start_node],
        }
    
    # Расчёт процента
    stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    total_nodes = len(config.json_config.get("nodes", [])) if config else 1
    completed = len(progress.get("answers", {}))
    progress_percent = min(100, (completed / max(total_nodes, 1)) * 100)
    
    return SurveyProgressResponse(
        session_id=session_id,
        current_node=progress.get("current_node", "welcome"),
        history=progress.get("history", []),
        progress_percent=round(progress_percent, 1),
    )


@router.post("/complete", response_model=SurveyCompleteResponse)
async def complete_survey(
    data: SurveyCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Завершение опроса.
    
    Генерирует отчёт и отправляет в Битрикс24.
    
    Args:
        data: ID сессии
        
    Returns:
        Статус завершения и отправки отчёта
    """
    # Получение сессии
    stmt = select(SurveySession).where(SurveySession.id == data.session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    
    # Проверка владения сессией
    await verify_session_owner(session, request, redis)
    
    if session.status == "completed":
        return SurveyCompleteResponse(
            success=True,
            message="Опрос уже был завершён ранее",
            report_sent=True,
        )
    
    # Получение ответов
    stmt = select(SurveyAnswer).where(SurveyAnswer.session_id == session.id)
    result = await db.execute(stmt)
    answers = result.scalars().all()
    
    # Получение конфига
    stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    # Генерация отчёта
    report_gen = ReportGenerator(config.json_config if config else {})
    answers_dict = {a.node_id: a.answer_data for a in answers}
    
    bitrix_client = Bitrix24Client()
    report_sent = False
    
    # Генерация и отправка PDF-отчёта в карточку Битрикс24
    pdf_sent = False
    try:
        from weasyprint import HTML as WeasyHTML
        from io import BytesIO
        
        # Генерируем читаемый HTML для PDF
        readable_html = report_gen.generate_readable_html_report(
            patient_name=session.patient_name,
            answers=answers_dict,
        )
        
        # Конвертируем в PDF
        pdf_buffer = BytesIO()
        WeasyHTML(string=readable_html).write_pdf(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()
        
        # Формируем имя файла
        patient_safe = session.patient_name or "patient"
        patient_safe = "".join(c for c in patient_safe if c.isalnum() or c in (' ', '_')).strip()
        patient_safe = patient_safe.replace(" ", "_")
        date_str = datetime.now(timezone.utc).strftime("%d_%m_%Y")
        pdf_filename = f"Anketa_{patient_safe}_{date_str}.pdf"
        
        # Отправляем PDF в Битрикс24
        pdf_sent = await bitrix_client.upload_pdf_to_entity(
            entity_id=session.lead_id,
            entity_type=session.entity_type,
            pdf_bytes=pdf_bytes,
            filename=pdf_filename,
        )
        
        if pdf_sent:
            logger.info(f"PDF-отчёт отправлен в Битрикс24: lead_id={session.lead_id}")
            report_sent = True
        else:
            logger.warning(f"Не удалось отправить PDF в Битрикс24: lead_id={session.lead_id}")
            
    except ImportError:
        logger.warning("WeasyPrint не установлен, PDF-отчёт не будет отправлен")
    except Exception as e:
        logger.error(f"Ошибка генерации/отправки PDF в Битрикс24: {e}")
    
    # Если PDF не удалось отправить — отправляем текстовый комментарий как fallback
    if not pdf_sent:
        report_text = report_gen.generate_text_report(
            patient_name=session.patient_name,
            answers=answers_dict,
        )
        report_sent = await bitrix_client.send_comment(
            entity_id=session.lead_id,
            entity_type=session.entity_type,
            comment=report_text,
        )
    
    # Обновление статуса сессии
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    
    # Логирование
    audit_log = AuditLog(
        session_id=session.id,
        action="survey_completed",
        details={
            "answers_count": len(answers),
            "report_sent": report_sent,
            "pdf_sent": pdf_sent,
        },
    )
    db.add(audit_log)
    
    # Инвалидация токена
    await redis.invalidate_token(session.token_hash)
    
    # Удаление прогресса из Redis
    await redis.delete_survey_progress(str(session.id))
    
    await db.commit()
    
    logger.info(f"Опрос завершён: session_id={session.id}, lead_id={session.lead_id}")
    
    return SurveyCompleteResponse(
        success=True,
        message="Спасибо! Анкета заполнена. Данные переданы врачу.",
        report_sent=report_sent,
        pdf_sent=pdf_sent,
    )


class GoBackRequest(BaseModel):
    """Запрос на возврат к предыдущему вопросу."""
    session_id: UUID


@router.post("/back")
async def go_back(
    data: GoBackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Возврат на предыдущий вопрос.
    
    Args:
        data: ID сессии
        
    Returns:
        Предыдущий узел
    """
    # Проверка сессии в БД
    stmt = select(SurveySession).where(SurveySession.id == data.session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    
    # Проверка владения сессией
    await verify_session_owner(session, request, redis)
    
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Опрос уже завершён",
        )
    
    progress = await redis.get_survey_progress(str(data.session_id))
    
    if not progress or len(progress.get("history", [])) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно вернуться назад",
        )
    
    # Удаление текущего узла из истории
    history = progress["history"]
    current_node = history.pop()  # Удаляем текущий
    previous_node = history[-1] if history else "welcome"
    
    # Удаляем ответ на текущий вопрос из прогресса
    if current_node in progress.get("answers", {}):
        del progress["answers"][current_node]
    
    progress["current_node"] = previous_node
    progress["history"] = history
    
    await redis.save_survey_progress(str(data.session_id), progress)
    
    return {
        "success": True,
        "current_node": previous_node,
    }
