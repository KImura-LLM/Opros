"""Синхронизация metadata CRM-полей Bitrix24 в локальную БД."""

from datetime import datetime, timezone
import re
from typing import Any

from loguru import logger
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BitrixCrmField, BitrixCrmFieldOption
from app.services.bitrix24 import Bitrix24Client


def _metadata_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("ru", "RU", "en", "EN"):
            nested = _metadata_text(value.get(key))
            if nested:
                return nested
        for nested_value in value.values():
            nested = _metadata_text(nested_value)
            if nested:
                return nested
    return None


CRM_FIELD_ID_PATTERN = re.compile(r"^UF_CRM_\d+$", re.IGNORECASE)


def _is_technical_field_title(field_id: str, value: str) -> bool:
    normalized_value = value.strip()
    return normalized_value == field_id or bool(CRM_FIELD_ID_PATTERN.fullmatch(normalized_value))


def crm_field_title(field_id: str, metadata: dict[str, Any]) -> str:
    fallback_title: str | None = None
    for key in (
        "title",
        "TITLE",
        "label",
        "LABEL",
        "formLabel",
        "FORM_LABEL",
        "listLabel",
        "LIST_LABEL",
        "listColumnLabel",
        "LIST_COLUMN_LABEL",
        "filterLabel",
        "FILTER_LABEL",
        "listFilterLabel",
        "LIST_FILTER_LABEL",
        "editFormLabel",
        "EDIT_FORM_LABEL",
        "showFilterLabel",
        "SHOW_FILTER_LABEL",
        "name",
        "NAME",
    ):
        value = _metadata_text(metadata.get(key))
        if not value:
            continue
        if _is_technical_field_title(field_id, value):
            fallback_title = fallback_title or value
            continue
        return value
    return fallback_title or field_id


def _field_title(field_id: str, metadata: dict[str, Any]) -> str:
    return crm_field_title(field_id, metadata)


def _field_type(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("type") or metadata.get("USER_TYPE_ID") or metadata.get("userTypeId")
    return str(value).strip() if value is not None and str(value).strip() else None


def _field_items(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    items = metadata.get("items") or metadata.get("LIST") or metadata.get("list")
    return items if isinstance(items, list) else []


def _is_list_field(metadata: dict[str, Any]) -> bool:
    return _field_type(metadata) == "enumeration" or bool(_field_items(metadata))


def _option_label(item: dict[str, Any]) -> str:
    for key in ("VALUE", "value", "NAME", "name", "TITLE", "title"):
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    option_id = item.get("ID") or item.get("id")
    return str(option_id).strip() if option_id is not None else ""


def _option_id(item: dict[str, Any]) -> str | None:
    value = item.get("ID") or item.get("id") or item.get("VALUE") or item.get("value")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _option_sort(item: dict[str, Any]) -> int | None:
    value = item.get("SORT") or item.get("sort")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def sync_bitrix_deal_fields(
    db: AsyncSession,
    client: Bitrix24Client | None = None,
) -> dict[str, Any]:
    """Обновляет локальный кэш полей сделки Bitrix24."""
    client = client or Bitrix24Client()
    synced_at = datetime.now(timezone.utc)
    fields = await client.get_deal_fields()
    user_fields = await client.get_deal_user_fields()

    if not fields:
        logger.warning("Bitrix24 не вернул metadata полей сделки; локальный кэш не изменён")
        return {
            "success": False,
            "fields_updated": 0,
            "options_updated": 0,
            "synced_at": synced_at.isoformat(),
            "message": "Bitrix24 не вернул metadata полей сделки",
        }

    await db.execute(
        update(BitrixCrmField)
        .where(BitrixCrmField.entity_type == "DEAL")
        .values(is_active=False, updated_at=synced_at)
    )
    await db.execute(
        update(BitrixCrmFieldOption)
        .where(BitrixCrmFieldOption.entity_type == "DEAL")
        .values(is_active=False, updated_at=synced_at)
    )

    fields_updated = 0
    options_updated = 0

    for user_field in user_fields:
        if not isinstance(user_field, dict):
            continue

        field_id = (
            user_field.get("FIELD_NAME")
            or user_field.get("fieldName")
            or user_field.get("XML_ID")
            or user_field.get("xmlId")
        )
        if not field_id:
            continue

        normalized_field_id = str(field_id).strip()
        if not normalized_field_id:
            continue

        base_metadata = fields.get(normalized_field_id)
        if isinstance(base_metadata, dict):
            base_metadata.update(user_field)
        else:
            fields[normalized_field_id] = user_field

    for field_id, metadata in fields.items():
        if not isinstance(metadata, dict):
            continue

        field_values = {
            "entity_type": "DEAL",
            "field_id": str(field_id),
            "title": _field_title(str(field_id), metadata),
            "type": _field_type(metadata),
            "is_list": _is_list_field(metadata),
            "is_active": True,
            "raw_metadata": metadata,
            "synced_at": synced_at,
            "updated_at": synced_at,
        }
        stmt = insert(BitrixCrmField).values(**field_values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_bitrix_crm_fields_entity_field",
            set_={
                "title": stmt.excluded.title,
                "type": stmt.excluded.type,
                "is_list": stmt.excluded.is_list,
                "is_active": True,
                "raw_metadata": stmt.excluded.raw_metadata,
                "synced_at": synced_at,
                "updated_at": synced_at,
            },
        )
        await db.execute(stmt)
        fields_updated += 1

        for item in _field_items(metadata):
            if not isinstance(item, dict):
                continue

            option_id = _option_id(item)
            label = _option_label(item)
            if not option_id or not label:
                continue

            option_values = {
                "entity_type": "DEAL",
                "field_id": str(field_id),
                "option_id": option_id,
                "label": label,
                "sort": _option_sort(item),
                "is_active": True,
                "raw_metadata": item,
                "synced_at": synced_at,
                "updated_at": synced_at,
            }
            option_stmt = insert(BitrixCrmFieldOption).values(**option_values)
            option_stmt = option_stmt.on_conflict_do_update(
                constraint="uq_bitrix_crm_field_options_entity_field_option",
                set_={
                    "label": option_stmt.excluded.label,
                    "sort": option_stmt.excluded.sort,
                    "is_active": True,
                    "raw_metadata": option_stmt.excluded.raw_metadata,
                    "synced_at": synced_at,
                    "updated_at": synced_at,
                },
            )
            await db.execute(option_stmt)
            options_updated += 1

    await db.commit()
    logger.info(
        f"CRM-поля Bitrix24 синхронизированы: fields={fields_updated}, options={options_updated}"
    )

    return {
        "success": True,
        "fields_updated": fields_updated,
        "options_updated": options_updated,
        "synced_at": synced_at.isoformat(),
    }
