"""
API для защищенного портала врачей.
"""

from datetime import date, datetime, time, timezone
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.reports import _get_report_content, _safe_filename
from app.core.database import get_db
from app.core.security import (
    create_doctor_access_token,
    create_doctor_pdf_share_token,
    verify_doctor_token,
    verify_doctor_pdf_share_token,
    verify_password,
    DOCTOR_PDF_SHARE_TOKEN_EXPIRE_HOURS,
)
from app.models import DoctorUser, SurveySession
from app.services.doctor_portal_routing import (
    PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
    PORTAL_CLINIC_BUCKET_TEST,
    PORTAL_CLINIC_BUCKETS,
    resolve_portal_clinic_bucket,
)


router = APIRouter(prefix="/doctors", tags=["Портал врачей"])

doctor_bearer = HTTPBearer(auto_error=False)


class DoctorLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)


class DoctorMeResponse(BaseModel):
    id: int
    username: str
    can_view_test_tab: bool


class DoctorAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor: DoctorMeResponse


class DoctorSessionItem(BaseModel):
    session_id: UUID
    patient_name: str | None = None
    doctor_name: str | None = None
    appointment_at: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    preview_url: str
    download_url: str
    share_url: str


class DoctorPdfShareResponse(BaseModel):
    share_url: str
    expires_in_hours: int


class DoctorSessionsResponse(BaseModel):
    items: list[DoctorSessionItem]
    total: int


def _normalize_day_bounds(value: date, is_end: bool) -> datetime:
    bound_time = time.max if is_end else time.min
    return datetime.combine(value, bound_time, tzinfo=timezone.utc)


def _calculate_duration_minutes(started_at: datetime | None, completed_at: datetime | None) -> int | None:
    if not started_at or not completed_at:
        return None

    total_seconds = max(0, int((completed_at - started_at).total_seconds()))
    return round(total_seconds / 60)


def _doctor_to_response(doctor: DoctorUser) -> DoctorMeResponse:
    return DoctorMeResponse(
        id=doctor.id,
        username=doctor.username,
        can_view_test_tab=doctor.can_view_test_tab,
    )


def _validate_clinic_bucket(clinic_bucket: str) -> str:
    normalized_bucket = (clinic_bucket or "").strip().lower()
    if normalized_bucket not in PORTAL_CLINIC_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Неизвестная вкладка портала врачей.",
        )
    return normalized_bucket


def _ensure_doctor_can_access_bucket(doctor: DoctorUser, clinic_bucket: str) -> None:
    if clinic_bucket == PORTAL_CLINIC_BUCKET_TEST and not doctor.can_view_test_tab:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к тестовой вкладке запрещен.",
        )


def _resolve_session_bucket(session: SurveySession) -> str:
    if session.portal_clinic_bucket:
        return session.portal_clinic_bucket

    return resolve_portal_clinic_bucket(session.bitrix_category_id)


def _build_doctor_session_item(session: SurveySession) -> DoctorSessionItem:
    return DoctorSessionItem(
        session_id=session.id,
        patient_name=session.patient_name,
        doctor_name=session.doctor_name,
        appointment_at=session.appointment_at,
        start_time=session.started_at,
        end_time=session.completed_at,
        duration_minutes=_calculate_duration_minutes(session.started_at, session.completed_at),
        preview_url=f"/api/v1/doctors/sessions/{session.id}/preview",
        download_url=f"/api/v1/doctors/sessions/{session.id}/download/pdf",
        share_url=f"/api/v1/doctors/sessions/{session.id}/share/pdf",
    )


async def _get_session_for_doctor(
    session_id: UUID,
    doctor: DoctorUser,
    db: AsyncSession,
) -> SurveySession:
    result = await db.execute(select(SurveySession).where(SurveySession.id == session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена.",
        )

    _ensure_doctor_can_access_bucket(doctor, _resolve_session_bucket(session))
    return session


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

    result = await db.execute(select(DoctorUser).where(DoctorUser.id == token_data.doctor_id))
    doctor = result.scalar_one_or_none()

    if doctor is None or not doctor.is_active or doctor.username != token_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Учетная запись врача недоступна.",
        )

    return doctor


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

    return DoctorAuthResponse(
        access_token=access_token,
        doctor=_doctor_to_response(doctor),
    )


