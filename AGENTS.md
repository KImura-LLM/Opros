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

The preferred way to avoid asking the user for a server password is:

1. Create an SSH key locally if one does not exist:
   - `ssh-keygen -t ed25519 -C "deploy@opros"`
2. Install the public key on the server for the deployment user.
3. Load the private key into `ssh-agent`:
   - Windows PowerShell:
     - `Get-Service ssh-agent | Set-Service -StartupType Automatic`
     - `Start-Service ssh-agent`
     - `ssh-add $env:USERPROFILE\\.ssh\\id_ed25519`
4. Add a local SSH config entry outside the repo:
   - File: `~/.ssh/config`
   - Example:

```sshconfig
Host opros-prod
    HostName opros-izdorov.ru
    User deploy
    IdentityFile ~/.ssh/id_ed25519
```

Then use:

```bash
ssh opros-prod
scp file.txt opros-prod:/home/deploy/opros/
```

### Password Handling Policy

- Do not automate password entry by hardcoding passwords into shell commands, repository files, `AGENTS.md`, `.bat`, `.ps1`, or committed scripts.
- Do not use plaintext passwords in Git history.
- If password-only access still exists temporarily, migrate to SSH keys as soon as possible.

## Git-Only Deployment Policy

- Production deployment must go through **Git**, not by manually uploading modified source files.
- Do not patch production code directly on the server unless the user explicitly requests an emergency hotfix.
- If an emergency hotfix is ever applied directly, it must be synchronized back into Git immediately afterward.

## Mandatory Deployment Workflow

Always use this order:

1. Check local worktree:
   - `git status`
2. Review changes before deploy.
3. Commit locally with a clear message.
4. Push to the main remote branch:
   - `git push origin main`
5. Connect to the server:
   - `ssh opros-prod`
6. Update code on the server:
   - `cd /home/deploy/opros`
   - `git pull origin main`
7. Rebuild and restart production services:
   - `docker compose -f docker-compose.prod.yml up -d --build`
8. Apply migrations when backend models or schema changed:
   - `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`

## Mandatory Post-Deploy Verification

After every production deployment, verify all of the following:

### Container Status

- `docker compose -f docker-compose.prod.yml ps`

Expected:
- backend is `Up` and healthy
- nginx is running
- postgres is healthy
- redis is healthy

### Logs

Always inspect logs immediately after deployment:

- `docker compose -f docker-compose.prod.yml logs --tail=100 backend`
- `docker compose -f docker-compose.prod.yml logs --tail=100 nginx`
- If frontend changed, also inspect:
  - `docker compose -f docker-compose.prod.yml logs --tail=100 frontend-builder`

Look for:
- startup failures
- migration errors
- Redis connection errors
- database connection errors
- Bitrix webhook exceptions
- report generation failures
- CSP violations or broken docs routes
- 404/500 spikes in Nginx

### Public Endpoint Checks

Verify at least:

- `https://opros-izdorov.ru/`
- `https://opros-izdorov.ru/docs`
- `https://opros-izdorov.ru/redoc`
- `https://opros-izdorov.ru/openapi.json`
- `https://opros-izdorov.ru/admin`
- `https://opros-izdorov.ru/health`

### Browser-Level Verification

Use Playwright or equivalent browser inspection for:

- Swagger UI renders successfully
- ReDoc renders successfully
- no blocking browser console errors on changed pages
- no broken network requests on critical flows

### Functional Smoke Tests

When relevant to the change, verify:

- survey start
- answering at least one branch
- report preview/export path
- Bitrix-related endpoint behavior
- admin page load

## Monitoring and Error Review

After deployment, do not stop at HTTP 200 checks.
Always perform short-term monitoring:

- review fresh backend logs
- review fresh Nginx logs
- watch for repeated errors for several minutes after restart
- if the change affects CRM integration, check for incoming Bitrix webhook errors
- if the change affects docs/admin/frontend, inspect browser console and network requests

If any critical error appears after deployment:

1. stop and document the failure clearly
2. decide whether a fast rollback is safer than forward-fixing
3. if rollback is needed, use Git to roll back to a known good revision and redeploy

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
