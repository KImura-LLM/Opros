"""Маршрутизация выбора опросника по данным сделки Bitrix24."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    SurveyConfig,
    SurveyRoutingClinicSetting,
    SurveyRoutingCondition,
    SurveyRoutingRule,
)


SURVEY_ROUTING_CLINICS = (
    {
        "key": "novosibirsk",
        "title": "Новосибирск",
        "bitrix_category_ids": ("0",),
    },
    {
        "key": "kemerovo",
        "title": "Кемерово",
        "bitrix_category_ids": ("1",),
    },
    {
        "key": "yaroslavl",
        "title": "Ярославль",
        "bitrix_category_ids": ("3",),
    },
    {
        "key": "test",
        "title": "Тест",
        "bitrix_category_ids": (),
    },
)

SURVEY_ROUTING_CLINIC_BY_KEY = {
    clinic["key"]: clinic
    for clinic in SURVEY_ROUTING_CLINICS
}

SURVEY_ROUTING_CATEGORY_TO_CLINIC = {
    str(category_id): clinic["key"]
    for clinic in SURVEY_ROUTING_CLINICS
    for category_id in clinic["bitrix_category_ids"]
}

SURVEY_ROUTING_FALLBACK_CLINIC_KEY = "test"

CONDITION_LOGIC_AND = "AND"
CONDITION_LOGIC_OR = "OR"
CONDITION_LOGICS = {CONDITION_LOGIC_AND, CONDITION_LOGIC_OR}

OPERATOR_EQUALS = "equals"
OPERATOR_NOT_EQUALS = "not_equals"
OPERATOR_CONTAINS = "contains"
OPERATOR_NOT_CONTAINS = "not_contains"
OPERATOR_IS_FILLED = "is_filled"
OPERATOR_IS_EMPTY = "is_empty"

ROUTING_OPERATORS = {
    OPERATOR_EQUALS,
    OPERATOR_NOT_EQUALS,
    OPERATOR_CONTAINS,
    OPERATOR_NOT_CONTAINS,
    OPERATOR_IS_FILLED,
    OPERATOR_IS_EMPTY,
}


@dataclass(frozen=True)
class SurveyRoutingDecision:
    """Результат выбора опросника."""

    clinic_key: str
    survey_config_id: int | None
    survey_name: str | None
    selected_rule_id: int | None
    selected_rule_name: str | None
    fallback_used: bool
    reason_code: str
    reason: str
    error: str | None = None

    @property
    def matched_rule(self) -> bool:
        return self.selected_rule_id is not None and not self.fallback_used

    def audit_details(self, lead_id: int | None = None, entity_type: str | None = "DEAL") -> dict[str, Any]:
        return {
            "lead_id": lead_id,
            "entity_type": entity_type,
            "clinic_key": self.clinic_key,
            "selected_survey_config_id": self.survey_config_id,
            "selected_rule_id": self.selected_rule_id,
            "fallback_used": self.fallback_used,
            "reason_code": self.reason_code,
        }


def get_survey_routing_clinics() -> tuple[dict[str, Any], ...]:
    """Возвращает клиники, доступные для маршрутизации."""
    return SURVEY_ROUTING_CLINICS


def normalize_bitrix_category_id(raw_value: Any) -> str | None:
    """Нормализует CATEGORY_ID Bitrix24 для выбора клиники."""
    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        raw_value = raw_value.strip()
        if not raw_value:
            return None

    try:
        return str(int(raw_value))
    except (TypeError, ValueError):
        return str(raw_value).strip() or None


def resolve_clinic_key_from_deal(deal_data: dict | None) -> tuple[str, str]:
    """Возвращает clinic_key и reason_code по данным сделки."""
    if not isinstance(deal_data, dict):
        return SURVEY_ROUTING_FALLBACK_CLINIC_KEY, "deal_fetch_error"

    category_id = normalize_bitrix_category_id(deal_data.get("CATEGORY_ID"))
    if category_id is None:
        return SURVEY_ROUTING_FALLBACK_CLINIC_KEY, "unknown_clinic"

    clinic_key = SURVEY_ROUTING_CATEGORY_TO_CLINIC.get(category_id)
    if clinic_key:
        return clinic_key, "clinic_resolved"

    return SURVEY_ROUTING_FALLBACK_CLINIC_KEY, "unknown_clinic"


def normalize_condition_logic(value: str | None) -> str:
    normalized = (value or CONDITION_LOGIC_AND).strip().upper()
    return normalized if normalized in CONDITION_LOGICS else CONDITION_LOGIC_AND


def normalize_operator(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in ROUTING_OPERATORS:
        raise ValueError(f"Unsupported routing operator: {value!r}")
    return normalized


def extract_condition_value(raw_value: Any) -> Any:
    """Нормализует value из условия, сохраняя совместимость с будущим JSON payload."""
    if isinstance(raw_value, dict):
        for key in ("value", "option_id", "id", "label"):
            if key in raw_value:
                return raw_value[key]
        return raw_value
    return raw_value


def extract_deal_field_values(raw_value: Any) -> list[Any]:
    """Разворачивает значение поля сделки в список скалярных значений для сравнения."""
    if raw_value is None:
        return []

    if isinstance(raw_value, (list, tuple, set)):
        values: list[Any] = []
        for item in raw_value:
            values.extend(extract_deal_field_values(item))
        return values

    if isinstance(raw_value, dict):
        for key in ("VALUE", "value", "ID", "id", "NAME", "name", "TITLE", "title"):
            if key in raw_value:
                return extract_deal_field_values(raw_value[key])
        return []

    return [raw_value]


def is_filled_value(raw_value: Any) -> bool:
    values = extract_deal_field_values(raw_value)
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                return True
            continue
        return True
    return False


def normalize_scalar_for_compare(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def compare_condition(condition: SurveyRoutingCondition, deal_data: dict[str, Any]) -> bool:
    """Проверяет одно условие маршрутизации."""
    operator = normalize_operator(condition.operator)
    field_value = deal_data.get(condition.crm_field_id)

    if operator == OPERATOR_IS_FILLED:
        return is_filled_value(field_value)
    if operator == OPERATOR_IS_EMPTY:
        return not is_filled_value(field_value)

    condition_value = normalize_scalar_for_compare(extract_condition_value(condition.value))
    field_values = [
        normalize_scalar_for_compare(value)
        for value in extract_deal_field_values(field_value)
    ]

    if operator == OPERATOR_EQUALS:
        return any(value == condition_value for value in field_values)
    if operator == OPERATOR_NOT_EQUALS:
        return not any(value == condition_value for value in field_values)
    if operator == OPERATOR_CONTAINS:
        needle = condition_value.casefold()
        return any(needle in value.casefold() for value in field_values)
    if operator == OPERATOR_NOT_CONTAINS:
        needle = condition_value.casefold()
        return not any(needle in value.casefold() for value in field_values)

    raise ValueError(f"Unsupported routing operator: {condition.operator!r}")


def rule_matches(rule: SurveyRoutingRule, deal_data: dict[str, Any]) -> bool:
    """Проверяет правило маршрутизации по всем условиям."""
    conditions = list(rule.conditions or [])
    if not conditions:
        return False

    results = [compare_condition(condition, deal_data) for condition in conditions]
    logic = normalize_condition_logic(rule.condition_logic)

    if logic == CONDITION_LOGIC_OR:
        return any(results)
    return all(results)


async def get_active_survey_config(db: AsyncSession, survey_config_id: int | None) -> SurveyConfig | None:
    if survey_config_id is None:
        return None

    result = await db.execute(
        select(SurveyConfig).where(
            SurveyConfig.id == survey_config_id,
            SurveyConfig.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_global_fallback_survey_config(db: AsyncSession) -> SurveyConfig | None:
    result = await db.execute(
        select(SurveyConfig)
        .where(SurveyConfig.is_active == True)
        .order_by(SurveyConfig.id.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_clinic_default_survey_config(
    db: AsyncSession,
    clinic_key: str,
) -> tuple[SurveyConfig | None, str]:
    result = await db.execute(
        select(SurveyRoutingClinicSetting).where(
            SurveyRoutingClinicSetting.clinic_key == clinic_key,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return await get_global_fallback_survey_config(db), "clinic_default_missing"

    if not setting.is_enabled:
        config = await get_active_survey_config(db, setting.default_survey_config_id)
        return config or await get_global_fallback_survey_config(db), "routing_disabled"

    config = await get_active_survey_config(db, setting.default_survey_config_id)
    if config:
        return config, "clinic_default"

    return await get_global_fallback_survey_config(db), "clinic_default_missing"


async def build_fallback_decision(
    db: AsyncSession,
    clinic_key: str,
    reason_code: str,
    reason: str,
    error: str | None = None,
) -> SurveyRoutingDecision:
    config, default_reason_code = await get_clinic_default_survey_config(db, clinic_key)
    final_reason_code = reason_code or default_reason_code

    if config is None:
        return SurveyRoutingDecision(
            clinic_key=clinic_key,
            survey_config_id=None,
            survey_name=None,
            selected_rule_id=None,
            selected_rule_name=None,
            fallback_used=True,
            reason_code="survey_config_missing",
            reason="Не найден активный fallback-опросник.",
            error=error,
        )

    return SurveyRoutingDecision(
        clinic_key=clinic_key,
        survey_config_id=config.id,
        survey_name=config.name,
        selected_rule_id=None,
        selected_rule_name=None,
        fallback_used=True,
        reason_code=final_reason_code,
        reason=reason,
        error=error,
    )


async def resolve_survey_for_deal(
    db: AsyncSession,
    deal_data: dict | None,
    clinic_key: str | None = None,
) -> SurveyRoutingDecision:
    """Выбирает опросник по данным сделки Bitrix24."""
    resolved_clinic_key, clinic_reason_code = resolve_clinic_key_from_deal(deal_data)
    effective_clinic_key = clinic_key or resolved_clinic_key

    if effective_clinic_key not in SURVEY_ROUTING_CLINIC_BY_KEY:
        effective_clinic_key = SURVEY_ROUTING_FALLBACK_CLINIC_KEY

    if not isinstance(deal_data, dict):
        return await build_fallback_decision(
            db,
            effective_clinic_key,
            "deal_fetch_error",
            "Не удалось получить сделку Bitrix24. Использован опросник по умолчанию.",
        )

    setting_result = await db.execute(
        select(SurveyRoutingClinicSetting).where(
            SurveyRoutingClinicSetting.clinic_key == effective_clinic_key,
        )
    )
    setting = setting_result.scalar_one_or_none()
    if setting and not setting.is_enabled:
        return await build_fallback_decision(
            db,
            effective_clinic_key,
            "routing_disabled",
            "Маршрутизация для клиники отключена. Использован опросник по умолчанию.",
        )

    if clinic_reason_code == "unknown_clinic" and clinic_key is None:
        logger.info(
            f"Клиника для сделки не определена по CATEGORY_ID={deal_data.get('CATEGORY_ID')!r}; "
            f"используется fallback clinic_key={effective_clinic_key}"
        )

    try:
        result = await db.execute(
            select(SurveyRoutingRule)
            .options(selectinload(SurveyRoutingRule.conditions))
            .where(
                SurveyRoutingRule.clinic_key == effective_clinic_key,
                SurveyRoutingRule.is_active == True,
            )
            .order_by(SurveyRoutingRule.priority.asc(), SurveyRoutingRule.id.asc())
        )
        rules = result.scalars().all()

        for rule in rules:
            if not rule_matches(rule, deal_data):
                continue

            config = await get_active_survey_config(db, rule.survey_config_id)
            if config is None:
                return await build_fallback_decision(
                    db,
                    effective_clinic_key,
                    "survey_config_missing",
                    f"Правило \"{rule.name}\" подошло, но выбранный опросник недоступен. Использован опросник по умолчанию.",
                )

            return SurveyRoutingDecision(
                clinic_key=effective_clinic_key,
                survey_config_id=config.id,
                survey_name=config.name,
                selected_rule_id=rule.id,
                selected_rule_name=rule.name,
                fallback_used=False,
                reason_code="matched_rule",
                reason=f"Подошло правило \"{rule.name}\".",
            )

    except Exception as exc:
        logger.exception(f"Ошибка оценки правил маршрутизации опросника: {exc}")
        return await build_fallback_decision(
            db,
            effective_clinic_key,
            "rule_evaluation_error",
            "При проверке правил произошла ошибка. Использован опросник по умолчанию.",
            error=str(exc),
        )

    return await build_fallback_decision(
        db,
        effective_clinic_key,
        "no_rule_matched",
        "Ни одно активное правило не подошло. Использован опросник по умолчанию.",
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
