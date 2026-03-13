# ============================================
# Эндпоинты опроса
# ============================================
"""
API для прохождения опроса.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
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
    SurveyNavigationResponse,
    SurveyCompleteRequest,
    SurveyCompleteResponse,
    SurveyConfigResponse,
)
from app.services.survey_engine import SurveyEngine
from app.services.report_generator import ReportGenerator
from app.services.bitrix24 import Bitrix24Client

router = APIRouter()


def calculate_progress_percent(config_json: dict, current_node_id: str | None, answers: dict) -> float:
    """Рассчитывает прогресс по текущему серверному состоянию."""
    engine = SurveyEngine(config_json)
    answered_node_ids = list(answers.keys())
    progress_percent = engine.calculate_dynamic_progress(current_node_id, answered_node_ids)
    return round(progress_percent, 1)


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
        return SurveyStartResponse(
            session_id=existing_session.id,
            patient_name=existing_session.patient_name,
            survey_config=config.json_config,
            message="Сессия восстановлена. Продолжайте с того места, где остановились.",
            expires_at=existing_session.expires_at,
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
    
    # Установка времени истечения сессии (12 часов с момента создания)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    
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
        patient_name=patient_name,
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
        if data.duration_seconds is not None:
            existing.duration_seconds = data.duration_seconds
    else:
        answer = SurveyAnswer(
            session_id=session.id,
            node_id=data.node_id,
            answer_data=data.answer_data,
            duration_seconds=data.duration_seconds,
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
    
    # Динамический расчёт прогресса с учётом реального пути ветвления.
    # Формула: answered / (answered + remaining_default_path_length)
    # При каждом ответе remaining пересчитывается от нового next_node,
    # поэтому прогресс точно отражает открытие/закрытие веток.
    answered_node_ids = list(progress["answers"].keys())
    progress_percent = engine.calculate_dynamic_progress(next_node, answered_node_ids)

    return SurveyAnswerResponse(
        success=True,
        next_node=next_node,
        progress=progress_percent,
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
    
    # Расчёт процента через динамический алгоритм SurveyEngine
    stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        progress_percent = calculate_progress_percent(
            config.json_config,
            progress.get("current_node", "welcome"),
            progress.get("answers", {}),
        )
    else:
        total_nodes = 1
        progress_percent = min(100.0, (len(progress.get("answers", {}).keys()) / total_nodes) * 100)
    
    return SurveyProgressResponse(
        session_id=session_id,
        current_node=progress.get("current_node", "welcome"),
        history=progress.get("history", []),
        progress_percent=progress_percent,
        answers=progress.get("answers", {}),
    )


# ==========================================
# Фоновая задача: генерация отчёта и отправка в Битрикс24
# Выполняется ПОСЛЕ того, как ответ уже отдан клиенту,
# чтобы пользователь не ждал 5-10 секунд.
# ==========================================

async def _process_survey_report(
    session_id: int,
    lead_id: int,
    entity_type: str | None,
    patient_name: str | None,
    survey_config_id: int,
    token_hash: str,
) -> None:
    """
    Фоновая обработка: генерация PDF, отправка в Битрикс24,
    инвалидация токена, очистка Redis-прогресса.
    """
    from app.core.database import async_session_maker
    from app.core.redis import RedisClient as _RedisClient

    async with async_session_maker() as db:
        redis = _RedisClient()
        await redis.connect()
        try:
            # Получение ответов
            stmt = select(SurveyAnswer).where(SurveyAnswer.session_id == session_id)
            result = await db.execute(stmt)
            answers = result.scalars().all()

            # Получение конфига
            stmt = select(SurveyConfig).where(SurveyConfig.id == survey_config_id)
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()

            # Генерация отчёта
            report_gen = ReportGenerator(config.json_config if config else {})
            answers_dict = {a.node_id: a.answer_data for a in answers}

            # -------------------------------------------------------
            # Генерируем HTML и TXT сразу — они понадобятся как для
            # отправки в Битрикс24, так и для сохранения снимка отчёта.
            # -------------------------------------------------------
            readable_html = report_gen.generate_readable_html_report(
                patient_name=patient_name,
                answers=answers_dict,
            )
            report_text = report_gen.generate_text_report(
                patient_name=patient_name,
                answers=answers_dict,
            )

            # Сохраняем снимок («запечатываем» отчёт) в таблице сессии
            stmt_sess = select(SurveySession).where(SurveySession.id == session_id)
            result_sess = await db.execute(stmt_sess)
            survey_session_obj = result_sess.scalar_one_or_none()
            if survey_session_obj:
                survey_session_obj.report_snapshot = {
                    "html": readable_html,
                    "txt": report_text,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "config_version": config.version if config else "unknown",
                    "regenerated": False,
                }
                logger.info(f"[BG] Снимок отчёта сохранён: session_id={session_id}")

            bitrix_client = Bitrix24Client()
            report_sent = False
            pdf_sent = False

            # Генерация и отправка PDF-отчёта в карточку Битрикс24
            try:
                from weasyprint import HTML as WeasyHTML
                from io import BytesIO

                pdf_buffer = BytesIO()
                WeasyHTML(string=readable_html).write_pdf(pdf_buffer)
                pdf_bytes = pdf_buffer.getvalue()

                patient_safe = patient_name or "patient"
                patient_safe = "".join(
                    c for c in patient_safe if c.isalnum() or c in (' ', '_')
                ).strip().replace(" ", "_")
                date_str = datetime.now(timezone.utc).strftime("%d_%m_%Y")
                pdf_filename = f"Anketa_{patient_safe}_{date_str}.pdf"

                pdf_sent = await bitrix_client.upload_pdf_to_entity(
                    entity_id=lead_id,
                    entity_type=entity_type,
                    pdf_bytes=pdf_bytes,
                    filename=pdf_filename,
                )

                if pdf_sent:
                    logger.info(f"[BG] PDF-отчёт отправлен в Битрикс24: lead_id={lead_id}")
                    report_sent = True
                else:
                    logger.warning(f"[BG] Не удалось отправить PDF в Битрикс24: lead_id={lead_id}")

            except ImportError:
                logger.warning("[BG] WeasyPrint не установлен, PDF-отчёт не будет отправлен")
            except Exception as e:
                logger.error(f"[BG] Ошибка генерации/отправки PDF: {e}")

            # Fallback: текстовый комментарий если PDF не отправлен
            if not pdf_sent:
                report_sent = await bitrix_client.send_comment(
                    entity_id=lead_id,
                    entity_type=entity_type,
                    comment=report_text,
                )

            # Обновление пользовательского поля «Опрос пройден» в CRM
            try:
                field_updated = await bitrix_client.update_entity_field(
                    entity_id=lead_id,
                    entity_type=entity_type,
                    fields={"UF_CRM_1771857760": "да"},
                )
                if field_updated:
                    logger.info(
                        f"[BG] Поле UF_CRM_1771857760 обновлено ('да'): "
                        f"lead_id={lead_id}, entity_type={entity_type}"
                    )
            except Exception as e:
                logger.error(f"[BG] Ошибка обновления поля CRM: {e}")

            # Аудит-лог результата фоновой обработки
            audit_log = AuditLog(
                session_id=session_id,
                action="report_processed",
                details={
                    "answers_count": len(answers),
                    "report_sent": report_sent,
                    "pdf_sent": pdf_sent,
                },
            )
            db.add(audit_log)

            # Инвалидация токена
            await redis.invalidate_token(token_hash)

            # Удаление прогресса из Redis
            await redis.delete_survey_progress(str(session_id))

            await db.commit()

            logger.info(f"[BG] Фоновая обработка завершена: session_id={session_id}")

        except Exception as e:
            logger.error(f"[BG] Критическая ошибка фоновой обработки session_id={session_id}: {e}")
        finally:
            await redis.disconnect()


@router.post("/complete", response_model=SurveyCompleteResponse)
async def complete_survey(
    data: SurveyCompleteRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """
    Завершение опроса — мгновенный ответ клиенту.
    
    Тяжёлые операции (PDF, Битрикс24) выполняются в фоне через BackgroundTasks,
    чтобы пользователь не ждал 5-10 секунд.
    
    Args:
        data: ID сессии
        
    Returns:
        Мгновенный статус завершения
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
    
    # === БЫСТРАЯ ЧАСТЬ: только обновление статуса в БД ===
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    
    # Аудит-лог о завершении (фоновый лог добавится отдельно)
    audit_log = AuditLog(
        session_id=session.id,
        action="survey_completed",
        details={"background_processing": True},
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"Опрос завершён (быстрый ответ): session_id={session.id}")
    
    # === ТЯЖЁЛАЯ ЧАСТЬ: отправляем в фон ===
    background_tasks.add_task(
        _process_survey_report,
        session_id=session.id,
        lead_id=session.lead_id,
        entity_type=session.entity_type,
        patient_name=session.patient_name,
        survey_config_id=session.survey_config_id,
        token_hash=session.token_hash,
    )
    
    return SurveyCompleteResponse(
        success=True,
        message="Спасибо! Анкета заполнена. Данные переданы врачу.",
        report_sent=True,
    )


class GoBackRequest(BaseModel):
    """Запрос на возврат к предыдущему вопросу."""
    session_id: UUID


@router.post("/back", response_model=SurveyNavigationResponse)
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

    stmt = select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Конфигурация опросника не найдена",
        )

    return SurveyNavigationResponse(
        success=True,
        current_node=previous_node,
        history=history,
        progress_percent=calculate_progress_percent(
            config.json_config,
            previous_node,
            progress.get("answers", {}),
        ),
        answers=progress.get("answers", {}),
    )
