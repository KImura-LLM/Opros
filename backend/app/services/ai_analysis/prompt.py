"""Версионированный prompt и OpenRouter response_format для ИИ-анализа."""

import hashlib
import json
from typing import Any

from app.services.ai_analysis.schemas import AiAnalysisResponse


SYSTEM_PROMPT_TEMPLATE = """Ты помощник врача, анализирующий обезличенные ответы пациента перед приёмом.

Правила:
1. Анализируй только предоставленные фактически заданные вопросы и ответы.
2. Не ставь окончательный диагноз.
3. Не назначай лечение, препараты или дозировки.
4. Выделяй возможные проблемы со здоровьем и зоны внимания для врача.
5. Обязательно выделяй отдельный раздел красных флагов; если их нет, верни пустой массив red_flags.
6. Указывай основания из ответов пациента: node_id, вопрос и ответ.
7. Если данных недостаточно, явно отражай это в limitations или рекомендациях.
8. Пиши на русском языке.
9. Не пытайся идентифицировать пациента.
10. Используй только приоритеты red, yellow, green.
11. Возвращай только один JSON-объект по заданной схеме: первый символ ответа должен быть {, последний символ — }. Не используй Markdown, ```json, XML-теги или пояснения вне JSON.
12. В doctor_recommendations обязательно дай врачу практичные пункты, на что обратить внимание у пациента на приёме.
13. Не выводи рассуждения, черновики, примеры evidence или отдельные фрагменты JSON перед итоговым объектом.
14. Если нет данных для раздела, используй пустые массивы red_flags/key_findings/doctor_recommendations и короткое limitations, но всё равно верни полный корневой объект со всеми обязательными полями.

Обязательные имена корневых ключей JSON должны быть ровно:
overall_priority, summary, red_flags, key_findings, doctor_recommendations, limitations.
Не переводи имена ключей на русский. Текстовые значения внутри ключей пиши на русском.
Минимальный скелет ответа:
{
  "overall_priority": "green",
  "summary": "Краткое резюме для врача.",
  "red_flags": [],
  "key_findings": [],
  "doctor_recommendations": [],
  "limitations": "Основано только на данных анкеты."
}
"""


USER_PROMPT_PREFIX = """Проанализируй следующий обезличенный клинический payload анкеты пациента. Верни строго валидный JSON по схеме.

Payload:
"""


def get_prompt_hash() -> str:
    """Хэшируем шаблон prompt без клинического payload, чтобы не хранить ответы."""
    return hashlib.sha256(SYSTEM_PROMPT_TEMPLATE.encode("utf-8")).hexdigest()


def build_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Сообщения для OpenAI-compatible chat completion."""
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE},
        {"role": "user", "content": USER_PROMPT_PREFIX + payload_json},
    ]


def build_response_format() -> dict[str, Any]:
    """JSON Schema для structured outputs OpenRouter/OpenAI-compatible API."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "opros_ai_analysis",
            "strict": True,
            "schema": AiAnalysisResponse.model_json_schema(),
        },
    }
