"""SQLAdmin view for AI-analysis queue/status."""

from markupsafe import Markup, escape
from sqladmin import ModelView

from app.models import SurveyAiAnalysis


def _safe_markup(html: str) -> Markup:
    return Markup(html)  # nosec B704


class SurveyAiAnalysisAdmin(ModelView, model=SurveyAiAnalysis):
    """Мониторинг ИИ-анализа анкет и ручной retry failed/skipped задач."""

    identity = "survey-ai-analysis"
    name = "ИИ-анализ"
    name_plural = "ИИ-анализы"
    icon = "fa-solid fa-robot"

    column_list = [
        SurveyAiAnalysis.id,
        SurveyAiAnalysis.session_id,
        SurveyAiAnalysis.status,
        SurveyAiAnalysis.overall_priority,
        SurveyAiAnalysis.model,
        SurveyAiAnalysis.attempts,
        SurveyAiAnalysis.error_code,
        SurveyAiAnalysis.queued_at,
        SurveyAiAnalysis.completed_at,
        "ai_actions",
    ]
    column_searchable_list = [SurveyAiAnalysis.status, SurveyAiAnalysis.model, SurveyAiAnalysis.error_code]
    column_sortable_list = [
        SurveyAiAnalysis.status,
        SurveyAiAnalysis.overall_priority,
        SurveyAiAnalysis.attempts,
        SurveyAiAnalysis.queued_at,
        SurveyAiAnalysis.completed_at,
    ]
    column_default_sort = [("queued_at", True)]
    column_details_list = [
        SurveyAiAnalysis.id,
        SurveyAiAnalysis.session_id,
        SurveyAiAnalysis.analysis_case_id,
        SurveyAiAnalysis.status,
        SurveyAiAnalysis.model,
        SurveyAiAnalysis.prompt_version,
        SurveyAiAnalysis.prompt_hash,
        SurveyAiAnalysis.request_payload_hash,
        SurveyAiAnalysis.overall_priority,
        SurveyAiAnalysis.error_code,
        SurveyAiAnalysis.error_message,
        SurveyAiAnalysis.attempts,
        SurveyAiAnalysis.response_json,
        SurveyAiAnalysis.queued_at,
        SurveyAiAnalysis.started_at,
        SurveyAiAnalysis.completed_at,
        SurveyAiAnalysis.created_at,
        SurveyAiAnalysis.updated_at,
    ]

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    @staticmethod
    def _status_formatter(model, _prop):
        label_map = {
            "pending": ("⏳ В очереди", "#eff6ff", "#1d4ed8", "#bfdbfe"),
            "running": ("🔄 Выполняется", "#fefce8", "#854d0e", "#fde047"),
            "succeeded": ("✅ Готов", "#f0fdf4", "#166534", "#86efac"),
            "failed": ("❌ Ошибка", "#fef2f2", "#991b1b", "#fca5a5"),
            "skipped": ("⏭️ Пропущен", "#f8fafc", "#475569", "#cbd5e1"),
        }
        label, bg, color, border = label_map.get(model.status, (model.status, "#f8fafc", "#334155", "#cbd5e1"))
        return _safe_markup(
            f'<span style="display:inline-flex;padding:3px 8px;border-radius:10px;'
            f'background:{bg};color:{color};border:1px solid {border};font-size:11px;font-weight:600;">'
            f'{escape(label)}</span>'
        )

    @staticmethod
    def _error_formatter(model, _prop):
        if not model.error_message:
            return "—"
        return escape(str(model.error_message)[:300])

    @staticmethod
    def _ai_actions_formatter(model, _prop):
        if model.status not in {"failed", "skipped"}:
            return Markup('<span style="color:#94a3b8;font-size:12px;">Retry недоступен</span>')

        analysis_id = escape(str(model.id))
        js = (
            "(function(btn){"
            "if(!confirm('Поставить ИИ-анализ в очередь повторно?'))return;"
            "btn.disabled=true;btn.textContent='⏳ В очередь...';"
            f"fetch('/admin/api/ai-analysis/{analysis_id}/retry',"
            "{method:'POST',credentials:'include'})"
            ".then(function(r){return r.json();})"
            ".then(function(d){if(d.success){btn.textContent='✅ Поставлено';setTimeout(function(){location.reload();},900);}"
            "else{alert('Ошибка: '+(d.error||d.detail||'неизвестная ошибка'));btn.disabled=false;btn.textContent='🔁 Повторить';}})"
            ".catch(function(){alert('Ошибка запроса');btn.disabled=false;btn.textContent='🔁 Повторить';})"
            "})(this)"
        )
        return _safe_markup(
            f'<button onclick="{js}" style="display:inline-flex;align-items:center;gap:4px;'
            f'padding:5px 10px;background:linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%);'
            f'color:white;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;">'
            f'🔁 Повторить</button>'
        )

    column_formatters = {
        SurveyAiAnalysis.status: _status_formatter.__func__,
        SurveyAiAnalysis.error_message: _error_formatter.__func__,
        "ai_actions": _ai_actions_formatter.__func__,
    }

    column_labels = {
        "ai_actions": "Действия",
        SurveyAiAnalysis.status: "Статус",
        SurveyAiAnalysis.overall_priority: "Приоритет",
        SurveyAiAnalysis.attempts: "Попытки",
        SurveyAiAnalysis.error_code: "Код ошибки",
        SurveyAiAnalysis.error_message: "Безопасная ошибка",
    }
