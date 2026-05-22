"""Service layer for DB-backed Opros AI-analysis jobs and report finalization."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisClient
from app.models import AuditLog, SurveyAiAnalysis, SurveyAnswer, SurveyConfig, SurveySession
from app.services.ai_analysis.anonymizer import (
    AiPayloadPrivacyError,
    AiPayloadTooLargeError,
    build_anonymized_payload,
    hash_payload,
)
from app.services.ai_analysis.openrouter_client import OpenRouterClient, OpenRouterClientError
from app.services.ai_analysis.prompt import get_prompt_hash
from app.services.bitrix24 import Bitrix24Client
from app.services.report_generator import ReportGenerator


FINAL_AI_STATUSES = {"succeeded", "failed", "skipped"}
PENDING_AI_STATUSES = {"pending", "running"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_error_message(message: str | None, limit: int = 500) -> str | None:
    if not message:
        return None
    return " ".join(str(message).split())[:limit]


def _running_stale_cutoff() -> datetime:
    """
    Cutoff for reclaiming interrupted running jobs.

    A normal OpenRouter request is bounded by OPENROUTER_TIMEOUT_SECONDS. Add a
    small safety margin, but do not let a killed worker leave the UI in
    "running" forever.
    """
    stale_after_seconds = max(settings.OPENROUTER_TIMEOUT_SECONDS + 30, 180)
    return _now() - timedelta(seconds=stale_after_seconds)


def _ai_snapshot_metadata(analysis: SurveyAiAnalysis | None, *, included: bool) -> dict[str, Any]:
    if analysis is None:
        return {
            "included": False,
            "status": "missing",
            "model": settings.OPENROUTER_MODEL,
            "prompt_version": settings.AI_ANALYSIS_PROMPT_VERSION,
        }

    metadata: dict[str, Any] = {
        "included": included,
        "status": analysis.status,
        "analysis_id": str(analysis.id),
        "model": analysis.model,
        "prompt_version": analysis.prompt_version,
    }
    if analysis.overall_priority:
        metadata["overall_priority"] = analysis.overall_priority
    return metadata


def _has_bitrix_report_upload_attempt(previous_snapshot: dict[str, Any] | None) -> bool:
    """Conservative marker: old snapshots without metadata are treated as already finalized."""
    if previous_snapshot is None:
        return False
    bitrix_report = previous_snapshot.get("bitrix_report")
    if isinstance(bitrix_report, dict):
        return bool(bitrix_report.get("upload_attempted"))
    return True


def build_ai_snapshot_metadata(analysis: SurveyAiAnalysis | None, *, included: bool) -> dict[str, Any]:
    """Public wrapper for report regeneration code."""
    return _ai_snapshot_metadata(analysis, included=included)


async def queue_ai_analysis_job(db: AsyncSession, session: SurveySession) -> tuple[SurveyAiAnalysis, bool]:
    """Idempotently creates one DB-backed AI job for a completed survey session."""
    new_id = uuid.uuid4()
    analysis_case_id = uuid.uuid4()
    stmt = insert(SurveyAiAnalysis).values(
        id=new_id,
        session_id=session.id,
        analysis_case_id=analysis_case_id,
        status="pending",
        model=settings.OPENROUTER_MODEL,
        prompt_version=settings.AI_ANALYSIS_PROMPT_VERSION,
        prompt_hash=get_prompt_hash(),
        queued_at=_now(),
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[SurveyAiAnalysis.session_id],
    ).returning(SurveyAiAnalysis.id)
    inserted_result = await db.execute(stmt)
    inserted_id = inserted_result.scalar_one_or_none()

    result = await db.execute(
        select(SurveyAiAnalysis).where(SurveyAiAnalysis.session_id == session.id)
    )
    analysis = result.scalar_one()
    created = inserted_id is not None
    if created:
        db.add(
            AuditLog(
                session_id=session.id,
                action="ai_analysis_queued",
                details={
                    "analysis_id": str(analysis.id),
                    "analysis_case_id": str(analysis.analysis_case_id),
                    "status": analysis.status,
                    "model": analysis.model,
                    "prompt_version": analysis.prompt_version,
                },
            )
        )
    return analysis, created


async def retry_failed_ai_analysis(db: AsyncSession, analysis_id: UUID | str) -> SurveyAiAnalysis:
    """Controlled admin retry: reset a failed/skipped job instead of creating duplicates."""
    result = await db.execute(
        select(SurveyAiAnalysis).where(SurveyAiAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise ValueError("AI analysis not found")
    if analysis.status not in {"failed", "skipped"}:
        raise ValueError("Only failed or skipped AI analyses can be retried")

    analysis.status = "pending"
    analysis.model = settings.OPENROUTER_MODEL
    analysis.prompt_version = settings.AI_ANALYSIS_PROMPT_VERSION
    analysis.prompt_hash = get_prompt_hash()
    analysis.request_payload_hash = None
    analysis.response_json = None
    analysis.overall_priority = None
    analysis.error_code = None
    analysis.error_message = None
    analysis.attempts = 0
    analysis.queued_at = _now()
    analysis.started_at = None
    analysis.completed_at = None
    db.add(
        AuditLog(
            session_id=analysis.session_id,
            action="ai_analysis_queued",
            details={
                "analysis_id": str(analysis.id),
                "analysis_case_id": str(analysis.analysis_case_id),
                "manual_retry": True,
                "model": analysis.model,
                "prompt_version": analysis.prompt_version,
            },
        )
    )
    return analysis


async def refresh_ai_analysis_for_session(db: AsyncSession, session: SurveySession) -> tuple[SurveyAiAnalysis, bool]:
    """
    Force-refresh AI analysis for an admin action.

    Creates a job when it is missing, reuses pending/running jobs without
    duplication, and resets any final job (including succeeded) to pending.
    """
    existing_result = await db.execute(
        select(SurveyAiAnalysis).where(SurveyAiAnalysis.session_id == session.id)
    )
    analysis = existing_result.scalar_one_or_none()
    if analysis is None:
        analysis, created = await queue_ai_analysis_job(db, session)
        db.add(
            AuditLog(
                session_id=analysis.session_id,
                action="ai_analysis_queued",
                details={
                    "analysis_id": str(analysis.id),
                    "analysis_case_id": str(analysis.analysis_case_id),
                    "manual_refresh": True,
                    "previous_status": "missing",
                    "model": analysis.model,
                    "prompt_version": analysis.prompt_version,
                },
            )
        )
        return analysis, created

    if analysis.status in PENDING_AI_STATUSES:
        return analysis, False

    previous_status = analysis.status
    analysis.analysis_case_id = uuid.uuid4()
    analysis.status = "pending"
    analysis.model = settings.OPENROUTER_MODEL
    analysis.prompt_version = settings.AI_ANALYSIS_PROMPT_VERSION
    analysis.prompt_hash = get_prompt_hash()
    analysis.request_payload_hash = None
    analysis.response_json = None
    analysis.overall_priority = None
    analysis.error_code = None
    analysis.error_message = None
    analysis.attempts = 0
    analysis.queued_at = _now()
    analysis.started_at = None
    analysis.completed_at = None
    db.add(analysis)
    db.add(
        AuditLog(
            session_id=analysis.session_id,
            action="ai_analysis_queued",
            details={
                "analysis_id": str(analysis.id),
                "analysis_case_id": str(analysis.analysis_case_id),
                "manual_refresh": True,
                "previous_status": previous_status,
                "model": analysis.model,
                "prompt_version": analysis.prompt_version,
            },
        )
    )
    return analysis, True


async def get_successful_ai_analysis(db: AsyncSession, session_id: UUID | str) -> SurveyAiAnalysis | None:
    result = await db.execute(
        select(SurveyAiAnalysis).where(
            SurveyAiAnalysis.session_id == session_id,
            SurveyAiAnalysis.status == "succeeded",
        )
    )
    return result.scalar_one_or_none()


async def get_ai_analysis_for_session(db: AsyncSession, session_id: UUID | str) -> SurveyAiAnalysis | None:
    result = await db.execute(
        select(SurveyAiAnalysis).where(SurveyAiAnalysis.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def requeue_stale_running_ai_analyses(db: AsyncSession) -> int:
    """Return stale running jobs to pending after worker interruption/timeout."""
    cutoff = _running_stale_cutoff()
    result = await db.execute(
        select(SurveyAiAnalysis)
        .where(
            SurveyAiAnalysis.status == "running",
            SurveyAiAnalysis.started_at < cutoff,
        )
        .with_for_update(skip_locked=True)
        .limit(10)
    )
    analyses = list(result.scalars().all())
    for analysis in analyses:
        analysis.status = "pending"
        analysis.error_code = "requeued_stale_running"
        analysis.error_message = "AI analysis worker was interrupted or timed out"
        analysis.attempts = 0
        analysis.started_at = None
        analysis.completed_at = None
        analysis.queued_at = _now()
        db.add(
            AuditLog(
                session_id=analysis.session_id,
                action="ai_analysis_requeued",
                details={
                    "analysis_id": str(analysis.id),
                    "analysis_case_id": str(analysis.analysis_case_id),
                    "reason": "stale_running",
                    "model": analysis.model,
                    "prompt_version": analysis.prompt_version,
                },
            )
        )
    if analyses:
        await db.flush()
    return len(analyses)


async def fetch_next_pending_ai_analysis(db: AsyncSession) -> SurveyAiAnalysis | None:
    """Returns one pending job using PostgreSQL row locking for multi-worker safety."""
    await requeue_stale_running_ai_analyses(db)
    result = await db.execute(
        select(SurveyAiAnalysis)
        .where(SurveyAiAnalysis.status == "pending")
        .order_by(SurveyAiAnalysis.queued_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _load_job_context(
    db: AsyncSession,
    analysis: SurveyAiAnalysis,
) -> tuple[SurveySession | None, SurveyConfig | None, list[SurveyAnswer]]:
    session_result = await db.execute(
        select(SurveySession).where(SurveySession.id == analysis.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        return None, None, []

    config_result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    )
    config = config_result.scalar_one_or_none()

    answers_result = await db.execute(
        select(SurveyAnswer)
        .where(SurveyAnswer.session_id == session.id)
        .order_by(SurveyAnswer.id.asc())
    )
    answers = list(answers_result.scalars().all())
    return session, config, answers


async def _was_ai_analysis_queued_manually(db: AsyncSession, analysis: SurveyAiAnalysis | None) -> bool:
    """Проверяет, была ли задача AI-анализа запущена вручную из админ-панели."""
    if analysis is None:
        return False

    result = await db.execute(
        select(AuditLog.details).where(
            AuditLog.session_id == analysis.session_id,
            AuditLog.action == "ai_analysis_queued",
        )
    )
    analysis_id = str(analysis.id)
    for details in result.scalars().all():
        if not isinstance(details, dict):
            continue
        if details.get("analysis_id") != analysis_id:
            continue
        if details.get("manual_refresh") or details.get("manual_retry"):
            return True
    return False


async def process_ai_analysis_job(db: AsyncSession, analysis: SurveyAiAnalysis) -> None:
    """Processes one AI job, then always attempts report generation/finalization."""
    if analysis.status != "pending":
        return

    session: SurveySession | None = None
    config: SurveyConfig | None = None
    answers: list[SurveyAnswer] = []

    analysis.status = "running"
    analysis.started_at = _now()
    analysis.error_code = None
    analysis.error_message = None
    db.add(
        AuditLog(
            session_id=analysis.session_id,
            action="ai_analysis_started",
            details={
                "analysis_id": str(analysis.id),
                "analysis_case_id": str(analysis.analysis_case_id),
                "model": analysis.model,
                "prompt_version": analysis.prompt_version,
            },
        )
    )
    await db.commit()

    try:
        session, config, answers = await _load_job_context(db, analysis)
        if not session:
            analysis.status = "failed"
            analysis.error_code = "session_not_found"
            analysis.error_message = "Survey session not found"
            analysis.completed_at = _now()
            db.add(analysis)
            await db.commit()
            return

        if not config:
            analysis.status = "failed"
            analysis.error_code = "config_not_found"
            analysis.error_message = "Survey config not found"
            analysis.completed_at = _now()
            db.add(analysis)
            await db.commit()
            return

        if not settings.AI_ANALYSIS_ENABLED:
            analysis.status = "skipped"
            analysis.error_code = "disabled"
            analysis.error_message = "AI analysis is disabled by feature flag"
            analysis.completed_at = _now()
            db.add(
                AuditLog(
                    session_id=session.id,
                    action="ai_analysis_excluded_from_report",
                    details={"analysis_id": str(analysis.id), "reason": "disabled"},
                )
            )
            await db.commit()
            await finalize_survey_report(db, session=session, config=config, answers=answers, ai_analysis=analysis)
            return

        payload = build_anonymized_payload(
            analysis_case_id=analysis.analysis_case_id,
            survey_config_id=session.survey_config_id,
            config_json=config.json_config,
            answers=answers,
            completed_at=session.completed_at,
        )
        analysis.request_payload_hash = hash_payload(payload)
        analysis.prompt_hash = get_prompt_hash()
    except (AiPayloadTooLargeError, AiPayloadPrivacyError) as exc:
        analysis.status = "failed"
        analysis.error_code = exc.__class__.__name__
        analysis.error_message = _safe_error_message(str(exc))
        analysis.completed_at = _now()
        db.add(analysis)
        db.add(
            AuditLog(
                session_id=session.id,
                action="ai_analysis_failed",
                details={
                    "analysis_id": str(analysis.id),
                    "analysis_case_id": str(analysis.analysis_case_id),
                    "error_code": analysis.error_code,
                },
            )
        )
        await db.commit()
        await finalize_survey_report(db, session=session, config=config, answers=answers, ai_analysis=analysis)
        return

    try:
        client = OpenRouterClient(model=analysis.model)
        max_attempts = max(1, settings.AI_ANALYSIS_MAX_ATTEMPTS)
        last_error: OpenRouterClientError | None = None

        for attempt in range(1, max_attempts + 1):
            analysis.attempts = attempt
            await db.commit()
            try:
                try:
                    ai_response = await asyncio.wait_for(
                        client.analyze(payload),
                        timeout=settings.OPENROUTER_TIMEOUT_SECONDS + 15,
                    )
                except asyncio.TimeoutError as exc:
                    raise OpenRouterClientError(
                        "timeout",
                        "OpenRouter request timed out",
                        retryable=True,
                    ) from exc
                response_json = ai_response.model_dump(mode="json")
                analysis.response_json = response_json
                analysis.overall_priority = ai_response.overall_priority
                analysis.status = "succeeded"
                analysis.error_code = None
                analysis.error_message = None
                analysis.completed_at = _now()
                db.add(
                    AuditLog(
                        session_id=session.id,
                        action="ai_analysis_succeeded",
                        details={
                            "analysis_id": str(analysis.id),
                            "analysis_case_id": str(analysis.analysis_case_id),
                            "model": analysis.model,
                            "prompt_version": analysis.prompt_version,
                            "attempts": analysis.attempts,
                            "overall_priority": analysis.overall_priority,
                        },
                    )
                )
                await db.commit()
                break
            except OpenRouterClientError as exc:
                last_error = exc
                analysis.error_code = exc.code
                analysis.error_message = _safe_error_message(exc.safe_message)
                await db.commit()
                if attempt < max_attempts and exc.retryable:
                    db.add(
                        AuditLog(
                            session_id=session.id,
                            action="ai_analysis_retried",
                            details={
                                "analysis_id": str(analysis.id),
                                "analysis_case_id": str(analysis.analysis_case_id),
                                "attempt": attempt,
                                "error_code": exc.code,
                            },
                        )
                    )
                    await db.commit()
                    await asyncio.sleep(min(2 ** attempt, 10))
                    continue
                break

        if analysis.status != "succeeded":
            analysis.status = "failed"
            analysis.completed_at = _now()
            if last_error:
                analysis.error_code = last_error.code
                analysis.error_message = _safe_error_message(last_error.safe_message)
            db.add(
                AuditLog(
                    session_id=session.id,
                    action="ai_analysis_failed",
                    details={
                        "analysis_id": str(analysis.id),
                        "analysis_case_id": str(analysis.analysis_case_id),
                        "error_code": analysis.error_code,
                        "attempts": analysis.attempts,
                    },
                )
            )
            await db.commit()

    except Exception as exc:
        logger.exception(f"[AI-WORKER] Непредвиденная ошибка обработки ИИ-задачи: analysis_id={analysis.id}")
        analysis.status = "failed"
        analysis.error_code = "unexpected_error"
        analysis.error_message = _safe_error_message(str(exc))
        analysis.completed_at = _now()
        db.add(analysis)
        if session:
            db.add(
                AuditLog(
                    session_id=session.id,
                    action="ai_analysis_failed",
                    details={
                        "analysis_id": str(analysis.id),
                        "analysis_case_id": str(analysis.analysis_case_id),
                        "error_code": analysis.error_code,
                    },
                )
            )
        await db.commit()

    if session and config:
        await finalize_survey_report(db, session=session, config=config, answers=answers, ai_analysis=analysis)


async def finalize_survey_report(
    db: AsyncSession,
    *,
    session: SurveySession,
    config: SurveyConfig,
    answers: list[SurveyAnswer],
    ai_analysis: SurveyAiAnalysis | None,
) -> None:
    """Generates snapshot, sends the initial Bitrix report once, and clears progress."""
    previous_snapshot = session.report_snapshot if isinstance(session.report_snapshot, dict) else None
    manual_ai_refresh = await _was_ai_analysis_queued_manually(db, ai_analysis)
    bitrix_upload_already_attempted = _has_bitrix_report_upload_attempt(previous_snapshot)
    should_upload_to_bitrix = not manual_ai_refresh and not bitrix_upload_already_attempted
    bitrix_skip_reason: str | None = None
    if not should_upload_to_bitrix:
        bitrix_skip_reason = "manual_report_refresh" if manual_ai_refresh else "report_already_finalized"

    answers_dict = {answer.node_id: answer.answer_data for answer in answers}
    ai_result = ai_analysis.response_json if ai_analysis and ai_analysis.status == "succeeded" else None
    ai_included = bool(ai_result)

    report_gen = ReportGenerator(config.json_config if config else {})
    readable_html = report_gen.generate_readable_html_report(
        patient_name=session.patient_name,
        answers=answers_dict,
        ai_analysis=ai_result,
    )
    report_text = report_gen.generate_text_report(
        patient_name=session.patient_name,
        answers=answers_dict,
        ai_analysis=ai_result,
    )

    report_snapshot = {
        "html": readable_html,
        "txt": report_text,
        "generated_at": _now().isoformat(),
        "config_version": config.version if config else "unknown",
        "regenerated": False,
        "ai_analysis": _ai_snapshot_metadata(ai_analysis, included=ai_included),
    }

    db.add(
        AuditLog(
            session_id=session.id,
            action="ai_analysis_included_in_report" if ai_included else "ai_analysis_excluded_from_report",
            details={
                "analysis_id": str(ai_analysis.id) if ai_analysis else None,
                "status": ai_analysis.status if ai_analysis else "missing",
                "included": ai_included,
            },
        )
    )

    report_sent = False
    pdf_sent = False

    if should_upload_to_bitrix:
        bitrix_client = Bitrix24Client()
        try:
            from weasyprint import HTML as WeasyHTML

            pdf_buffer = BytesIO()
            WeasyHTML(string=readable_html).write_pdf(pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()

            patient_safe = session.patient_name or "patient"
            patient_safe = "".join(c for c in patient_safe if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
            date_str = _now().strftime("%d_%m_%Y")
            pdf_filename = f"Anketa_{patient_safe}_{date_str}.pdf"

            pdf_sent = await bitrix_client.upload_pdf_to_entity(
                entity_id=session.lead_id,
                entity_type=session.entity_type,
                pdf_bytes=pdf_bytes,
                filename=pdf_filename,
            )
            report_sent = pdf_sent
        except ImportError:
            logger.warning("[AI-WORKER] WeasyPrint не установлен, PDF-отчёт не будет отправлен")
        except Exception as exc:
            logger.error(f"[AI-WORKER] Ошибка генерации/отправки PDF: {exc}")

        if not pdf_sent:
            report_sent = await bitrix_client.send_comment(
                entity_id=session.lead_id,
                entity_type=session.entity_type,
                comment=report_text,
            )

        try:
            field_updated = await bitrix_client.update_entity_field(
                entity_id=session.lead_id,
                entity_type=session.entity_type,
                fields={"UF_CRM_1771857760": "да"},
            )
            if field_updated:
                logger.info(
                    f"[AI-WORKER] Поле UF_CRM_1771857760 обновлено: session_id={session.id}, entity_type={session.entity_type}"
                )
        except Exception as exc:
            logger.error(f"[AI-WORKER] Ошибка обновления поля CRM: {exc}")
    else:
        logger.info(
            f"[AI-WORKER] Отправка отчёта в Bitrix24 пропущена: "
            f"session_id={session.id}, reason={bitrix_skip_reason}"
        )

    report_snapshot["bitrix_report"] = {
        "upload_attempted": should_upload_to_bitrix,
        "report_sent": report_sent,
        "pdf_sent": pdf_sent,
        "skipped_reason": bitrix_skip_reason,
    }
    session.report_snapshot = report_snapshot
    db.add(session)

    db.add(
        AuditLog(
            session_id=session.id,
            action="report_processed",
            details={
                "answers_count": len(answers),
                "report_sent": report_sent,
                "pdf_sent": pdf_sent,
                "bitrix_upload_attempted": should_upload_to_bitrix,
                "bitrix_skip_reason": bitrix_skip_reason,
                "ai_included": ai_included,
                "ai_status": ai_analysis.status if ai_analysis else "missing",
            },
        )
    )

    redis = RedisClient()
    await redis.connect()
    try:
        await redis.invalidate_token(session.token_hash)
        await redis.delete_survey_progress(str(session.id))
    finally:
        await redis.disconnect()

    await db.commit()
    logger.info(
        f"[AI-WORKER] Отчёт обработан: session_id={session.id}, ai_included={ai_included}, report_sent={report_sent}"
    )
