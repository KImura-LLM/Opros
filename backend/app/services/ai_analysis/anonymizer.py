"""Allowlist-анонимизатор ответов анкеты для внешнего ИИ-сервиса."""

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID


MAX_FREE_TEXT_CHARS = 1500
MAX_ANSWER_TEXT_CHARS = 2500
MAX_PAYLOAD_BYTES = 80 * 1024
FORBIDDEN_PAYLOAD_KEYS = {
    "id",
    "session_id",
    "survey_session_id",
    "lead_id",
    "deal_id",
    "crm_id",
    "entity_id",
    "patient_name",
    "doctor_name",
    "token",
    "token_hash",
    "ip_address",
    "user_agent",
    "survey_link",
    "raw_crm",
}


class AiPayloadTooLargeError(ValueError):
    """Payload после нормализации всё ещё слишком большой для безопасной отправки."""


class AiPayloadPrivacyError(ValueError):
    """Payload содержит запрещённые идентификаторы на верхнем уровне."""


class _AnswerLike:
    node_id: str
    answer_data: dict[str, Any]
    duration_seconds: int | None


def _truncate_text(value: Any, limit: int = MAX_FREE_TEXT_CHARS) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _option_text(node: dict[str, Any], value: Any) -> str:
    raw = str(value)
    for option in node.get("options", []) or []:
        if str(option.get("value", option.get("id", ""))) == raw or str(option.get("id", "")) == raw:
            return _truncate_text(option.get("text", raw), MAX_ANSWER_TEXT_CHARS)
    return _truncate_text(raw, MAX_ANSWER_TEXT_CHARS)


def _additional_field_text(field: dict[str, Any], value: Any) -> str:
    raw = str(value)
    for option in field.get("options", []) or []:
        option_value = option.get("value", option.get("id", ""))
        if str(option_value) == raw or str(option.get("id", "")) == raw:
            return _truncate_text(option.get("text", raw), MAX_ANSWER_TEXT_CHARS)
    return _truncate_text(raw, MAX_ANSWER_TEXT_CHARS)


def _format_answer(node: dict[str, Any], answer_data: dict[str, Any]) -> str:
    """Нормализует только клинические поля ответа, без системных идентификаторов."""
    parts: list[str] = []

    selected = answer_data.get("selected")
    if selected is not None:
        if isinstance(selected, list):
            selected_text = ", ".join(_option_text(node, item) for item in selected)
        elif isinstance(selected, bool):
            selected_text = "Да" if selected else "Нет"
        else:
            selected_text = _option_text(node, selected)
        if selected_text:
            parts.append(selected_text)

    if answer_data.get("value") is not None:
        value = answer_data.get("value")
        max_value = node.get("max_value")
        if max_value is not None:
            parts.append(f"{_truncate_text(value)}/{_truncate_text(max_value)}")
        else:
            parts.append(_truncate_text(value, MAX_ANSWER_TEXT_CHARS))

    text_value = answer_data.get("text")
    if isinstance(text_value, str) and text_value.strip():
        parts.append(_truncate_text(text_value, MAX_FREE_TEXT_CHARS))

    locations = answer_data.get("locations")
    if isinstance(locations, list) and locations:
        parts.append("Локализация: " + ", ".join(_option_text(node, item) for item in locations))

    intensity = answer_data.get("intensity")
    if intensity is not None:
        parts.append(f"Интенсивность: {_truncate_text(intensity)}/10")

    for field in node.get("additional_fields", []) or []:
        field_id = field.get("id")
        if not field_id or field_id not in answer_data:
            continue
        field_value = answer_data.get(field_id)
        if field_value in (None, "", []):
            continue
        field_label = field.get("label") or field_id
        if isinstance(field_value, list):
            value_text = ", ".join(_additional_field_text(field, item) for item in field_value)
        else:
            value_text = _additional_field_text(field, field_value)
        parts.append(f"{_truncate_text(field_label, 200)}: {value_text}")

    # Узкий fallback для частых клинических текстовых полей, если они не описаны
    # в additional_fields. Системные/CRM ключи сюда не попадают.
    for key in ("other_text", "comment", "details", "description", "additional_text"):
        value = answer_data.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(_truncate_text(value, MAX_FREE_TEXT_CHARS))

    return "; ".join(part for part in parts if part).strip()[:MAX_ANSWER_TEXT_CHARS]


def _group_by_node(config_json: dict[str, Any]) -> dict[str, str | None]:
    group_names = {g.get("id"): g.get("name") for g in config_json.get("groups", []) or [] if g.get("id")}
    mapping: dict[str, str | None] = {}
    for node in config_json.get("nodes", []) or []:
        node_id = node.get("id")
        if not node_id:
            continue
        group_id = node.get("group") or node.get("group_id")
        mapping[node_id] = group_names.get(group_id) if group_id else None
    return mapping


def build_anonymized_payload(
    *,
    analysis_case_id: str | UUID,
    survey_config_id: int | None,
    config_json: dict[str, Any],
    answers: list[_AnswerLike] | tuple[_AnswerLike, ...],
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Собирает outbound payload только через allowlist клинических полей."""
    nodes = {node.get("id"): node for node in config_json.get("nodes", []) or [] if node.get("id")}
    group_map = _group_by_node(config_json)

    clinical_answers: list[dict[str, Any]] = []
    for answer in answers:
        node_id = str(answer.node_id)
        node = nodes.get(node_id)
        if not node or node.get("type") == "info_screen":
            continue

        answer_data = answer.answer_data if isinstance(answer.answer_data, dict) else {}
        formatted_answer = _format_answer(node, answer_data)
        if not formatted_answer:
            continue

        item: dict[str, Any] = {
            "node_id": node_id,
            "question": _truncate_text(node.get("question_text") or node_id, 500),
            "answer": formatted_answer,
            "type": _truncate_text(node.get("type") or "unknown", 80),
        }
        group_name = group_map.get(node_id)
        if group_name:
            item["group"] = _truncate_text(group_name, 200)
        if getattr(answer, "duration_seconds", None) is not None:
            item["duration_seconds"] = int(answer.duration_seconds)
        clinical_answers.append(item)

    payload: dict[str, Any] = {
        "analysis_case_id": str(analysis_case_id),
        "survey_config_id": survey_config_id,
        "survey_version": _truncate_text(config_json.get("version") or "unknown", 50),
        "answers": clinical_answers,
    }
    if completed_at:
        payload["completed_date"] = completed_at.date().isoformat()

    forbidden = FORBIDDEN_PAYLOAD_KEYS & set(payload.keys())
    if forbidden:
        raise AiPayloadPrivacyError(f"Forbidden payload keys: {sorted(forbidden)}")

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise AiPayloadTooLargeError("Anonymized AI payload exceeds safe size limit")

    return payload


def hash_payload(payload: dict[str, Any]) -> str:
    """Хэш обезличенного payload без сохранения самого prompt в БД."""
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
