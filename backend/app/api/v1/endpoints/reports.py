# ============================================
# Reports Endpoints - Эндпоинты для отчётов
# ============================================
"""
API для экспорта и просмотра отчётов.
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from weasyprint import HTML

from app.core.database import get_db
from app.models import SurveySession, SurveyAnswer, SurveyConfig
from app.services.report_generator import ReportGenerator


router = APIRouter(prefix="/reports", tags=["reports"])


async def get_session_with_answers(
    session_id: UUID,
    db: AsyncSession
) -> tuple[SurveySession, dict, ReportGenerator]:
    """
    Получить сессию опроса с ответами и инициализировать генератор отчётов.
    
    Args:
        session_id: ID сессии
        db: Сессия БД
        
    Returns:
        Кортеж (SurveySession, answers_dict, ReportGenerator)
        
    Raises:
        HTTPException: Если сессия не найдена или не завершена
    """
    # Получаем сессию
    result = await db.execute(
        select(SurveySession).where(SurveySession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    if session.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Отчёт доступен только для завершённых сессий"
        )
    
    # Получаем ответы
    result = await db.execute(
        select(SurveyAnswer).where(SurveyAnswer.session_id == session_id)
    )
    answers_list = result.scalars().all()
    
    # Преобразуем в словарь {node_id: answer_data}
    answers_dict = {answer.node_id: answer.answer_data for answer in answers_list}
    
    # Получаем конфигурацию опросника
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == session.survey_config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Конфигурация опросника не найдена")
    
    # Инициализируем генератор отчётов
    report_generator = ReportGenerator(config.json_config)
    
    return session, answers_dict, report_generator


@router.get("/{session_id}/preview")
async def preview_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Предпросмотр отчёта в HTML формате.
    
    Args:
        session_id: ID сессии опроса
        
    Returns:
        HTML-документ для отображения в браузере
    """
    try:
        session, answers_dict, report_generator = await get_session_with_answers(
            session_id, db
        )
        
        # Генерируем читаемый HTML отчёт
        html_content = report_generator.generate_readable_html_report(
            patient_name=session.patient_name,
            answers=answers_dict
        )
        
        logger.info(f"Сгенерирован предпросмотр отчёта для сессии {session_id}")
        
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации предпросмотра отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка генерации отчёта")


@router.get("/{session_id}/export/html")
async def export_html(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Экспорт отчёта в HTML файл.
    
    Args:
        session_id: ID сессии опроса
        
    Returns:
        HTML-файл для скачивания
    """
    try:
        session, answers_dict, report_generator = await get_session_with_answers(
            session_id, db
        )
        
        # Генерируем читаемый HTML отчёт
        html_content = report_generator.generate_readable_html_report(
            patient_name=session.patient_name,
            answers=answers_dict
        )
        
        # Формируем имя файла
        patient_name = session.patient_name or "patient"
        # Очищаем имя от спецсимволов
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
        safe_name = safe_name.replace(" ", "_")
        filename = f"report_{safe_name}_{session_id}.html"
        
        logger.info(f"Экспорт отчёта в HTML для сессии {session_id}")
        
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при экспорте HTML отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")


@router.get("/{session_id}/export/txt")
async def export_txt(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Экспорт отчёта в TXT файл.
    
    Args:
        session_id: ID сессии опроса
        
    Returns:
        Текстовый файл для скачивания
    """
    try:
        session, answers_dict, report_generator = await get_session_with_answers(
            session_id, db
        )
        
        # Генерируем текстовый отчёт
        text_content = report_generator.generate_text_report(
            patient_name=session.patient_name,
            answers=answers_dict
        )
        
        # Формируем имя файла
        patient_name = session.patient_name or "patient"
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
        safe_name = safe_name.replace(" ", "_")
        filename = f"report_{safe_name}_{session_id}.txt"
        
        # Кодируем имя файла для HTTP-заголовка (поддержка кириллицы)
        from urllib.parse import quote
        encoded_filename = quote(filename)
        
        logger.info(f"Экспорт отчёта в TXT для сессии {session_id}")
        
        # Кодируем в UTF-8 для корректной работы с кириллицей
        content_bytes = text_content.encode('utf-8')
        
        return Response(
            content=content_bytes,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при экспорте TXT отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")


@router.get("/{session_id}/export/pdf")
async def export_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Экспорт отчёта в PDF файл.
    
    Args:
        session_id: ID сессии опроса
        
    Returns:
        PDF-файл для скачивания
    """
    try:
        session, answers_dict, report_generator = await get_session_with_answers(
            session_id, db
        )
        
        # Генерируем читаемый HTML отчёт
        html_content = report_generator.generate_readable_html_report(
            patient_name=session.patient_name,
            answers=answers_dict
        )
        
        # Конвертируем HTML в PDF
        from io import BytesIO
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_bytes = pdf_file.getvalue()
        
        # Формируем имя файла
        patient_name = session.patient_name or "patient"
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
        safe_name = safe_name.replace(" ", "_")
        filename = f"report_{safe_name}_{session_id}.pdf"
        
        # Кодируем имя файла для HTTP-заголовка (поддержка кириллицы)
        from urllib.parse import quote
        encoded_filename = quote(filename)
        
        logger.info(f"Экспорт отчёта в PDF для сессии {session_id}")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при экспорте PDF отчёта: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта отчёта")
