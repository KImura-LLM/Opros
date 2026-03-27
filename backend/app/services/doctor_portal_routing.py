"""
Правила маршрутизации сессий портала врачей по воронкам Bitrix24.
"""

from typing import Any


PORTAL_CLINIC_BUCKET_NOVOSIBIRSK = "novosibirsk"
PORTAL_CLINIC_BUCKET_KEMEROVO = "kemerovo"
PORTAL_CLINIC_BUCKET_YAROSLAVL = "yaroslavl"
PORTAL_CLINIC_BUCKET_TEST = "test"

PORTAL_CLINIC_BUCKETS = (
    PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
    PORTAL_CLINIC_BUCKET_KEMEROVO,
    PORTAL_CLINIC_BUCKET_YAROSLAVL,
    PORTAL_CLINIC_BUCKET_TEST,
)

PORTAL_CLINIC_BUCKET_LABELS = {
    PORTAL_CLINIC_BUCKET_NOVOSIBIRSK: "Новосибирск",
    PORTAL_CLINIC_BUCKET_KEMEROVO: "Кемерово",
    PORTAL_CLINIC_BUCKET_YAROSLAVL: "Ярославль",
    PORTAL_CLINIC_BUCKET_TEST: "Тест",
}

BITRIX_CATEGORY_TO_PORTAL_BUCKET = {
    "0": PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
    "1": PORTAL_CLINIC_BUCKET_KEMEROVO,
    "3": PORTAL_CLINIC_BUCKET_YAROSLAVL,
}


def normalize_bitrix_category_id(raw_value: Any) -> int | None:
    """Нормализует CATEGORY_ID из Bitrix24 в целое число."""
    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        raw_value = raw_value.strip()
        if not raw_value:
            return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def resolve_portal_clinic_bucket(category_id: Any) -> str:
    """Возвращает bucket вкладки портала врачей по CATEGORY_ID."""
    normalized_category_id = normalize_bitrix_category_id(category_id)
    if normalized_category_id is None:
        return PORTAL_CLINIC_BUCKET_TEST

    return BITRIX_CATEGORY_TO_PORTAL_BUCKET.get(
        str(normalized_category_id),
        PORTAL_CLINIC_BUCKET_TEST,
    )


def extract_portal_routing_from_deal(deal_data: dict | None) -> tuple[int | None, str]:
    """Извлекает CATEGORY_ID и bucket вкладки из данных сделки Bitrix24."""
    if not isinstance(deal_data, dict):
        return None, PORTAL_CLINIC_BUCKET_TEST

    category_id = normalize_bitrix_category_id(deal_data.get("CATEGORY_ID"))
    return category_id, resolve_portal_clinic_bucket(category_id)
