"""Синхронизация metadata CRM-полей Bitrix24 в локальную БД."""

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BitrixCrmField, BitrixCrmFieldOption
from app.services.bitrix24 import Bitrix24Client


def _field_title(field_id: str, metadata: dict[str, Any]) -> str:
    for key in ("title", "formLabel", "listLabel", "filterLabel", "name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return field_id


def _field_type(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("type")
    return str(value).strip() if value is not None and str(value).strip() else None


def _field_items(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    items = metadata.get("items")
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
