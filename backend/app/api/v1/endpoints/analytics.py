# ============================================
# Analytics Endpoints - Эндпоинты аналитики
# ============================================
"""
API для сбора и отдачи статистики по опросам.
Используется в дашборде админ-панели.
"""

from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, case, text
from loguru import logger

from app.core.database import get_db
from app.models import SurveySession, SurveyAnswer, SurveyConfig
from app.api.v1.endpoints.survey_editor import verify_admin_session


router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get("/dashboard")
async def get_dashboard_stats(
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата конца (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _admin: bool = Depends(verify_admin_session),
):
    """
    Получить сводную статистику для дашборда.

    Возвращает:
    - Динамику пройденных опросов по дням
    - Топ-10 популярных вариантов ответа
    - Воронку прохождения опроса
    - Среднее время прохождения
    - Статистику по статусам сессий
    """

    # --- Определяем диапазон дат ---
    try:
        if date_from:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        else:
            dt_from = datetime.utcnow() - timedelta(days=6)  # Неделя по умолчанию

        if date_to:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(
                hours=23, minutes=59, seconds=59
            )
        else:
            dt_to = datetime.utcnow()
    except ValueError:
        dt_from = datetime.utcnow() - timedelta(days=6)
        dt_to = datetime.utcnow()

    # ================================================
    # БЛОК 1: Динамика завершённых опросов по дням
    # ================================================
    completed_by_day_q = await db.execute(
        select(
            cast(SurveySession.completed_at, Date).label("day"),
            func.count().label("count"),
        )
        .where(
            SurveySession.status == "completed",
            SurveySession.completed_at >= dt_from,
            SurveySession.completed_at <= dt_to,
        )
        .group_by(cast(SurveySession.completed_at, Date))
        .order_by(cast(SurveySession.completed_at, Date))
    )
    completed_rows = completed_by_day_q.all()

    # Заполняем пропуски (дни без опросов = 0)
    day_map = {str(row.day): row.count for row in completed_rows}
    chart_labels = []
    chart_values = []
    current = dt_from.date() if isinstance(dt_from, datetime) else dt_from
    end = dt_to.date() if isinstance(dt_to, datetime) else dt_to
    while current <= end:
        chart_labels.append(current.strftime("%d.%m"))
        chart_values.append(day_map.get(str(current), 0))
        current += timedelta(days=1)

    # Число пройденных опросов за сегодня
    today = date.today()
    today_count_q = await db.execute(
        select(func.count()).where(
            SurveySession.status == "completed",
            cast(SurveySession.completed_at, Date) == today,
        )
    )
    today_count = today_count_q.scalar() or 0

    # Среднее время прохождения (в минутах)
    avg_time_q = await db.execute(
        select(
            func.avg(
                func.extract("epoch", SurveySession.completed_at)
                - func.extract("epoch", SurveySession.started_at)
            )
        ).where(
            SurveySession.status == "completed",
            SurveySession.completed_at.isnot(None),
            SurveySession.started_at.isnot(None),
        )
    )
    avg_seconds = avg_time_q.scalar()
    avg_minutes = round(avg_seconds / 60, 1) if avg_seconds else 0

    # Общее число за выбранный период
    total_completed = sum(chart_values)

    # ================================================
    # Общая статистика по статусам
    # ================================================
    statuses_q = await db.execute(
        select(
            SurveySession.status,
            func.count().label("cnt"),
        ).group_by(SurveySession.status)
    )
    statuses = {row.status: row.cnt for row in statuses_q.all()}

    # ================================================
    # БЛОК 2: Топ ответов (частота выбора вариантов)
    # ================================================
    # Получаем ВСЕ ответы из завершённых сессий
    all_answers_q = await db.execute(
        select(SurveyAnswer.node_id, SurveyAnswer.answer_data).join(
            SurveySession, SurveySession.id == SurveyAnswer.session_id
        ).where(SurveySession.status == "completed")
    )
    all_answers = all_answers_q.all()

    # Получаем конфиг опросника для маппинга node_id → текст вопроса / текст ответа
    config_q = await db.execute(
        select(SurveyConfig.json_config).where(SurveyConfig.is_active == True).limit(1)
    )
    config_json = config_q.scalar()

    # Строим маппинг node_id → {question_text, options: {value → text}}
    node_map = {}
    if config_json and config_json.get("nodes"):
        for node in config_json["nodes"]:
            opts = {}
            for opt in node.get("options", []):
                opts[str(opt.get("value", ""))] = opt.get("text", "")
            node_map[node["id"]] = {
                "question_text": node.get("question_text", node["id"]),
                "options": opts,
            }

    # Подсчёт частоты каждого варианта
    answer_freq = {}  # {(node_id, value_label): count}
    for row in all_answers:
        node_id = row.node_id
        data = row.answer_data
        if not data:
            continue

        node_info = node_map.get(node_id, {"question_text": node_id, "options": {}})
        q_text = node_info["question_text"]
        options_map = node_info["options"]

        # Обработка разных форматов answer_data
        selected = data.get("selected") or data.get("value")
        if selected is None:
            # Для body_map и подобных — пропускаем или берём areas
            areas = data.get("areas")
            if areas and isinstance(areas, list):
                for area in areas:
                    label = area if isinstance(area, str) else str(area)
                    readable = options_map.get(label, label)
                    key = f"{q_text} → {readable}"
                    answer_freq[key] = answer_freq.get(key, 0) + 1
            continue

        if isinstance(selected, list):
            for val in selected:
                val_str = str(val)
                readable = options_map.get(val_str, val_str)
                key = f"{q_text} → {readable}"
                answer_freq[key] = answer_freq.get(key, 0) + 1
        else:
            val_str = str(selected)
            readable = options_map.get(val_str, val_str)
            key = f"{q_text} → {readable}"
            answer_freq[key] = answer_freq.get(key, 0) + 1

    # Сортировка по убыванию
    sorted_answers = sorted(answer_freq.items(), key=lambda x: x[1], reverse=True)
    top_10 = sorted_answers[:10]
    all_answers_stats = sorted_answers

    # ================================================
    # БЛОК 4: Воронка прохождения (drop-off)
    # ================================================
    # Считаем сколько сессий ответили на каждый node_id (в выбранном периоде)
    funnel_q = await db.execute(
        select(
            SurveyAnswer.node_id,
            func.count(func.distinct(SurveyAnswer.session_id)).label("cnt"),
        )
        .join(SurveySession, SurveySession.id == SurveyAnswer.session_id)
        .where(
            SurveySession.started_at >= dt_from,
            SurveySession.started_at <= dt_to,
        )
        .group_by(SurveyAnswer.node_id)
        .order_by(func.count(func.distinct(SurveyAnswer.session_id)).desc())
    )
    funnel_rows = funnel_q.all()
    funnel_data = []
    for row in funnel_rows:
        node_info = node_map.get(row.node_id, {"question_text": row.node_id})
        funnel_data.append(
            {
                "node_id": row.node_id,
                "label": node_info["question_text"],
                "count": row.cnt,
            }
        )

    # ================================================
    # Формируем ответ
    # ================================================
    return {
        "chart": {
            "labels": chart_labels,
            "values": chart_values,
            "total": total_completed,
            "today": today_count,
            "avg_minutes": avg_minutes,
        },
        "statuses": statuses,
        "top_answers": [{"label": k, "count": v} for k, v in top_10],
        "all_answers": [{"label": k, "count": v} for k, v in all_answers_stats],
        "funnel": funnel_data,
    }
