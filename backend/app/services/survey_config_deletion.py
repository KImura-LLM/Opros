"""Защитные проверки перед удалением конфигураций опросников."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SurveyRoutingClinicSetting, SurveyRoutingRule, SurveySession


async def get_survey_config_delete_error(
    db: AsyncSession,
    survey_config_id: int,
) -> str | None:
    """
    Вернуть пользовательскую ошибку, если на опросник ещё есть ссылки.

    Завершённые сессии хранят обязательную FK-ссылку на использованный
    опросник, поэтому физическое удаление может повредить отчёты и историю.
    """
    sessions_count = await db.scalar(
        select(func.count(SurveySession.id)).where(
            SurveySession.survey_config_id == survey_config_id
        )
    )
    routing_rules_count = await db.scalar(
        select(func.count(SurveyRoutingRule.id)).where(
            SurveyRoutingRule.survey_config_id == survey_config_id
        )
    )
    clinic_defaults_count = await db.scalar(
        select(func.count(SurveyRoutingClinicSetting.id)).where(
            SurveyRoutingClinicSetting.default_survey_config_id == survey_config_id
        )
    )

    blockers = [
        (label, count or 0)
        for label, count in (
            ("сессии опросов", sessions_count),
            ("правила маршрутизации", routing_rules_count),
            ("настройки клиник по умолчанию", clinic_defaults_count),
        )
        if count
    ]
    if not blockers:
        return None

    details = ", ".join(f"{label}: {count}" for label, count in blockers)
    return (
        "Нельзя удалить опросник, который уже используется. "
        f"Связанные записи — {details}. "
        "Чтобы убрать опросник из новых выдач, снимите флаг «Активен». "
        "Для полного удаления сначала удалите или переназначьте связанные тестовые данные."
    )
