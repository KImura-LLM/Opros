# ============================================
# SQLAdmin Setup - Админ-панель
# ============================================
"""
Настройка административной панели SQLAdmin.
"""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from typing import Optional
from pathlib import Path

from app.core.config import settings
from app.core.database import engine
from app.models import SurveyConfig, SurveySession, SurveyAnswer, AuditLog


class AdminAuth(AuthenticationBackend):
    """
    Аутентификация для админ-панели.
    Простая Basic Auth через Cookie.
    """
    
    async def login(self, request: Request) -> bool:
        """Обработка входа."""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"admin_authenticated": True})
            return True
        return False
    
    async def logout(self, request: Request) -> bool:
        """Обработка выхода."""
        request.session.clear()
        return True
    
    async def authenticate(self, request: Request) -> bool:
        """Проверка аутентификации."""
        return request.session.get("admin_authenticated", False)


class SurveyConfigAdmin(ModelView, model=SurveyConfig):
    """Админ-представление для конфигураций опросника."""
    
    identity = "survey-config"
    name = "Опросник"
    name_plural = "Опросники"
    icon = "fa-solid fa-clipboard-list"
    
    column_list = [
        SurveyConfig.id,
        SurveyConfig.name,
        SurveyConfig.version,
        SurveyConfig.is_active,
        SurveyConfig.created_at,
    ]
    
    column_searchable_list = [SurveyConfig.name]
    column_sortable_list = [SurveyConfig.id, SurveyConfig.name, SurveyConfig.created_at]
    column_default_sort = [("id", True)]
    
    form_columns = [
        SurveyConfig.name,
        SurveyConfig.description,
        SurveyConfig.json_config,
        SurveyConfig.version,
        SurveyConfig.is_active,
    ]
    
    # Отображение JSON в форме
    form_widget_args = {
        "json_config": {"rows": 30},
        "description": {"rows": 3},
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class SurveySessionAdmin(ModelView, model=SurveySession):
    """Админ-представление для сессий опроса."""
    
    identity = "survey-session"
    name = "Сессия"
    name_plural = "Сессии опросов"
    icon = "fa-solid fa-user-clock"
    
    column_list = [
        SurveySession.id,
        SurveySession.lead_id,
        SurveySession.patient_name,
        SurveySession.status,
        SurveySession.consent_given,
        SurveySession.started_at,
        SurveySession.completed_at,
    ]
    
    column_searchable_list = [SurveySession.lead_id, SurveySession.patient_name]
    column_sortable_list = [
        SurveySession.lead_id,
        SurveySession.status,
        SurveySession.started_at,
    ]
    column_default_sort = [("started_at", True)]
    
    column_formatters = {
        SurveySession.status: lambda m, a: {
            "in_progress": "🔄 В процессе",
            "completed": "✅ Завершён",
            "abandoned": "❌ Брошен",
        }.get(m.status, m.status),
    }
    
    # Только просмотр
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


class SurveyAnswerAdmin(ModelView, model=SurveyAnswer):
    """Админ-представление для ответов."""
    
    identity = "survey-answer"
    name = "Ответ"
    name_plural = "Ответы"
    icon = "fa-solid fa-comments"
    
    column_list = [
        SurveyAnswer.id,
        SurveyAnswer.session_id,
        SurveyAnswer.node_id,
        SurveyAnswer.created_at,
    ]
    
    column_searchable_list = [SurveyAnswer.node_id]
    column_sortable_list = [SurveyAnswer.id, SurveyAnswer.created_at]
    column_default_sort = [("id", True)]
    
    # Только просмотр
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True


class AuditLogAdmin(ModelView, model=AuditLog):
    """Админ-представление для логов аудита."""
    
    identity = "audit-log"
    name = "Лог"
    name_plural = "Логи аудита"
    icon = "fa-solid fa-shield-halved"
    
    column_list = [
        AuditLog.id,
        AuditLog.session_id,
        AuditLog.action,
        AuditLog.ip_address,
        AuditLog.timestamp,
    ]
    
    column_searchable_list = [AuditLog.action, AuditLog.ip_address]
    column_sortable_list = [AuditLog.id, AuditLog.timestamp]
    column_default_sort = [("timestamp", True)]
    
    # Только просмотр
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


def setup_admin(app):
    """
    Настройка и подключение админ-панели к приложению.
    
    Args:
        app: FastAPI application
    """
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Опросник - Админ",
        base_url="/admin",
        templates_dir=str(Path(__file__).parent / "templates")
    )
    
    # Регистрация моделей
    admin.add_view(SurveyConfigAdmin)
    admin.add_view(SurveySessionAdmin)
    admin.add_view(SurveyAnswerAdmin)
    admin.add_view(AuditLogAdmin)
