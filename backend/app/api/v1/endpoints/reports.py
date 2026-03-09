# ============================================
# Reports Endpoints - Эндпоинты для отчётов
# ============================================
"""
API для экспорта и просмотра отчётов.

Логика работы с «запечатанными» отчётами:
- После завершения опроса отчёт фиксируется (snapshot) и больше не изменяется
  при редактировании структуры опросника.
- preview / export используют сохранённый снимок (если он есть).
- POST /{session_id}/regenerate — принудительная перегенерация администратором.
"""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.models import SurveySession, SurveyAnswer, SurveyConfig
from app.services.report_generator import ReportGenerator
from app.api.v1.endpoints.survey_editor import verify_admin_session


router = APIRouter(prefix="/reports", tags=["reports"])


# ──────────────────────────────────────────────────────────────
# Внутренние помощники
# ──────────────────────────────────────────────────────────────

async def _get_completed_session(session_id: UUID, db: AsyncSession) -> SurveySession:
    """Получить завершённую сессию или выбросить HTTPException."""
    result = await db.execute(
        select(SurveySession).where(SurveySession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Отчёт доступен только для завершённых сессий",
        )

    return session


async def _get_report_content(session_id: UUID, db: AsyncSession) -> tuple[SurveySession, str, str]:
    """
    Возвращает (session, html_content, txt_content).

    Если у сессии сохранён снимок (report_snapshot), использует его —
    изменения в конфигурации опросника НЕ отражаются в старых отчётах.
    Для сессий без снимка (старые записи) выполняет динамическую генерацию.
    """
    session = await _get_completed_session(session_id, db)

    # ── Путь 1: используем сохранённый снимок ──
    if session.report_snapshot:
        html = session.report_snapshot.get("html", "")
        txt = session.report_snapshot.get("txt", "")
        return session, html, txt

    # ── Путь 2: динамическая генерация (старые сессии без снимка) ──
    result = await db.execute(
        select(SurveyAnswer).where(SurveyAnswer.session_id == session_id)
    )
    answers_dict = {a.node_id: a.answer_data for a in result.scalars().all()}

    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Конфигурация опросника не найдена")

    report_gen = ReportGenerator(config.json_config)
    html = report_gen.generate_readable_html_report(
        patient_name=session.patient_name,
        answers=answers_dict,
    )
    txt = report_gen.generate_text_report(
        patient_name=session.patient_name,
        answers=answers_dict,
    )
    return session, html, txt


def _safe_filename(patient_name: str | None, session_id: UUID, ext: str) -> str:
    """Формирует безопасное имя файла для скачивания."""
    name = patient_name or "patient"
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
    return f"report_{safe}_{session_id}.{ext}"


# ──────────────────────────────────────────────────────────────
# Эндпоинты
# ──────────────────────────────────────────────────────────────

@router.get("/{session_id}/preview")
async def preview_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """
    Предпросмотр отчёта в HTML формате.
    Возвращает сохранённый снимок (если есть) или динамически сгенерированный отчёт.
    """
    try:
        session, html_content, _ = await _get_report_content(session_id, db)
        logger.info(
            f"Предпросмотр отчёта: session_id={session_id}, "
            f"snapshot={'да' if session.report_snapshot else 'нет'}"
        )
        return Response(content=html_content, media_type="text/html; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка предпросмотра отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка генерации отчёта")


@router.get("/{session_id}/export/html")
async def export_html(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """Экспорт отчёта в HTML файл (использует снимок если доступен)."""
    try:
        from urllib.parse import quote

        session, html_content, _ = await _get_report_content(session_id, db)
        filename = _safe_filename(session.patient_name, session_id, "html")
        logger.info(f"Экспорт HTML: session_id={session_id}")

        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка экспорта HTML отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")


@router.get("/{session_id}/export/txt")
async def export_txt(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """Экспорт отчёта в TXT файл (использует снимок если доступен)."""
    try:
        from urllib.parse import quote

        session, _, txt_content = await _get_report_content(session_id, db)
        filename = _safe_filename(session.patient_name, session_id, "txt")
        logger.info(f"Экспорт TXT: session_id={session_id}")

        return Response(
            content=txt_content.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка экспорта TXT отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")


@router.get("/{session_id}/export/pdf")
async def export_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """
    Экспорт отчёта в PDF файл.
    Конвертирует сохранённый HTML-снимок (или динамически сгенерированный HTML) в PDF.
    """
    try:
        from urllib.parse import quote
        from weasyprint import HTML
        from io import BytesIO

        session, html_content, _ = await _get_report_content(session_id, db)

        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()

        filename = _safe_filename(session.patient_name, session_id, "pdf")
        logger.info(f"Экспорт PDF: session_id={session_id}")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка экспорта PDF отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")


@router.post("/{session_id}/regenerate")
async def regenerate_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """
    Принудительная перегенерация отчёта с **текущей** версией опросника.

    Вызывается только при явном нажатии кнопки «Обновить отчёт» администратором.
    Пересчитывает HTML и TXT из актуальной конфигурации и сохраняет
    новый снимок (флаг regenerated=True).
    """
    try:
        session = await _get_completed_session(session_id, db)

        result = await db.execute(
            select(SurveyAnswer).where(SurveyAnswer.session_id == session_id)
        )
        answers_dict = {a.node_id: a.answer_data for a in result.scalars().all()}

        result = await db.execute(
            select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail="Конфигурация опросника не найдена")

        report_gen = ReportGenerator(config.json_config)
        html = report_gen.generate_readable_html_report(
            patient_name=session.patient_name,
            answers=answers_dict,
        )
        txt = report_gen.generate_text_report(
            patient_name=session.patient_name,
            answers=answers_dict,
        )

        session.report_snapshot = {
            "html": html,
            "txt": txt,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "config_version": config.version,
            "regenerated": True,
        }
        await db.commit()

        logger.info(
            f"Отчёт принудительно обновлён администратором: "
            f"session_id={session_id}, config_version={config.version}"
        )

        return {
            "success": True,
            "message": "Отчёт успешно пересчитан по текущей версии опросника",
            "config_version": config.version,
            "generated_at": session.report_snapshot["generated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка принудительной перегенерации отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка пересчёта отчёта")
