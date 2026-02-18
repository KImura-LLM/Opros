---
applyTo: '**'
---
# Copilot Instructions for Opros Project

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