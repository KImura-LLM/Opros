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
from loguru import logger

from app.core.config import settings
from app.core.database import engine
from app.models import SurveyConfig, SurveySession, SurveyAnswer, AuditLog


class AdminAuth(AuthenticationBackend):
    """
    Аутентификация для админ-панели.
    Простая Basic Auth через Cookie.
    """
    
    def __init__(self, secret_key: str) -> None:
        """
        Инициализация без дублирующего SessionMiddleware.
        Сессии управляются единым SessionMiddleware, подключённым в main.py.
        Без этого переопределения AuthenticationBackend добавляет свой
        SessionMiddleware к под-приложению SQLAdmin, что создаёт конфликт
        двух сессионных cookie и приводит к потере данных аутентификации.
        """
        self.secret_key = secret_key
        self.middlewares = []
    
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

    column_details_list = [
        SurveyConfig.id,
        SurveyConfig.name,
        SurveyConfig.version,
        SurveyConfig.description,
        SurveyConfig.is_active,
        SurveyConfig.json_config,
        SurveyConfig.created_at,
        SurveyConfig.updated_at,
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
    
    # Добавляем кастомное поле для кнопки редактора
    column_list = [
        SurveyConfig.id,
        SurveyConfig.name,
        SurveyConfig.version,
        SurveyConfig.is_active,
        SurveyConfig.created_at,
        "edit_link",  # Кастомная колонка для кнопки редактора
        "analysis_link",  # Кастомная колонка для кнопки системного анализа
    ]
    
    # Форматтер для списка
    @staticmethod
    def _edit_link_formatter(model, prop):
        """Рендеринг кнопки визуального редактора."""
        from markupsafe import Markup
        # Используем FRONTEND_URL из настроек
        editor_url = f"{settings.FRONTEND_URL}/editor/{model.id}"
        
        return Markup(f'''
            <a href="{editor_url}" 
               target="_blank"
               style="
                   display: inline-flex;
                   align-items: center;
                   gap: 6px;
                   padding: 6px 12px;
                   background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                   color: white;
                   border-radius: 6px;
                   font-size: 12px;
                   font-weight: 500;
                   text-decoration: none;
                   transition: all 0.2s;
                   box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
               "
               onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 8px rgba(59, 130, 246, 0.4)';"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(59, 130, 246, 0.3)';"
            >
                <i class="fa-solid fa-diagram-project"></i>
                Визуальный редактор
            </a>
        ''')
    
    @staticmethod
    def _analysis_link_formatter(model, prop):
        """Рендеринг кнопки редактора системного анализа."""
        from markupsafe import Markup
        analysis_url = f"{settings.FRONTEND_URL}/analysis-editor/{model.id}"
        
        return Markup(f'''
            <a href="{analysis_url}" 
               target="_blank"
               style="
                   display: inline-flex;
                   align-items: center;
                   gap: 6px;
                   padding: 6px 12px;
                   background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                   color: white;
                   border-radius: 6px;
                   font-size: 12px;
                   font-weight: 500;
                   text-decoration: none;
                   transition: all 0.2s;
                   box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
               "
               onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 8px rgba(245, 158, 11, 0.4)';"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(245, 158, 11, 0.3)';"
            >
                <i class="fa-solid fa-stethoscope"></i>
                Системный анализ
            </a>
        ''')
    
    column_formatters = {
        "edit_link": _edit_link_formatter.__func__,
        "analysis_link": _analysis_link_formatter.__func__,
    }
    
    column_labels = {
        "edit_link": "Визуальный редактор",
        "analysis_link": "Системный анализ",
    }


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
        "report_actions",  # Кастомная колонка для кнопок
    ]
    
    column_searchable_list = [SurveySession.lead_id, SurveySession.patient_name]
    column_sortable_list = [
        SurveySession.lead_id,
        SurveySession.status,
        SurveySession.started_at,
    ]
    column_default_sort = [("started_at", True)]
    
    # Форматтер для кнопок экспорта
    @staticmethod
    def _report_actions_formatter(model, prop):
        """Рендеринг кнопок экспорта отчёта и индикатора статуса снимка."""
        from markupsafe import Markup

        # Показываем кнопки только для завершённых сессий
        if model.status != "completed":
            return Markup('<span style="color: #94a3b8; font-size: 12px;">Сессия не завершена</span>')

        base_url = f"/api/v1/reports/{model.id}"

        # ── Индикатор состояния снимка отчёта ──
        if model.report_snapshot:
            generated_at = model.report_snapshot.get("generated_at", "")
            config_ver = model.report_snapshot.get("config_version", "?")
            is_regen = model.report_snapshot.get("regenerated", False)
            if generated_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    date_str = generated_at[:16]
            else:
                date_str = "—"

            if is_regen:
                badge = (
                    f'<span style="display:inline-flex;align-items:center;gap:4px;'
                    f'padding:3px 8px;background:#fef3c7;color:#92400e;border:1px solid #fcd34d;'
                    f'border-radius:10px;font-size:10px;font-weight:600;" '
                    f'title="Отчёт обновлён администратором {date_str} (версия конфига {config_ver})">'
                    f'🔄 Обновлён {date_str}</span>'
                )
            else:
                badge = (
                    f'<span style="display:inline-flex;align-items:center;gap:4px;'
                    f'padding:3px 8px;background:#ecfdf5;color:#065f46;border:1px solid #6ee7b7;'
                    f'border-radius:10px;font-size:10px;font-weight:600;" '
                    f'title="Снимок отчёта сохранён {date_str} (версия конфига {config_ver})">'
                    f'🔒 Снимок {date_str}</span>'
                )
        else:
            badge = (
                '<span style="display:inline-flex;align-items:center;gap:4px;'
                'padding:3px 8px;background:#fef2f2;color:#991b1b;border:1px solid #fca5a5;'
                'border-radius:10px;font-size:10px;font-weight:600;" '
                'title="Снимок не сохранён — отчёт генерируется из текущей конфигурации">⚡ Нет снимка</span>'
            )

        # ── Кнопка «Обновить отчёт» (принудительная перегенерация) ──
        sid = str(model.id)
        # JS строится отдельно — без вложенных f-строк с экранированными фигурными скобками,
        # чтобы избежать ошибок синтаксиса при конкатенации Python/JS
        _js = (
            "(function(btn){"
            "if(!confirm('Пересчитать отчёт по текущей версии опросника?\\nСтарый снимок будет заменён.'))return;"
            "btn.disabled=true;btn.textContent='⏳ Обновление...';"
            f"fetch('/api/v1/reports/{sid}/regenerate',"
            "{method:'POST',credentials:'include'})"
            ".then(function(r){return r.json();})"
            ".then(function(d){"
            "if(d.success){"
            "btn.textContent='✅ Обновлено!';"
            "btn.style.background='linear-gradient(135deg,#059669 0%,#047857 100%)';"
            "setTimeout(function(){location.reload();},1200);"
            "}else{"
            "alert('Ошибка: '+(d.detail||'неизвестная ошибка'));"
            "btn.disabled=false;btn.textContent='🔄 Обновить отчёт';"
            "}}).catch(function(){"
            "alert('Ошибка запроса к серверу');"
            "btn.disabled=false;btn.textContent='🔄 Обновить отчёт';"
            "})})(this)"
        )
        refresh_btn = (
            f'<button onclick="{_js}"'
            ' style="display:inline-flex;align-items:center;gap:4px;'
            'padding:5px 10px;'
            'background:linear-gradient(135deg,#7c3aed 0%,#6d28d9 100%);'
            'color:white;border:none;border-radius:4px;'
            'font-size:11px;font-weight:500;cursor:pointer;'
            'box-shadow:0 1px 3px rgba(124,58,237,0.3);transition:all 0.2s;"'
            " onmouseover=\"this.style.transform='translateY(-1px)';this.style.boxShadow='0 3px 6px rgba(124,58,237,0.45)';\""
            " onmouseout=\"this.style.transform='translateY(0)';this.style.boxShadow='0 1px 3px rgba(124,58,237,0.3)';\""
            ' title="Пересчитать отчёт с текущей версией опросника (заменит сохранённый снимок)">'
            '🔄 Обновить отчёт'
            '</button>'
        )

        return Markup(f'''
            <div style="display: flex; flex-direction: column; gap: 6px; min-width: 220px;">
                <div>{badge}</div>
                <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                    <a href="{base_url}/preview"
                       target="_blank"
                       style="
                           display: inline-flex; align-items: center; gap: 4px;
                           padding: 5px 10px;
                           background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                           color: white; border-radius: 4px; font-size: 11px; font-weight: 500;
                           text-decoration: none; transition: all 0.2s;
                           box-shadow: 0 1px 3px rgba(59, 130, 246, 0.3);"
                       onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(59, 130, 246, 0.4)';"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(59, 130, 246, 0.3)';"
                       title="Открыть предпросмотр отчёта">
                        <i class="fa-solid fa-eye"></i> Просмотр
                    </a>
                    <a href="{base_url}/export/pdf"
                       download
                       style="
                           display: inline-flex; align-items: center; gap: 4px;
                           padding: 5px 10px;
                           background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                           color: white; border-radius: 4px; font-size: 11px; font-weight: 500;
                           text-decoration: none; transition: all 0.2s;
                           box-shadow: 0 1px 3px rgba(220, 38, 38, 0.3);"
                       onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(220, 38, 38, 0.4)';"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(220, 38, 38, 0.3)';"
                       title="Скачать отчёт в формате PDF">
                        <i class="fa-solid fa-file-pdf"></i> PDF
                    </a>
                    <a href="{base_url}/export/txt"
                       download
                       style="
                           display: inline-flex; align-items: center; gap: 4px;
                           padding: 5px 10px;
                           background: linear-gradient(135deg, #059669 0%, #047857 100%);
                           color: white; border-radius: 4px; font-size: 11px; font-weight: 500;
                           text-decoration: none; transition: all 0.2s;
                           box-shadow: 0 1px 3px rgba(5, 150, 105, 0.3);"
                       onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(5, 150, 105, 0.4)';"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(5, 150, 105, 0.3)';"
                       title="Скачать отчёт в текстовом формате">
                        <i class="fa-solid fa-file-lines"></i> TXT
                    </a>
                    {refresh_btn}
                </div>
            </div>
        ''')
    
    column_formatters = {
        SurveySession.status: lambda m, a: {
            "in_progress": "🔄 В процессе",
            "completed": "✅ Завершён",
            "abandoned": "❌ Брошен",
        }.get(m.status, m.status),
        "report_actions": _report_actions_formatter.__func__,
    }
    
    # Добавляем предпросмотр в детали
    column_details_list = [
        SurveySession.id,
        SurveySession.lead_id,
        SurveySession.patient_name,
        SurveySession.status,
        SurveySession.consent_given,
        SurveySession.started_at,
        SurveySession.completed_at,
        "report_preview",  # Кастомное поле для предпросмотра
    ]
    
    # Форматтер для предпросмотра в деталях
    @staticmethod
    def _report_preview_formatter(model, prop):
        """Рендеринг встроенного предпросмотра отчёта."""
        from markupsafe import Markup
        
        if model.status != "completed":
            return Markup('<div style="padding: 20px; background: #fef2f2; border-radius: 8px; color: #991b1b;"><p>Предпросмотр отчёта доступен только для завершённых сессий.</p></div>')
        
        preview_url = f"/api/v1/reports/{model.id}/preview"
        
        return Markup(f'''
            <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #1e293b; font-size: 18px;">📋 Предпросмотр отчёта</h3>
                    <a href="{preview_url}" 
                       target="_blank"
                       style="
                           display: inline-flex;
                           align-items: center;
                           gap: 6px;
                           padding: 8px 16px;
                           background: #3b82f6;
                           color: white;
                           border-radius: 6px;
                           font-size: 13px;
                           font-weight: 500;
                           text-decoration: none;
                       "
                    >
                        <i class="fa-solid fa-external-link-alt"></i>
                        Открыть в новом окне
                    </a>
                </div>
                <iframe 
                    src="{preview_url}" 
                    style="
                        width: 100%; 
                        height: 800px; 
                        border: 2px solid #cbd5e1; 
                        border-radius: 6px;
                        background: white;
                    "
                    frameborder="0"
                ></iframe>
            </div>
        ''')
    
    column_formatters_detail = {
        "report_preview": _report_preview_formatter.__func__,
    }
    
    column_labels = {
        "report_actions": "Отчёты",
        "report_preview": "Отчёт",
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
    from fastapi import Request
    from fastapi.responses import HTMLResponse
    from starlette.templating import Jinja2Templates as _Jinja2Templates

    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    
    templates_dir = str(Path(__file__).parent / "templates")

    # --- Кастомная страница аналитики ---
    # ВАЖНО: регистрируем ДО создания Admin(), иначе SQLAdmin перехватит /admin/*
    _analytics_tpl = _Jinja2Templates(directory=templates_dir)

    @app.get("/admin/analytics", response_class=HTMLResponse, include_in_schema=False)
    async def admin_analytics_page(request: Request):
        """Страница дашборда аналитики в админ-панели."""
        if not request.session.get("admin_authenticated"):
            from starlette.responses import RedirectResponse as RR
            return RR(url="/admin/login", status_code=302)

        # Создаём минимальный объект admin для совместимости с layout.html
        class AdminStub:
            title = "Опросник - Админ"
        
        return _analytics_tpl.TemplateResponse(
            "analytics.html",
            {"request": request, "admin": AdminStub()},
        )
    
    @app.get("/admin/logs", response_class=HTMLResponse, include_in_schema=False)
    async def admin_logs_page(request: Request):
        """Страница просмотра логов системы."""
        if not request.session.get("admin_authenticated"):
            from starlette.responses import RedirectResponse as RR
            return RR(url="/admin/login", status_code=302)

        class AdminStub:
            title = "Опросник - Админ"
        
        return _analytics_tpl.TemplateResponse(
            "logs.html",
            {"request": request, "admin": AdminStub()},
        )
    
    @app.get("/admin/api/session", include_in_schema=False)
    async def admin_api_session(request: Request):
        """Проверка статуса сессии администратора. Используется фронтендом (EditorPage)."""
        from fastapi.responses import JSONResponse
        if request.session.get("admin_authenticated", False):
            return JSONResponse({"authenticated": True})
        return JSONResponse({"authenticated": False}, status_code=401)

    @app.post("/admin/login", include_in_schema=False)
    async def admin_login_with_next(request: Request):
        """
        Кастомный обработчик логина с поддержкой редиректа обратно в редактор.
        Читает URL возврата из cookie `admin_redirect` (т.к. форма SQLAdmin не передаёт query params).
        Регистрируется ДО создания Admin(), чтобы перехватить стандартный хендлер SQLAdmin.
        """
        from starlette.responses import RedirectResponse as RR
        from starlette.responses import Response

        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Читаем URL возврата из cookie (устанавливается фронтендом перед редиректом на логин)
        redirect_cookie = request.cookies.get("admin_redirect", "").strip()

        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"admin_authenticated": True})
            # Редирект только на внутренние страницы в целях безопасности
            redirect_to = redirect_cookie if (redirect_cookie and redirect_cookie.startswith("/")) else "/admin/"
            logger.info(f"Администратор вошёл в систему, редирект: {redirect_to}")
            response = RR(url=redirect_to, status_code=303)
            # Удаляем cookie после использования
            response.delete_cookie("admin_redirect", path="/")
            return response

        logger.warning("Неудачная попытка входа в админ-панель")
        return RR(url="/admin/login", status_code=302)

    @app.get("/admin/api/logs", include_in_schema=False)
    async def admin_api_logs(
        request: Request,
        level: str = "",
        source: str = "",
        lines: int = 100
    ):
        """API endpoint для получения логов из файла."""
        from fastapi.responses import JSONResponse
        import re
        import os
        
        if not request.session.get("admin_authenticated"):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        try:
            # Путь к файлу логов
            log_path = os.path.join(os.getcwd(), "logs", "app.log")
            
            log_lines = []
            if os.path.exists(log_path):
                # Читаем последние строки файла
                # Для оптимизации при больших файлах можно использовать seek,
                # но с ротацией 10МБ readlines() вполне приемлем
                with open(log_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                    # Берем последние N строк + запас для фильтрации
                    start_idx = max(0, len(all_lines) - lines * 2) 
                    log_lines = all_lines[start_idx:]
            else:
                # Если файла нет, возвращаем пустой список (возможно первый запуск)
                return JSONResponse({"logs": []})
            
            # Парсинг логов
            logs = []
            
            # Паттерн для парсинга логов loguru
            # Пример: 2026-02-17 12:34:56 | INFO     | app.services.bitrix24:send_comment:101 - Отправка комментария
            pattern = re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*'
                r'(?P<level>\w+)\s*\|\s*'
                r'(?P<source>[^:]+:[^:]+:[^\s]+)\s*-\s*'
                r'(?P<message>.*)'
            )
            
            for line in log_lines:
                if not line.strip():
                    continue
                
                match = pattern.search(line)
                if match:
                    log_data = match.groupdict()
                    
                    # Фильтрация по уровню
                    if level and log_data['level'].strip() != level:
                        continue
                    
                    # Фильтрация по источнику
                    if source and source not in log_data['source']:
                         continue
                         
                    logs.append({
                        "timestamp": log_data['timestamp'],
                        "level": log_data['level'].strip(),
                        "source": log_data['source'].strip(),
                        "message": log_data['message'].strip()
                    })
            
            # Возвращаем последние N отфильтрованных логов
            return JSONResponse({"logs": logs[-lines:]})
            
        except Exception as e:
            return JSONResponse({
                "error": "Failed to fetch logs",
                "details": str(e)
            }, status_code=500)


    # --- Ручной запуск очистки истёкших сессий (только для авторизованных) ---
    @app.post("/admin/cleanup-sessions", include_in_schema=False)
    async def admin_cleanup_sessions(request: Request):
        """Ручная принудительная очистка истёкших и зависших сессий."""
        from fastapi.responses import JSONResponse
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import update
        from app.core.database import async_session_maker
        from app.models import SurveySession

        if not request.session.get("admin_authenticated"):
            return JSONResponse({"error": "Не авторизован"}, status_code=403)

        now = datetime.now(timezone.utc)
        # Граница "зависших" без expires_at — старше 3 часов
        stale_threshold = now - timedelta(hours=3)

        async with async_session_maker() as db:
            # 1. Закрываем сессии с истёкшим expires_at
            res1 = await db.execute(
                update(SurveySession)
                .where(
                    SurveySession.status == "in_progress",
                    SurveySession.expires_at.isnot(None),
                    SurveySession.expires_at < now,
                )
                .values(status="abandoned", completed_at=now)
            )
            # 2. Закрываем сессии без expires_at, старше 3 часов
            res2 = await db.execute(
                update(SurveySession)
                .where(
                    SurveySession.status == "in_progress",
                    SurveySession.expires_at.is_(None),
                    SurveySession.started_at < stale_threshold,
                )
                .values(status="abandoned", completed_at=now)
            )
            await db.commit()

        count = res1.rowcount + res2.rowcount
        logger.info(f"Ручная очистка: завершено {count} истёкших/зависших сессий")
        return JSONResponse({"success": True, "closed": count, "timestamp": now.isoformat()})

    # --- Инициализация SQLAdmin ---
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Опросник - Админ",
        base_url="/admin",
        templates_dir=templates_dir
    )
    
    # Регистрация моделей
    admin.add_view(SurveyConfigAdmin)
    admin.add_view(SurveySessionAdmin)
    admin.add_view(SurveyAnswerAdmin)
    admin.add_view(AuditLogAdmin)
