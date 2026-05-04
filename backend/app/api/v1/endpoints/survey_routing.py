"""Admin API для маршрутизации опросников по Bitrix24."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.survey_editor import verify_admin_session
from app.core.database import get_db
from app.models import (
    BitrixCrmField,
    BitrixCrmFieldOption,
    SurveyConfig,
    SurveyRoutingClinicSetting,
    SurveyRoutingCondition,
    SurveyRoutingRule,
)
from app.services.bitrix24 import Bitrix24Client
from app.services.bitrix_crm_fields import sync_bitrix_deal_fields
from app.services.survey_routing import (
    CONDITION_LOGICS,
    ROUTING_OPERATORS,
    get_survey_routing_clinics,
    normalize_condition_logic,
    normalize_operator,
    resolve_survey_for_deal,
)


router = APIRouter(prefix="/routing", tags=["Маршрутизация опросников"])


class RoutingClinicItem(BaseModel):
    key: str
    title: str
    default_survey_config_id: int | None = None
    default_survey_name: str | None = None
    is_enabled: bool = True


class RoutingClinicsResponse(BaseModel):
    items: list[RoutingClinicItem]


class RoutingClinicSettingsPayload(BaseModel):
    default_survey_config_id: int | None = None
    is_enabled: bool = True


class RoutingConditionPayload(BaseModel):
    id: int | None = None
    crm_field_id: str = Field(..., min_length=1, max_length=255)
    operator: str
    value: Any = None

    @model_validator(mode="after")
    def validate_condition(self):
        operator = normalize_operator(self.operator)
        self.operator = operator
        if operator not in {"is_filled", "is_empty"}:
            if self.value is None or (isinstance(self.value, str) and not self.value.strip()):
                raise ValueError("Для выбранного оператора нужно указать значение")
        return self


class RoutingRulePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    survey_config_id: int
    condition_logic: str = "AND"
    priority: int | None = None
    conditions: list[RoutingConditionPayload] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def validate_rule(self):
        self.condition_logic = normalize_condition_logic(self.condition_logic)
        return self


class RoutingConditionResponse(RoutingConditionPayload):
    id: int


class RoutingRuleResponse(BaseModel):
    id: int
    clinic_key: str
    name: str
    is_active: bool
    survey_config_id: int
    survey_name: str | None = None
    condition_logic: str
    priority: int
    conditions: list[RoutingConditionResponse]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoutingClinicDetailResponse(BaseModel):
    clinic: RoutingClinicItem
    rules: list[RoutingRuleResponse]


class RoutingReorderItem(BaseModel):
    id: int
    priority: int


class RoutingReorderPayload(BaseModel):
    items: list[RoutingReorderItem]


class CrmFieldItem(BaseModel):
    field_id: str
    title: str
    type: str | None = None
    is_list: bool
    is_active: bool
    synced_at: datetime | None = None


class CrmFieldsResponse(BaseModel):
    items: list[CrmFieldItem]


class CrmFieldOptionItem(BaseModel):
    option_id: str
    label: str
    sort: int | None = None
    is_active: bool


class CrmFieldOptionsResponse(BaseModel):
    items: list[CrmFieldOptionItem]


class TestDealPayload(BaseModel):
    deal_id: int = Field(..., gt=0)


class TestDealResponse(BaseModel):
    success: bool
    clinic_key: str
    deal_id: int
    selected_survey_config_id: int | None
    selected_survey_name: str | None
    selected_rule_id: int | None
    selected_rule_name: str | None
    fallback_used: bool
    reason: str


def _ensure_known_clinic(clinic_key: str) -> dict[str, Any]:
    for clinic in get_survey_routing_clinics():
        if clinic["key"] == clinic_key:
            return clinic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Клиника маршрутизации не найдена.",
    )


async def _ensure_survey_exists(db: AsyncSession, survey_config_id: int | None) -> None:
    if survey_config_id is None:
        return

    result = await db.execute(
        select(SurveyConfig.id).where(
            SurveyConfig.id == survey_config_id,
            SurveyConfig.is_active == True,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Выбранный опросник не найден или отключён.",
        )


async def _next_priority(db: AsyncSession, clinic_key: str) -> int:
    result = await db.execute(
        select(func.max(SurveyRoutingRule.priority)).where(
            SurveyRoutingRule.clinic_key == clinic_key,
        )
    )
    current = result.scalar_one_or_none()
    return int(current or 0) + 10


def _rule_to_response(rule: SurveyRoutingRule) -> RoutingRuleResponse:
    return RoutingRuleResponse(
        id=rule.id,
        clinic_key=rule.clinic_key,
        name=rule.name,
        is_active=rule.is_active,
        survey_config_id=rule.survey_config_id,
        survey_name=rule.survey_config.name if rule.survey_config else None,
        condition_logic=rule.condition_logic,
        priority=rule.priority,
        conditions=[
            RoutingConditionResponse(
                id=condition.id,
                crm_field_id=condition.crm_field_id,
                operator=condition.operator,
                value=condition.value,
            )
            for condition in rule.conditions
        ],
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def _clinic_item(db: AsyncSession, clinic: dict[str, Any]) -> RoutingClinicItem:
    result = await db.execute(
        select(SurveyRoutingClinicSetting, SurveyConfig.name)
        .outerjoin(SurveyConfig, SurveyConfig.id == SurveyRoutingClinicSetting.default_survey_config_id)
        .where(SurveyRoutingClinicSetting.clinic_key == clinic["key"])
    )
    row = result.first()
    if not row:
        return RoutingClinicItem(key=clinic["key"], title=clinic["title"])

    setting, survey_name = row
    return RoutingClinicItem(
        key=clinic["key"],
        title=clinic["title"],
        default_survey_config_id=setting.default_survey_config_id,
        default_survey_name=survey_name,
        is_enabled=setting.is_enabled,
    )


@router.get("/clinics", response_model=RoutingClinicsResponse)
async def list_routing_clinics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    items = [
        await _clinic_item(db, clinic)
        for clinic in get_survey_routing_clinics()
    ]
    return RoutingClinicsResponse(items=items)


@router.get("/clinics/{clinic_key}", response_model=RoutingClinicDetailResponse)
async def get_routing_clinic(
    request: Request,
    clinic_key: str,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    clinic = _ensure_known_clinic(clinic_key)
    clinic_item = await _clinic_item(db, clinic)

    result = await db.execute(
        select(SurveyRoutingRule)
        .options(
            selectinload(SurveyRoutingRule.conditions),
            selectinload(SurveyRoutingRule.survey_config),
        )
        .where(SurveyRoutingRule.clinic_key == clinic_key)
        .order_by(SurveyRoutingRule.priority.desc(), SurveyRoutingRule.id.asc())
    )
    rules = result.scalars().all()

    return RoutingClinicDetailResponse(
        clinic=clinic_item,
        rules=[_rule_to_response(rule) for rule in rules],
    )


@router.put("/clinics/{clinic_key}/settings", response_model=RoutingClinicItem)
async def save_routing_clinic_settings(
    request: Request,
    clinic_key: str,
    payload: RoutingClinicSettingsPayload,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    clinic = _ensure_known_clinic(clinic_key)
    await _ensure_survey_exists(db, payload.default_survey_config_id)

    result = await db.execute(
        select(SurveyRoutingClinicSetting).where(
            SurveyRoutingClinicSetting.clinic_key == clinic_key,
        )
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SurveyRoutingClinicSetting(clinic_key=clinic_key)
        db.add(setting)

    setting.default_survey_config_id = payload.default_survey_config_id
    setting.is_enabled = payload.is_enabled
    setting.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return await _clinic_item(db, clinic)


@router.post("/clinics/{clinic_key}/rules", response_model=RoutingRuleResponse)
async def create_routing_rule(
    request: Request,
    clinic_key: str,
    payload: RoutingRulePayload,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    _ensure_known_clinic(clinic_key)
    await _ensure_survey_exists(db, payload.survey_config_id)

    rule = SurveyRoutingRule(
        clinic_key=clinic_key,
        name=payload.name.strip(),
        is_active=payload.is_active,
        survey_config_id=payload.survey_config_id,
        condition_logic=payload.condition_logic,
        priority=payload.priority if payload.priority is not None else await _next_priority(db, clinic_key),
    )
    for condition in payload.conditions:
        rule.conditions.append(
            SurveyRoutingCondition(
                crm_field_id=condition.crm_field_id.strip(),
                operator=condition.operator,
                value=condition.value,
            )
        )

    db.add(rule)
    await db.commit()

    result = await db.execute(
        select(SurveyRoutingRule)
        .options(
            selectinload(SurveyRoutingRule.conditions),
            selectinload(SurveyRoutingRule.survey_config),
        )
        .where(SurveyRoutingRule.id == rule.id)
    )
    return _rule_to_response(result.scalar_one())


@router.put("/rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(
    request: Request,
    rule_id: int,
    payload: RoutingRulePayload,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    await _ensure_survey_exists(db, payload.survey_config_id)
    result = await db.execute(
        select(SurveyRoutingRule)
        .options(selectinload(SurveyRoutingRule.conditions))
        .where(SurveyRoutingRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Правило не найдено.")

    rule.name = payload.name.strip()
    rule.is_active = payload.is_active
    rule.survey_config_id = payload.survey_config_id
    rule.condition_logic = payload.condition_logic
    if payload.priority is not None:
        rule.priority = payload.priority
    rule.updated_at = datetime.now(timezone.utc)

    await db.execute(delete(SurveyRoutingCondition).where(SurveyRoutingCondition.rule_id == rule.id))
    for condition in payload.conditions:
        db.add(
            SurveyRoutingCondition(
                rule_id=rule.id,
                crm_field_id=condition.crm_field_id.strip(),
                operator=condition.operator,
                value=condition.value,
            )
        )

    await db.commit()

    refreshed = await db.execute(
        select(SurveyRoutingRule)
        .options(
            selectinload(SurveyRoutingRule.conditions),
            selectinload(SurveyRoutingRule.survey_config),
        )
        .where(SurveyRoutingRule.id == rule.id)
    )
    return _rule_to_response(refreshed.scalar_one())


@router.delete("/rules/{rule_id}")
async def delete_routing_rule(
    request: Request,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    result = await db.execute(select(SurveyRoutingRule).where(SurveyRoutingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Правило не найдено.")

    await db.delete(rule)
    await db.commit()
    return {"success": True}


@router.post("/clinics/{clinic_key}/rules/reorder")
async def reorder_routing_rules(
    request: Request,
    clinic_key: str,
    payload: RoutingReorderPayload,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    _ensure_known_clinic(clinic_key)
    ids = [item.id for item in payload.items]
    result = await db.execute(
        select(SurveyRoutingRule).where(
            SurveyRoutingRule.clinic_key == clinic_key,
            SurveyRoutingRule.id.in_(ids),
        )
    )
    rules = {rule.id: rule for rule in result.scalars().all()}
    for item in payload.items:
        if item.id in rules:
            rules[item.id].priority = item.priority
            rules[item.id].updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True}


@router.get("/crm-fields", response_model=CrmFieldsResponse)
async def list_crm_fields(
    request: Request,
    search: str = "",
    field_type: str = "",
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    query = select(BitrixCrmField).where(BitrixCrmField.entity_type == "DEAL")
    if active_only:
        query = query.where(BitrixCrmField.is_active == True)
    if field_type:
        query = query.where(BitrixCrmField.type == field_type)
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.where(
            or_(
                BitrixCrmField.field_id.ilike(pattern),
                BitrixCrmField.title.ilike(pattern),
            )
        )
    query = query.order_by(BitrixCrmField.title.asc()).limit(200)
    result = await db.execute(query)

    return CrmFieldsResponse(
        items=[
            CrmFieldItem(
                field_id=field.field_id,
                title=field.title,
                type=field.type,
                is_list=field.is_list,
                is_active=field.is_active,
                synced_at=field.synced_at,
            )
            for field in result.scalars().all()
        ]
    )


@router.get("/crm-fields/{field_id}/options", response_model=CrmFieldOptionsResponse)
async def list_crm_field_options(
    request: Request,
    field_id: str,
    search: str = "",
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    query = select(BitrixCrmFieldOption).where(
        BitrixCrmFieldOption.entity_type == "DEAL",
        BitrixCrmFieldOption.field_id == field_id,
    )
    if active_only:
        query = query.where(BitrixCrmFieldOption.is_active == True)
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.where(
            or_(
                BitrixCrmFieldOption.option_id.ilike(pattern),
                BitrixCrmFieldOption.label.ilike(pattern),
            )
        )
    query = query.order_by(BitrixCrmFieldOption.sort.asc().nullslast(), BitrixCrmFieldOption.label.asc()).limit(300)
    result = await db.execute(query)

    return CrmFieldOptionsResponse(
        items=[
            CrmFieldOptionItem(
                option_id=option.option_id,
                label=option.label,
                sort=option.sort,
                is_active=option.is_active,
            )
            for option in result.scalars().all()
        ]
    )


@router.post("/crm-fields/sync")
async def sync_crm_fields(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    return await sync_bitrix_deal_fields(db)


@router.post("/clinics/{clinic_key}/test-deal", response_model=TestDealResponse)
async def test_deal_routing(
    request: Request,
    clinic_key: str,
    payload: TestDealPayload,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    _ensure_known_clinic(clinic_key)
    deal_data = await Bitrix24Client().get_deal(payload.deal_id)
    decision = await resolve_survey_for_deal(
        db=db,
        deal_data=deal_data,
        clinic_key=clinic_key,
    )
    return TestDealResponse(
        success=True,
        clinic_key=decision.clinic_key,
        deal_id=payload.deal_id,
        selected_survey_config_id=decision.survey_config_id,
        selected_survey_name=decision.survey_name,
        selected_rule_id=decision.selected_rule_id,
        selected_rule_name=decision.selected_rule_name,
        fallback_used=decision.fallback_used,
        reason=decision.reason,
    )
