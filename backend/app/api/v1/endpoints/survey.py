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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.core.redis import get_redis, RedisClient
from app.core.security import verify_token, get_token_hash
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
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    session = SurveySession(
        lead_id=token_data.lead_id,
        entity_type=token_data.entity_type,
        patient_name=token_data.patient_name,
        survey_config_id=config.id,
        token_hash=token_data.token_hash,
        status="in_progress",
        consent_given=True,
        consent_timestamp=datetime.now(timezone.utc),
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
    )


@router.post("/answer", response_model=SurveyAnswerResponse)
async def submit_answer(
    data: SurveyAnswerRequest,
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
    
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Опрос уже завершён",
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
        # Предполагаем среднюю длину опроса в 10 вопросов для более реалистичного прогресс-бара
        # Реальное число узлов в JSON намного больше длины любого конкретного пути
        ESTIMATED_PATH_LENGTH = 10
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
        answers=progress.get("answers", {}),
        history=progress.get("history", []),
        progress_percent=round(progress_percent, 1),
    )


@router.post("/complete", response_model=SurveyCompleteResponse)
async def complete_survey(
    data: SurveyCompleteRequest,
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
    report_html = report_gen.generate_html_report(
        patient_name=session.patient_name,
        answers=answers_dict,
    )
    
    # Отправка в Битрикс24
    bitrix_client = Bitrix24Client()
    report_sent = await bitrix_client.send_comment(
        entity_id=session.lead_id,
        entity_type=session.entity_type,
        comment=report_html,
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
    )


@router.post("/back")
async def go_back(
    session_id: UUID,
    redis: RedisClient = Depends(get_redis),
):
    """
    Возврат на предыдущий вопрос.
    
    Args:
        session_id: ID сессии
        
    Returns:
        Предыдущий узел
    """
    progress = await redis.get_survey_progress(str(session_id))
    
    if not progress or len(progress.get("history", [])) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно вернуться назад",
        )
    
    # Удаление текущего узла из истории
    history = progress["history"]
    history.pop()  # Удаляем текущий
    previous_node = history[-1] if history else "welcome"
    
    progress["current_node"] = previous_node
    progress["history"] = history
    
    await redis.save_survey_progress(str(session_id), progress)
    
    return {
        "success": True,
        "current_node": previous_node,
    }
