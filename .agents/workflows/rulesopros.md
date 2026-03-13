---
description: Правила и архитектурные принципы проекта Opros для AI-агента
---

You are a Senior Fullstack Developer working on a compliant medical PWA (Progressive Web App).
Follow these patterns to ensure security, performance, and code consistency.

## 💻 Development Workflows

- **Language**: Strictly use **Russian** in all comments, commit messages, and documentation.
- **API validation**: Strict Pydantic models for all inputs/outputs (`schemas.py`).
- **Testing**: Prioritize E2E tests with Playwright over unit tests for UI logic.

## 🚨 MANDATORY: MCP Playwright Usage
**You MUST use the MCP Playwright tools for any task involving:**
1.  **Site Verification**: Checking the live or local deployment for visual regressions, layout issues, and responsiveness.
2.  **E2E Testing**: Verifying complex survey logic branches, navigation flows, and form submissions.
3.  **Error Collection**: Gathering console logs, network errors, and runtime exceptions from the browser context.
**Do NOT guess UI behavior.** Use `mcp_playwright_browser_*` tools to inspect the actual state of the application.

## 🏗 Project Architecture & Tech Stack

### Backend (`/backend`)
- **Framework**: FastAPI (Async) with Pydantic for validation.
- **Database**: PostgreSQL (Async SQLAlchemy) for persistence.
- **Caching/Session**: Redis for session state and temporary answer storage.
- **Migrations**: Alembic (`/backend/alembic`).
- **Scripts**: Maintenance scripts in `/backend/scripts` (e.g., `seed.py`, `cleanup.py`).
- **Entry Point**: `app.main:app`.

### Frontend (`/frontend`)
- **Framework**: React 18, Vite, TypeScript.
- **State Management**: Zustand (`surveyStore.ts`).
- **Styling**: Tailwind CSS (Mobile First), Framer Motion.
- **Features**:
    - **Survey Runner**: Renders questions based on JSON.
    - **Survey Editor**: Visual editor for the JSON structure (`/frontend/src/editor`).

### Infrastructure
- **Docker**: `docker-compose.yml` (dev) and `docker-compose.prod.yml` (prod).
- **Reverse Proxy**: Nginx (`/nginx/conf.d/default.conf`).
- **Deployment**: Automatic deploy via SSH (see `INFO/DEPLOY_GUIDE.md`).

## 🧠 Critical Concepts

1.  **JSON-Driven UI (Survey Engine)**:
    - The core logic is defined in `backend/data/survey_structure.json` (or `_v2.json` for current iterations).
    - The frontend receives a JSON graph; **never hardcode questions in React**.
    - Changes to survey logic must happen in the JSON file or via the Editor.

2.  **Privacy & Security (152-FZ)**:
    - **Zero PII in LocalStorage**: Patient data lives in RAM (Zustand) or backend Redis session.
    - **Magic Link Auth**: Secure access via URL tokens (no passwords).
    - **Session Expiry**: Strict session timeouts handled by Redis and backend scripts (`auto_expire_sessions.py`).

3.  **Data Flow**:
    - `POST /api/v1/survey/start` -> Init session in Redis.
    - `POST /api/v1/survey/answer` -> Validate, Compute Next Node, Update Redis.
    - **Bitrix24 Webhook**: Final results sent to CRM upon completion (`services/bitrix24.py`).



## ❌ Anti-Patterns

- **No Hardcoded Logic**: Do not write `if (questionId === 'q5')` in components. Use the JSON `logic` rules.
- **No Client-Side Persistence**: Never use `localStorage` for sensitive medical data.
- **No Complex UI**: Keep interfaces accessible for elderly users (large buttons, clear contrast).

## 📂 Key Files Reference

- **Schema**: `backend/data/survey_structure.json`
- **Frontend State**: `frontend/src/store/surveyStore.ts`
- **Backend Engine**: `backend/app/services/survey_engine.py`
- **API Router**: `backend/app/api/v1/router.py`
- **Bitrix Service**: `backend/app/services/bitrix24.py`
- **Documentation**: `INFO/` folder (Deploy, Logs, Server Info).

---

## 🛠 Доступные инструменты агента

### 🌐 MCP Playwright (браузерное управление)
Используй для проверки UI, E2E-тестирования и сбора ошибок из консоли браузера.

