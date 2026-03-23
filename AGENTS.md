# AGENTS.md

## Project Identity

This repository is a production medical survey platform called **Opros**.
It is a PWA used for pre-visit patient intake, symptom collection, report generation, and Bitrix24 CRM integration.

The project handles medically sensitive and personally identifiable data.
Treat all changes as potentially high impact.

## Primary Goals

- Keep production stable.
- Preserve patient-data safety and privacy.
- Keep survey logic JSON-driven.
- Deploy changes only through Git-based workflow.
- Verify the live system after each deployment.

## Required Communication Rules

- Use **Russian** in user-facing explanations unless the user explicitly asks for another language.
- Keep code and infra decisions conservative.
- Before any deployment, explain what will be changed and what will be verified.
- After deployment, always report what was checked, what passed, and any remaining risks.

## Repository Map

### Backend

- `backend/app/main.py`
  Entry point for FastAPI, docs endpoints, middleware, session setup, health endpoint.
- `backend/app/api/v1/endpoints/`
  Main API endpoints:
  - `auth.py`
  - `survey.py`
  - `survey_editor.py`
  - `reports.py`
  - `analytics.py`
  - `bitrix_webhook.py`
- `backend/app/services/`
  Core business logic:
  - `survey_engine.py` is the survey execution engine.
  - `report_generator.py` builds HTML/TXT/PDF reports.
  - `bitrix24.py` handles CRM integration.
- `backend/app/core/`
  Config, DB, Redis, middleware, shared infra code.
- `backend/app/admin/`
  SQLAdmin setup and admin templates.
- `backend/data/`
  JSON-based survey definitions such as `survey_structure.json` and `survey_structure_v2.json`.
- `backend/alembic/`
  Database migrations.

### Frontend

- `frontend/src/pages/`
  Main application pages.
- `frontend/src/components/`
  Survey UI and layout building blocks.
- `frontend/src/store/surveyStore.ts`
  Critical Zustand store for survey state.
- `frontend/src/api/surveyApi.ts`
  Frontend API client.
- `frontend/src/editor/`
  Visual survey editor.
- `frontend/vite.config.ts`
  Important SPA routing and denylist behavior for `/api`, `/admin`, `/docs`, `/redoc`, `/health`.

### Infrastructure

- `docker-compose.yml`
  Development stack.
- `docker-compose.prod.yml`
  Production stack.
- `nginx/conf.d/default.conf`
  Reverse proxy, CSP, public routing, docs exposure.
- `DEPLOY.md`
  Human deployment reference.

## Architecture Summary

- Frontend: React 18 + Vite + TypeScript + Zustand + Tailwind.
- Backend: FastAPI + async SQLAlchemy + Pydantic.
- Database: PostgreSQL.
- Session/cache: Redis.
- Reverse proxy: Nginx.
- Runtime: Docker Compose.
- Production backend process: Gunicorn with Uvicorn workers.

## Critical Domain Rules

- Survey behavior must remain **JSON-driven**.
- Do not hardcode survey branching rules in React components.
- Do not store patient-sensitive data in `localStorage`.
- Assume all API, report, auth, and Bitrix integration changes can affect production workflows.

## Most Sensitive Areas

### 1. Survey Engine

Files:
- `backend/app/services/survey_engine.py`
- `backend/app/api/v1/endpoints/survey.py`
- `backend/data/*.json`

Risk:
- A small logic mistake can break questionnaire flow, skip branches, corrupt answers, or generate wrong reports.

Rules:
- Validate survey JSON before and after editing.
- Prefer fixing logic in JSON or engine code, not in ad hoc frontend conditionals.
- After changes, verify a real end-to-end survey path.

### 2. Authentication and Session Lifecycle