@router.get("/me", response_model=DoctorMeResponse)
async def doctor_me(
    doctor: DoctorUser = Depends(get_current_doctor),
):
    return _doctor_to_response(doctor)


@router.get("/sessions", response_model=DoctorSessionsResponse)
async def doctor_sessions(
    clinic_bucket: str = Query(
        PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
        description="Вкладка портала врачей",
    ),
    doctor_name: str | None = Query(None, description="Фильтр по ФИО врача"),
    date_from: date | None = Query(None, description="Начало периода"),
    date_to: date | None = Query(None, description="Конец периода"),
    db: AsyncSession = Depends(get_db),
    doctor: DoctorUser = Depends(get_current_doctor),
):
    clinic_bucket = _validate_clinic_bucket(clinic_bucket)
    _ensure_doctor_can_access_bucket(doctor, clinic_bucket)

    stmt = select(SurveySession).where(SurveySession.status == "completed")
    stmt = stmt.where(
        or_(
            SurveySession.portal_clinic_bucket == clinic_bucket,
            SurveySession.portal_clinic_bucket.is_(None),
            SurveySession.portal_clinic_bucket == "",
        )
    )

    doctor_filter = (doctor_name or "").strip()
    if doctor_filter:
        stmt = stmt.where(SurveySession.doctor_name.ilike(f"%{doctor_filter}%"))

    if date_from:
        stmt = stmt.where(SurveySession.completed_at >= _normalize_day_bounds(date_from, is_end=False))

    if date_to:
        stmt = stmt.where(SurveySession.completed_at <= _normalize_day_bounds(date_to, is_end=True))

    stmt = stmt.order_by(SurveySession.completed_at.desc().nullslast(), SurveySession.started_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    items: list[DoctorSessionItem] = []

    for session in sessions:
        effective_bucket = _resolve_session_bucket(session)
        if effective_bucket != clinic_bucket:
            continue

        items.append(_build_doctor_session_item(session))

    return DoctorSessionsResponse(items=items, total=len(items))


@router.get("/sessions/{session_id}/preview")
async def doctor_preview_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: DoctorUser = Depends(get_current_doctor),
):
    await _get_session_for_doctor(session_id, doctor, db)
    _, html_content, _ = await _get_report_content(session_id, db)
    return Response(content=html_content, media_type="text/html; charset=utf-8")


@router.get("/sessions/{session_id}/download/pdf")
async def doctor_download_pdf(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: DoctorUser = Depends(get_current_doctor),
):
    from weasyprint import HTML

    await _get_session_for_doctor(session_id, doctor, db)
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


@router.post("/sessions/{session_id}/share/pdf", response_model=DoctorPdfShareResponse)
async def doctor_share_pdf(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    doctor: DoctorUser = Depends(get_current_doctor),
):
    await _get_session_for_doctor(session_id, doctor, db)
    share_token = create_doctor_pdf_share_token(session_id=session_id, doctor_id=doctor.id)
    return DoctorPdfShareResponse(
        share_url=str(request.url_for("doctor_shared_pdf", share_token=share_token)),
        expires_in_hours=DOCTOR_PDF_SHARE_TOKEN_EXPIRE_HOURS,
    )


@router.get("/shared/pdf/{share_token}", name="doctor_shared_pdf")
async def doctor_shared_pdf(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    token_data = verify_doctor_pdf_share_token(share_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка на PDF недействительна или устарела.",
        )

    doctor_result = await db.execute(select(DoctorUser).where(DoctorUser.id == token_data.doctor_id))
    doctor = doctor_result.scalar_one_or_none()
    if doctor is None or not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ссылка на PDF недействительна или устарела.",
        )

    session, html_content, _ = await _get_report_content(token_data.session_id, db)
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF-отчёт недоступен.",
        )
    _ensure_doctor_can_access_bucket(doctor, _resolve_session_bucket(session))

    from weasyprint import HTML

    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    filename = _safe_filename(session.patient_name, token_data.session_id, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
        },
    )
