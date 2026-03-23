"""
API для защищенного портала врачей.
"""

from datetime import date, datetime, time, timezone
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.reports import _get_report_content, _safe_filename
from app.core.database import get_db
from app.core.security import (
    create_doctor_access_token,
    verify_doctor_token,
    verify_password,
)
from app.models import DoctorUser, SurveySession


router = APIRouter(prefix="/doctors", tags=["Портал врачей"])

doctor_bearer = HTTPBearer(auto_error=False)


class DoctorLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)


class DoctorMeResponse(BaseModel):
    id: int
    username: str


class DoctorAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor: DoctorMeResponse


class DoctorSessionItem(BaseModel):
    session_id: UUID
    patient_name: str | None = None
    doctor_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    preview_url: str
    download_url: str


class DoctorSessionsResponse(BaseModel):
    items: list[DoctorSessionItem]
    total: int


async def get_current_doctor(
    credentials: HTTPAuthorizationCredentials | None = Depends(doctor_bearer),
    db: AsyncSession = Depends(get_db),
) -> DoctorUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация врача.",
        )

    token_data = verify_doctor_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия врача недействительна или истекла.",
        )

    result = await db.execute(
        select(DoctorUser).where(DoctorUser.id == token_data.doctor_id)
    )
    doctor = result.scalar_one_or_none()

    if doctor is None or not doctor.is_active or doctor.username != token_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Учетная запись врача недоступна.",
        )

    return doctor


def _normalize_day_bounds(value: date, is_end: bool) -> datetime:
    bound_time = time.max if is_end else time.min
    return datetime.combine(value, bound_time, tzinfo=timezone.utc)


def _calculate_duration_minutes(started_at: datetime | None, completed_at: datetime | None) -> int | None:
    if not started_at or not completed_at:
        return None

    total_seconds = max(0, int((completed_at - started_at).total_seconds()))
    return round(total_seconds / 60)


@router.post("/login", response_model=DoctorAuthResponse)
async def doctor_login(
    data: DoctorLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorUser).where(DoctorUser.username == data.username.strip())
    )
    doctor = result.scalar_one_or_none()

    if doctor is None or not doctor.is_active or not verify_password(data.password, doctor.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль.",
        )

    access_token = create_doctor_access_token(
        doctor_id=doctor.id,
        username=doctor.username,
    )

    doctor_payload = DoctorMeResponse(id=doctor.id, username=doctor.username)
    return DoctorAuthResponse(access_token=access_token, doctor=doctor_payload)


@router.get("/me", response_model=DoctorMeResponse)
async def doctor_me(
    doctor: DoctorUser = Depends(get_current_doctor),
):
    return DoctorMeResponse(id=doctor.id, username=doctor.username)


@router.get("/sessions", response_model=DoctorSessionsResponse)
async def doctor_sessions(
    doctor_name: str | None = Query(None, description="Фильтр по ФИО врача"),
    date_from: date | None = Query(None, description="Начало периода"),
    date_to: date | None = Query(None, description="Конец периода"),
    db: AsyncSession = Depends(get_db),
    _doctor: DoctorUser = Depends(get_current_doctor),
):
    stmt = select(SurveySession).where(SurveySession.status == "completed")

    doctor_filter = (doctor_name or "").strip()
    if doctor_filter:
        stmt = stmt.where(SurveySession.doctor_name.ilike(f"%{doctor_filter}%"))

    if date_from:
        stmt = stmt.where(SurveySession.started_at >= _normalize_day_bounds(date_from, is_end=False))

    if date_to:
        stmt = stmt.where(SurveySession.started_at <= _normalize_day_bounds(date_to, is_end=True))

    stmt = stmt.order_by(SurveySession.started_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    items = [
        DoctorSessionItem(
            session_id=session.id,
            patient_name=session.patient_name,
            doctor_name=session.doctor_name,
            start_time=session.started_at,
            end_time=session.completed_at,
            duration_minutes=_calculate_duration_minutes(session.started_at, session.completed_at),
            preview_url=f"/api/v1/doctors/sessions/{session.id}/preview",
            download_url=f"/api/v1/doctors/sessions/{session.id}/download/pdf",
        )
        for session in sessions
    ]

    return DoctorSessionsResponse(items=items, total=len(items))


@router.get("/sessions/{session_id}/preview")
async def doctor_preview_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _doctor: DoctorUser = Depends(get_current_doctor),
):
    _, html_content, _ = await _get_report_content(session_id, db)
    return Response(content=html_content, media_type="text/html; charset=utf-8")


@router.get("/sessions/{session_id}/download/pdf")
async def doctor_download_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _doctor: DoctorUser = Depends(get_current_doctor),
):
    from weasyprint import HTML

    session, html_content, _ = await _get_report_content(session_id, db)

    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    filename = _safe_filename(session.patient_name, session_id, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
