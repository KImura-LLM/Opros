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
        "visual_structure",  # Кастомное поле
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
    ]
    
    # Форматтер для списка
    @staticmethod
    def _edit_link_formatter(model, prop):
        """Рендеринг кнопки редактора."""
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
                Редактор
            </a>
        ''')
    
    column_formatters = {
        "edit_link": _edit_link_formatter.__func__,
    }
    
    column_labels = {
        "edit_link": "Визуальный редактор",
    }

    def visual_structure(model, prop):
        """Рендеринг визуальной структуры опросника."""
        from markupsafe import Markup
        import re
        
        config = model.json_config
        nodes = {n['id']: n for n in config.get('nodes', [])}
        start = config.get('start_node')
        
        # Helper to find option text by value
        def get_option_text(node, value):
            if not node or not node.get('options'): return value
            val_str = str(value).replace("'", "").strip()
            for opt in node['options']:
                if str(opt.get('value')) == val_str:
                    return opt.get('text')
            return value

        # Helper to parse condition
        def pretty_condition(cond, parent_node):
            if not cond: return ""
            # Try to extract value from "selected == 'val'"
            match = re.search(r"selected\s*==\s*'([^']+)'", cond)
            if match:
                val = match.group(1)
                return get_option_text(parent_node, val)
            
            match_in = re.search(r"selected\s+contains\s+'([^']+)'", cond)
            if match_in:
                val = match_in.group(1)
                text = get_option_text(parent_node, val)
                return f"Содержит: {text}"
                
            return cond.replace("selected", "Выбор").replace("==", "=").replace("'", "")

        html = ['<div style="font-family: \'Segoe UI\', Roboto, sans-serif; line-height: 1.6; font-size: 16px; background: #fff; padding: 25px; border-radius: 8px; border: 1px solid #e2e8f0; color: #333;">']
        html.append(f'<h3 style="margin-top:0; margin-bottom:20px; font-size: 1.6em; color:#1e293b; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px;">{model.name} <span style="font-weight:normal; font-size:0.7em; color:#94a3b8">v{model.version}</span></h3>')

        STYLES = {
            'question': 'font-weight: 600; font-size: 1.25em; color: #1e293b; margin-bottom: 6px;',
            'description': 'font-size: 0.95em; color: #64748b; margin-bottom: 10px; font-style: italic;',
            'options': 'margin-left: 0; color: #475569; font-size: 1em; display: grid; gap: 4px;',
            'option-item': 'display: flex; align-items: center; gap: 8px;',
            'option-bullet': 'width: 6px; height: 6px; border-radius: 50%; background: #94a3b8;',
            
            'logic-container': 'margin-left: 14px; padding-left: 24px; border-left: 3px solid #cbd5e1; margin-top: 15px;',
            'branch': 'margin-top: 15px;',
            'arrow-line': 'color: #94a3b8; font-weight: bold; font-size: 1.2em; display: inline-block;',
            'arrow-label': 'background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-size: 0.9em; color: #334155; display: inline-block; margin-bottom: 8px; font-weight: 500; border: 1px solid #e2e8f0;',
            
            'final': 'display: inline-block; padding: 6px 16px; border-radius: 6px; background: #dcfce7; color: #166534; font-weight: 600; border: 1px solid #bbf7d0; font-size: 0.9em;',
            'loop': 'color: #d97706; font-style: italic; background: #fffbeb; padding: 4px 10px; border-radius: 6px; border: 1px solid #fde68a;',
            'node-box': 'background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 12px;'
        }

        # Icons map (purely decoration)
        ICONS = {
            'info_screen': 'ℹ️',
            'consent_screen': '✅',
            'is_final': '🏁'
        }

        def render_node_recursive(node_id, visited, depth=0):
            if depth > 50: return '<div style="color:red">...</div>'
            
            node = nodes.get(node_id)
            if not node: return ''

            # Container
            out = f'<div style="{STYLES["node-box"]}">'
            
            # Question
            icon = ICONS.get(node.get('type'), '')
            title = node.get('question_text', 'Без вопроса')
            out += f'<div style="{STYLES["question"]}">{title}</div>'
            
            # Description
            if node.get('description'):
                 out += f'<div style="{STYLES["description"]}">{node.get("description")}</div>'
            
            # Options (only if not branching immediately by them, but usually good to show)
            if node.get('options'):
                out += f'<div style="{STYLES["options"]}">'
                for opt in node['options']:
                     out += f'<div style="{STYLES["option-item"]}"><div style="{STYLES["option-bullet"]}"></div>{opt.get("text")}</div>'
                out += '</div>'

            # End of node content
            out += '</div>'

            # Logic / Children
            
            # Check for Final or Loop
            if node.get('is_final'):
                 out += f'<div style="margin-left: 20px; margin-bottom: 20px;"><span style="{STYLES["final"]}">🏁 Завершение опроса</span></div>'
                 return out
            
            if node_id in visited:
                 out += f'<div style="margin-left: 20px; margin-bottom: 10px;"><span style="{STYLES["loop"]}">⟳ Возврат к вопросу "{title}"</span></div>'
                 return out

            new_visited = visited | {node_id}
            logic = node.get('logic', [])
            
            if logic:
                out += f'<div style="{STYLES["logic-container"]}">'
                
                # Группировка правил по следующему узлу (next_node)
                grouped_logic = {} # {next_node: [rules]}
                # Важно сохранить порядок появления групп, чтобы визуализация соответствовала логике
                ordered_next_nodes = [] 
                
                for rule in logic:
                    nn = rule.get('next_node')
                    if nn not in grouped_logic:
                        grouped_logic[nn] = []
                        ordered_next_nodes.append(nn)
                    grouped_logic[nn].append(rule)

                for next_node in ordered_next_nodes:
                    rules = grouped_logic[next_node]
                    
                    # Формируем объединенную подпись
                    labels = []
                    has_default = False
                    
                    for rule in rules:
                        is_default = rule.get('default', False)
                        cond = rule.get('condition')
                        
                        if is_default:
                            has_default = True
                        else:
                            labels.append(pretty_condition(cond, node))
                    
                    if has_default:
                        # Если это единственное правило и оно default - просто "Далее"
                        # Если есть другие условия, ведущие сюда, но есть и default - "В остальных случаях"
                        if len(rules) == 1 and len(logic) == 1:
                            labels.append("Далее")
                        else:
                            labels.append("В остальных случаях")
                    
                    # Объединяем метки
                    if not labels: labels = ["Далее"] 
                    combined_label = " <span style='opacity:0.6'>или</span> ".join(labels)

                    out += f'<div style="{STYLES["branch"]}">'
                    # Стрелка с подписью
                    out += f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;"><span style="{STYLES["arrow-line"]}">↳</span> <span style="{STYLES["arrow-label"]}">{combined_label}</span></div>'
                    out += render_node_recursive(next_node, new_visited, depth + 1)
                    out += '</div>'

                out += '</div>'
            
            return out

        if start:
            html.append(render_node_recursive(start, set()))
        else:
            html.append('<div style="color:red">Start node not defined</div>')
        
        html.append('</div>')
        return Markup("".join(html))
    
    # Регистрируем форматтер для деталей
    column_formatters_detail = {
        "visual_structure": visual_structure
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
        """Рендеринг кнопок экспорта отчёта."""
        from markupsafe import Markup
        
        # Показываем кнопки только для завершённых сессий
        if model.status != "completed":
            return Markup('<span style="color: #94a3b8; font-size: 12px;">Сессия не завершена</span>')
        
        # Используем BACKEND_URL из настроек или локальный адрес
        base_url = f"/api/v1/reports/{model.id}"
        
        return Markup(f'''
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                <a href="{base_url}/preview" 
                   target="_blank"
                   style="
                       display: inline-flex;
                       align-items: center;
                       gap: 4px;
                       padding: 5px 10px;
                       background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                       color: white;
                       border-radius: 4px;
                       font-size: 11px;
                       font-weight: 500;
                       text-decoration: none;
                       transition: all 0.2s;
                       box-shadow: 0 1px 3px rgba(59, 130, 246, 0.3);
                   "
                   onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(59, 130, 246, 0.4)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(59, 130, 246, 0.3)';"
                   title="Открыть предпросмотр отчёта"
                >
                    <i class="fa-solid fa-eye"></i>
                    Просмотр
                </a>
                
                <a href="{base_url}/export/pdf" 
                   download
                   style="
                       display: inline-flex;
                       align-items: center;
                       gap: 4px;
                       padding: 5px 10px;
                       background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                       color: white;
                       border-radius: 4px;
                       font-size: 11px;
                       font-weight: 500;
                       text-decoration: none;
                       transition: all 0.2s;
                       box-shadow: 0 1px 3px rgba(220, 38, 38, 0.3);
                   "
                   onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(220, 38, 38, 0.4)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(220, 38, 38, 0.3)';"
                   title="Скачать отчёт в формате PDF"
                >
                    <i class="fa-solid fa-file-pdf"></i>
                    PDF
                </a>
                
                <a href="{base_url}/export/txt" 
                   download
                   style="
                       display: inline-flex;
                       align-items: center;
                       gap: 4px;
                       padding: 5px 10px;
                       background: linear-gradient(135deg, #059669 0%, #047857 100%);
                       color: white;
                       border-radius: 4px;
                       font-size: 11px;
                       font-weight: 500;
                       text-decoration: none;
                       transition: all 0.2s;
                       box-shadow: 0 1px 3px rgba(5, 150, 105, 0.3);
                   "
                   onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 3px 6px rgba(5, 150, 105, 0.4)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(5, 150, 105, 0.3)';"
                   title="Скачать отчёт в текстовом формате"
                >
                    <i class="fa-solid fa-file-lines"></i>
                    TXT
                </a>
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