| Инструмент | Назначение |
|---|---|
| `playwright-browser_navigate` | Перейти на URL |
| `playwright-browser_snapshot` | Получить снимок доступности страницы (предпочтительнее скриншота для действий) |
| `playwright-browser_take_screenshot` | Сделать скриншот страницы или элемента |
| `playwright-browser_click` | Кликнуть по элементу |
| `playwright-browser_type` | Ввести текст в поле |
| `playwright-browser_fill_form` | Заполнить несколько полей формы сразу |
| `playwright-browser_select_option` | Выбрать значение в выпадающем списке |
| `playwright-browser_hover` | Навести курсор на элемент |
| `playwright-browser_drag` | Перетащить элемент |
| `playwright-browser_press_key` | Нажать клавишу |
| `playwright-browser_evaluate` | Выполнить JavaScript на странице |
| `playwright-browser_console_messages` | Получить сообщения из консоли браузера |
| `playwright-browser_network_requests` | Получить список сетевых запросов |
| `playwright-browser_handle_dialog` | Обработать диалоговое окно (alert/confirm/prompt) |
| `playwright-browser_file_upload` | Загрузить файл |
| `playwright-browser_wait_for` | Ждать появления/исчезновения текста или паузу |
| `playwright-browser_resize` | Изменить размер окна браузера |
| `playwright-browser_tabs` | Управление вкладками (список, создание, закрытие, переключение) |
| `playwright-browser_navigate_back` | Вернуться на предыдущую страницу |
| `playwright-browser_close` | Закрыть страницу |
| `playwright-browser_install` | Установить браузер |

### 🐙 GitHub MCP (управление репозиторием)
Используй для работы с Issues, Pull Requests, Actions, кодом и релизами.

| Инструмент | Назначение |
|---|---|
| `github-mcp-server-get_file_contents` | Получить содержимое файла или директории |
| `github-mcp-server-search_code` | Поиск кода по всем репозиториям GitHub |
| `github-mcp-server-get_commit` | Получить детали коммита |
| `github-mcp-server-list_commits` | Список коммитов ветки |
| `github-mcp-server-list_branches` | Список веток репозитория |
| `github-mcp-server-list_tags` / `get_tag` | Работа с тегами |
| `github-mcp-server-issue_read` | Чтение issue (детали, комментарии, метки, суб-задачи) |
| `github-mcp-server-list_issues` / `search_issues` | Список и поиск issues |
| `github-mcp-server-pull_request_read` | Чтение PR (детали, diff, файлы, ревью, статус) |
| `github-mcp-server-list_pull_requests` / `search_pull_requests` | Список и поиск PR |
| `github-mcp-server-actions_get` / `actions_list` | Работа с GitHub Actions (воркфлоу, запуски, артефакты) |
| `github-mcp-server-get_job_logs` | Получить логи заданий CI/CD |
| `github-mcp-server-list_releases` / `get_latest_release` / `get_release_by_tag` | Работа с релизами |
| `github-mcp-server-list_code_scanning_alerts` / `get_code_scanning_alert` | Алерты сканирования кода |
| `github-mcp-server-list_secret_scanning_alerts` / `get_secret_scanning_alert` | Алерты утечки секретов |
| `github-mcp-server-search_repositories` / `search_users` | Поиск репозиториев и пользователей |
| `github-mcp-server-get_label` / `list_issue_types` | Метки и типы задач |

### 💻 Файловая система и код

| Инструмент | Назначение |
|---|---|
| `bash` | Выполнение shell-команд (сборка, тесты, git, установка пакетов) |
| `view` | Просмотр файла или директории с номерами строк |
| `create` | Создание нового файла |
| `edit` | Точечное редактирование строк файла |
| `grep` | Поиск паттернов в содержимом файлов (ripgrep) |
| `glob` | Поиск файлов по шаблону имени |
| `web_fetch` | Загрузка веб-страницы (markdown или HTML) |
| `store_memory` | Сохранение факта о кодовой базе для будущих сессий |

### 🔒 Безопасность

| Инструмент | Назначение |
|---|---|
| `gh-advisory-database` | Проверка зависимостей на CVE-уязвимости (npm, pip, go и др.) |
| `codeql_checker` | Статический анализ кода на уязвимости (CodeQL) |
| `code_review` | Автоматическое ревью изменений перед финализацией |

### 🤖 Вспомогательные агенты (Sub-agents)

Запускаются через инструмент `task`. Каждый агент работает независимо.

| Агент | Назначение |
|---|---|
| `explore` | Быстрое исследование кодовой базы, ответы на вопросы о коде (модель Haiku) |
| `task` | Выполнение команд (сборка, тесты, линтинг) с кратким выводом результата (модель Haiku) |
| `general-purpose` | Сложные многошаговые задачи с полным набором инструментов (модель Sonnet) |

### 📋 Управление задачей

| Инструмент | Назначение |
|---|---|
| `report_progress` | Зафиксировать прогресс: коммит + пуш изменений в PR, обновление чеклиста |
| `search_code_subagent` | Семантический поиск кода по естественному запросу |