Files:
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/main.py`
- `backend/app/core/*`

Risk:
- Broken token validation, session expiry, or consent flow can block patient access or weaken security.

Rules:
- Be careful with JWT, Redis, session TTL, cookie settings, proxy headers, and production flags.
- Never relax security defaults without explicit reason.

### 3. Bitrix24 Integration

Files:
- `backend/app/api/v1/endpoints/bitrix_webhook.py`
- `backend/app/services/bitrix24.py`
- parts of `backend/app/api/v1/endpoints/survey.py`

Risk:
- Errors here can break lead/deal enrichment, survey-link generation, timeline comments, PDF upload, or webhook processing.

Rules:
- Preserve existing payload formats and category filters.
- Check logs after deployment for Bitrix webhook failures.

### 4. Reports

Files:
- `backend/app/services/report_generator.py`
- `backend/app/api/v1/endpoints/reports.py`

Risk:
- Wrong report content affects clinical workflows and CRM history.
- PDF issues may come from WeasyPrint dependencies in production.

Rules:
- Verify HTML/TXT/PDF output paths when touching report code.

### 5. Nginx, Docs, and Public Routing

Files:
- `nginx/conf.d/default.conf`
- `backend/app/main.py`

Risk:
- Misrouting can break `/api`, `/admin`, `/docs`, `/redoc`, `/openapi.json`, or `/health`.
- CSP changes can make pages render partially while still returning HTTP 200.

Rules:
- After docs or proxy changes, verify actual browser rendering and browser console state.
- Do not assume a successful HTTP code means the page is healthy.

## Known Infrastructure Pitfalls

- Production API docs are controlled by backend flags, not only by Nginx.
- `/docs`, `/redoc`, and `/openapi.json` must be tested together.
- `vite.config.ts` contains SPA fallback denylist logic, so route conflicts can be subtle.
- Public `/health` routing must be checked carefully because frontend fallback can mask backend health issues.
- Changes to Nginx CSP can break Swagger/ReDoc or admin assets without obvious backend errors.

## Server Information

- Production domain: `https://opros-izdorov.ru`
- Main host: `opros-izdorov.ru`
- Server OS: Ubuntu 22.04
- Project path on server: `/home/deploy/opros`
- Production compose file: `/home/deploy/opros/docker-compose.prod.yml`

## Access Rules

- **Do not store server passwords, tokens, or raw secrets in this repository, in `AGENTS.md`, or in committed scripts.**
- If non-interactive access is needed, use **SSH key authentication with ssh-agent**.
- If credentials must be stored, use an OS password manager or secret store outside the repository.

## Required Non-Interactive Server Access Method

SSH key authentication is fully configured for `root@147.45.249.254`.
**AI Agents must use single-line remote SSH commands** to perform server actions instead of starting interactive sessions.

Example pattern for AI agents (called directly from the VS Code terminal):
```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && <your command>"
```

### Password Handling Policy

- **Zero Passwords:** SSH keys are used exclusively. Do not use, ask for, or store plaintext passwords in Git history, repository files, `AGENTS.md`, or deployment scripts.

## Git-Only Deployment Policy

- Production deployment must go through **Git**, not by manually uploading modified source files.
- Do not patch production code directly on the server unless the user explicitly requests an emergency hotfix.
- If an emergency hotfix is ever applied directly, it must be synchronized back into Git immediately afterward.

## Deployment Instructions (Non-Interactive AI-Agent flow)

Agents should deploy new versions by running this combined command from the local VS Code terminal:

```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && \
git pull origin main && \
docker compose -f docker-compose.prod.yml up -d --build && \
docker compose -f docker-compose.prod.yml exec -w /app backend sh -lc 'PYTHONPATH=/app alembic -c alembic.ini upgrade head'"
```

### Validating Deployments remotely
Check logs or container status using remote non-interactive calls:
```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml ps"
```
```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml logs --tail=50 backend"
```

### App URLs

- `https://opros-izdorov.ru`
- `https://opros-izdorov.ru/admin`
- `https://opros-izdorov.ru/docs`
- `https://opros-izdorov.ru/redoc`

### Emergency Stop

```bash
cd /home/deploy/opros
docker compose -f docker-compose.prod.yml down
```

### Full Restart with Cleanup (danger: removes volumes)

```bash
cd /home/deploy/opros
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
```

## Editing Rules

- Prefer small, auditable changes.
- Do not rewrite broad areas when a targeted fix is enough.
- Respect existing architecture and naming.
- Keep comments concise and only where they help.

## Safety Rules

- Never commit secrets.
- Never relax patient-data protections for convenience.
- Never assume a production issue is fixed until logs and live verification confirm it.
- Never treat successful container startup as sufficient proof of success.
