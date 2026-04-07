# ============================================
# Analytics Endpoints - Эндпоинты аналитики
# ============================================
"""
API для сбора и отдачи статистики по опросам.
Используется в дашборде админ-панели.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Date, cast, func, select

from app.core.database import get_db
from app.models import SurveySession, SurveyAnswer, SurveyConfig
from app.api.v1.endpoints.survey_editor import verify_admin_session


router = APIRouter(prefix="/analytics", tags=["Аналитика"])


def _parse_dashboard_range(date_from: Optional[str], date_to: Optional[str]) -> tuple[datetime | None, datetime | None]:
    """Нормализует выбранные даты. Если фильтр пустой, диапазон не ограничивается."""
    try:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC) if date_from else None
        dt_to = (
            datetime.combine(
                datetime.strptime(date_to, "%Y-%m-%d").date(),
                time.max,
                tzinfo=UTC,
            )
            if date_to
            else None
        )
    except ValueError:
        dt_from = None
        dt_to = None

    return dt_from, dt_to


def _apply_period_filters(stmt: Any, date_column: Any, dt_from: datetime | None, dt_to: datetime | None) -> Any:
    """Добавляет фильтр по периоду только когда админ явно выбрал даты."""
    if dt_from is not None:
        stmt = stmt.where(date_column >= dt_from)
    if dt_to is not None:
        stmt = stmt.where(date_column <= dt_to)
    return stmt


def _build_completed_chart_series(
    completed_rows: list[Any],
    dt_from: datetime | None,
    dt_to: datetime | None,
) -> tuple[list[str], list[int]]:
    """Готовит подписи и значения для графика завершённых опросов."""
    if not completed_rows:
        if dt_from is None or dt_to is None:
            return [], []

        chart_labels: list[str] = []
        chart_values: list[int] = []
        current = dt_from.date()
        end = dt_to.date()
        while current <= end:
            chart_labels.append(current.strftime("%d.%m"))
            chart_values.append(0)
            current += timedelta(days=1)
        return chart_labels, chart_values

    first_day = completed_rows[0].day
    last_day = completed_rows[-1].day
    start_day = dt_from.date() if dt_from is not None else first_day
    end_day = dt_to.date() if dt_to is not None else last_day

    day_map = {str(row.day): row.count for row in completed_rows}
    chart_labels = []
    chart_values = []
    current = start_day
    while current <= end_day:
        chart_labels.append(current.strftime("%d.%m"))
        chart_values.append(day_map.get(str(current), 0))
        current += timedelta(days=1)

    return chart_labels, chart_values


def _build_node_map(config_rows: list[Any]) -> dict[str, dict[str, Any]]:
    """Собирает справочник question_text/options по всем версиям конфигов."""
    node_map: dict[str, dict[str, Any]] = {}
    for config_row in reversed(config_rows):
        config_json = config_row.json_config
        if not config_json or not config_json.get("nodes"):
            continue

        for node in config_json["nodes"]:
            opts = {}
            for opt in node.get("options", []):
                opts[str(opt.get("value", ""))] = opt.get("text", "")

            node_map[node["id"]] = {
                "question_text": node.get("question_text", node["id"]),
                "options": opts,
            }

    return node_map


def _extract_answer_labels(node_info: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Преобразует сырой answer_data в человекочитаемые подписи."""
    labels: list[str] = []
    options_map = node_info.get("options", {})
    question_text = node_info.get("question_text", "unknown")

    locations = data.get("locations")
    if isinstance(locations, list) and locations:
        for location in locations:
            location_id = str(location)
            readable = options_map.get(location_id, location_id)
            labels.append(f"{question_text} → {readable}")
        return labels

    areas = data.get("areas")
    if isinstance(areas, list) and areas:
        for area in areas:
            area_id = str(area.get("id", "")) if isinstance(area, dict) else str(area)
            readable = options_map.get(area_id, area_id)
            labels.append(f"{question_text} → {readable}")
        return labels

    selected = data.get("selected")
    if selected is not None:
        selected_values = selected if isinstance(selected, list) else [selected]
        for value in selected_values:
            value_str = str(value)
            readable = options_map.get(value_str, value_str)
            labels.append(f"{question_text} → {readable}")
        return labels

    value = data.get("value")
    if value is not None:
        labels.append(f"{question_text} → {value}")

    return labels


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
    dt_from, dt_to = _parse_dashboard_range(date_from, date_to)

    # ================================================
    # БЛОК 1: Динамика завершённых опросов по дням
    # ================================================
    completed_by_day_stmt = (
        select(
            cast(SurveySession.completed_at, Date).label("day"),
            func.count().label("count"),
        )
        .where(SurveySession.status == "completed")
        .group_by(cast(SurveySession.completed_at, Date))
        .order_by(cast(SurveySession.completed_at, Date))
    )
    completed_by_day_stmt = _apply_period_filters(
        completed_by_day_stmt,
        SurveySession.completed_at,
        dt_from,
        dt_to,
    )
    completed_by_day_q = await db.execute(completed_by_day_stmt)
    completed_rows = completed_by_day_q.all()

    # Заполняем пропуски (дни без опросов = 0)
    chart_labels, chart_values = _build_completed_chart_series(completed_rows, dt_from, dt_to)

    # Число пройденных опросов за сегодня
    today = datetime.now(UTC).date()
    today_count_q = await db.execute(
        select(func.count()).where(
            SurveySession.status == "completed",
            cast(SurveySession.completed_at, Date) == today,
        )
    )
    today_count = today_count_q.scalar() or 0

    # Среднее время прохождения (в минутах)
    avg_time_stmt = (
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
    avg_time_stmt = _apply_period_filters(
        avg_time_stmt,
        SurveySession.completed_at,
        dt_from,
        dt_to,
    )
    avg_time_q = await db.execute(avg_time_stmt)
    avg_seconds = avg_time_q.scalar()
    avg_minutes = round(avg_seconds / 60, 1) if avg_seconds else 0

    # Общее число за выбранный период
    total_completed = sum(chart_values)

    # ================================================
    # Общая статистика по статусам
    # ================================================
    status_date = func.coalesce(SurveySession.completed_at, SurveySession.started_at)
    statuses_stmt = (
        select(
            SurveySession.status,
            func.count().label("cnt"),
        )
        .group_by(SurveySession.status)
    )
    statuses_stmt = _apply_period_filters(statuses_stmt, status_date, dt_from, dt_to)
    statuses_q = await db.execute(statuses_stmt)
    statuses = {row.status: row.cnt for row in statuses_q.all()}

    # ================================================
    # БЛОК 2: Топ ответов (частота выбора вариантов)
    # ================================================
    # Получаем ВСЕ ответы из завершённых сессий
    all_answers_stmt = (
        select(SurveyAnswer.node_id, SurveyAnswer.answer_data).join(
            SurveySession, SurveySession.id == SurveyAnswer.session_id
        ).where(
            SurveySession.status == "completed",
        )
    )
    all_answers_stmt = _apply_period_filters(
        all_answers_stmt,
        SurveySession.completed_at,
        dt_from,
        dt_to,
    )
    all_answers_q = await db.execute(all_answers_stmt)
    all_answers = all_answers_q.all()

    # Получаем ВСЕ конфиги опросника для маппинга node_id → текст вопроса / текст ответа
    # (ответы могли быть записаны по разным версиям конфига)
    all_configs_q = await db.execute(
        select(SurveyConfig.json_config, SurveyConfig.is_active)
        .order_by(SurveyConfig.is_active.desc(), SurveyConfig.id.desc())
    )
    all_configs = all_configs_q.all()

    # Строим маппинг node_id → {question_text, options: {value → text}}
    # Сначала загружаем старые конфиги, затем активный — активный перезаписывает,
    # тем самым для актуальных узлов берётся свежий текст, а старые узлы не теряются
    node_map = _build_node_map(all_configs)

    # Подсчёт частоты каждого варианта
    answer_freq = {}  # {"Текст вопроса → Текст ответа": count}
    for row in all_answers:
        node_id = row.node_id
        data = row.answer_data
        if not data:
            continue

        node_info = node_map.get(node_id, {"question_text": node_id, "options": {}})
        for key in _extract_answer_labels(node_info, data):
            answer_freq[key] = answer_freq.get(key, 0) + 1

    # Сортировка по убыванию
    sorted_answers = sorted(answer_freq.items(), key=lambda x: x[1], reverse=True)
    top_10 = sorted_answers[:10]
    all_answers_stats = sorted_answers

    # ================================================
    # БЛОК 4: Воронка прохождения (drop-off)
    # ================================================
    # Для каждой НЕзавершённой сессии (abandoned + in_progress) находим
    # последний отвеченный вопрос — это точка, на которой пациент прекратил
    # прохождение. Используем подзапрос: max(id) ответа для каждой такой сессии,
    # затем группируем по node_id и считаем количество выходов на каждом вопросе.

    # Подзапрос: последний ответ (максимальный id) для каждой незавершённой сессии
    last_answer_stmt = (
        select(
            SurveyAnswer.session_id,
            func.max(SurveyAnswer.id).label("last_answer_id"),
        )
        .join(SurveySession, SurveySession.id == SurveyAnswer.session_id)
        .where(
            SurveySession.status.in_(["abandoned", "in_progress"]),
        )
        .group_by(SurveyAnswer.session_id)
    )
    last_answer_stmt = _apply_period_filters(
        last_answer_stmt,
        SurveySession.started_at,
        dt_from,
        dt_to,
    )
    last_answer_subq = last_answer_stmt.subquery()

    # Основной запрос: берём node_id последнего ответа и считаем частоту
    funnel_q = await db.execute(
        select(
            SurveyAnswer.node_id,
            func.count().label("cnt"),
        )
        .join(last_answer_subq, SurveyAnswer.id == last_answer_subq.c.last_answer_id)
        .group_by(SurveyAnswer.node_id)
        .order_by(func.count().desc())
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
    # БЛОК 5: Среднее время ответа на каждый вопрос
    # ================================================
    # Среднее время (в секундах), затраченное на каждый вопрос
    # Учитываем только ответы с заполненным duration_seconds
    answer_time_stmt = (
        select(
            SurveyAnswer.node_id,
            func.avg(SurveyAnswer.duration_seconds).label("avg_duration"),
            func.min(SurveyAnswer.duration_seconds).label("min_duration"),
            func.max(SurveyAnswer.duration_seconds).label("max_duration"),
            func.count().label("sample_count"),
        )
        .join(SurveySession, SurveySession.id == SurveyAnswer.session_id)
        .where(
            SurveySession.status == "completed",
            SurveyAnswer.duration_seconds.isnot(None),
            SurveyAnswer.duration_seconds > 0,
        )
        .group_by(SurveyAnswer.node_id)
        .order_by(func.avg(SurveyAnswer.duration_seconds).desc())
    )
    answer_time_stmt = _apply_period_filters(
        answer_time_stmt,
        SurveySession.completed_at,
        dt_from,
        dt_to,
    )
    answer_time_q = await db.execute(answer_time_stmt)
    answer_time_rows = answer_time_q.all()

    answer_times_data = []
    for row in answer_time_rows:
        node_info = node_map.get(row.node_id, {"question_text": row.node_id})
        avg_sec = round(float(row.avg_duration), 1)
        answer_times_data.append({
            "node_id": row.node_id,
            "label": node_info["question_text"],
            "avg_seconds": avg_sec,
            "min_seconds": int(row.min_duration),
            "max_seconds": int(row.max_duration),
            "sample_count": row.sample_count,
        })

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
        "answer_times": answer_times_data,
    }
