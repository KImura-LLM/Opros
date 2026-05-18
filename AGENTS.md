# AGENTS.md

Краткие инструкции для AI-агентов в проекте **Opros**. Подробная архитектура и процессы описаны в `docs/PROJECT_WIKI.md`; деплойные команды и справка — в `DEPLOY.md`. Если инструкции расходятся, сначала следуй этому файлу, затем `docs/PROJECT_WIKI.md`, затем `DEPLOY.md`.

## 1. Главное правило

Opros — production PWA для медицинских опросов, отчётов, врачебного портала, Bitrix24 и AI-анализа. Проект работает с ПДн и медицински чувствительными данными.

- Отвечай пользователю на **русском**, если он явно не попросил другой язык.
- По умолчанию работай **только локально**: файлы проекта, локальный Docker Compose, локальная БД.
- Не используй SSH, production, удалённый deploy и production Bitrix24 без явной команды пользователя.
- Перед нетривиальной правкой кратко обозначай план и критерии проверки.
- Делай минимальные точечные изменения; не рефактори соседний код без необходимости.
- Перед правками проверяй `git status`; не затирай чужие/уже существующие изменения.
- Названия коммитов и описания к ним пиши на русском языке.
- Не коммить, не печатай и не логируй секреты: `.env`, пароли, JWT, Bitrix/OpenRouter ключи, webhook URL, `token_hash`.
- Не логируй ПДн: ФИО, контакты, Bitrix ID, session ID, IP/user-agent.

## 2. Краткая карта проекта

### Backend

- `backend/app/main.py` — FastAPI app, middleware, sessions, API routers, SQLAdmin, docs, health.
- `backend/app/api/v1/endpoints/` — API endpoints:
  - `auth.py` — JWT/session flow;
  - `survey.py` — прохождение опроса;
  - `survey_editor.py` — CRUD редактора;
  - `survey_routing.py` — маршрутизация опросников;
  - `reports.py` — HTML/TXT/PDF отчёты;
  - `analytics.py` — аналитика;
  - `bitrix_webhook.py` — Bitrix24 webhooks;
  - `doctors.py` — врачебный портал.
- `backend/app/services/` — бизнес-логика:
  - `survey_engine.py`, `survey_routing.py`, `report_generator.py`, `bitrix24.py`, `bitrix_crm_fields.py`, `doctor_portal_routing.py`, `ai_analysis/`.
- `backend/app/models/` — SQLAlchemy models.
- `backend/app/admin/` — SQLAdmin views/templates.
- `backend/data/` — JSON-опросники.
- `backend/alembic/` — миграции.
- `backend/scripts/` — seed/cleanup/session expiry/Bitrix sync/AI worker.
- `backend/tests/` — backend tests.

### Frontend

- `frontend/src/App.tsx` — routes: `/`, `/s/:code`, `/survey`, `/complete`, `/error`, `/doctors`, `/editor/:surveyId`, `/analysis-editor/:surveyId`, `/routing`.
- `frontend/src/pages/` — страницы анкеты, редакторов, маршрутизации, врачебного портала.
- `frontend/src/store/surveyStore.ts` — критичный Zustand store прохождения опроса.
- `frontend/src/store/doctorStore.ts` — состояние врачебного портала.
- `frontend/src/api/` — survey/doctor/routing API clients.
- `frontend/src/editor/` — визуальный редактор опросника.
- `frontend/src/analysis/` — rule-based analysis editor.
- `frontend/vite.config.ts` — PWA и SPA fallback denylist.

### Infra/docs

- `docker-compose.yml` — local stack.
- `docker-compose.prod.yml` — production stack.
- `nginx/conf.d/default.conf` — reverse proxy, CSP, `/api`, `/admin`, `/docs`, `/redoc`, `/health`.
- `docs/PROJECT_WIKI.md` — подробная актуальная wiki.
- `DEPLOY.md` — справка по ручному деплою; перед применением сверять с текущей deploy-policy ниже.

## 3. Критичные доменные правила

- Survey logic должна оставаться **JSON-driven**. Не хардкодь branching/medical logic в React.
- Не сохраняй patient-sensitive данные в `localStorage`.
- Не удаляй/не переименовывай `node_id` без анализа влияния на ответы, отчёты, analysis rules, routing и snapshots.
- Не меняй смысл существующих answer values без compatibility/миграционного плана.
- Не удаляй физически `SurveyConfig`, если есть ссылки из `survey_sessions`, routing rules или clinic defaults. Обычно нужно деактивировать опросник или переназначить/удалить тестовые связанные данные.
- Завершённые отчёты должны оставаться воспроизводимыми через snapshot/исторический config.
- AI/OpenRouter не должен получать ПДн: ФИО, контакты, Bitrix ID, session ID, JWT/token_hash, IP/user-agent.
- AI-анализ не заменяет rule-based анализ и не должен блокировать завершение опроса пациентом.
- Любое изменение моделей БД требует оценки Alembic migration и локальной проверки upgrade.

## 4. Самые чувствительные зоны

- **Survey flow:** `survey_engine.py`, `survey.py`, `backend/data/*.json`, `SurveyPage.tsx`, `surveyStore.ts`.
- **Auth/session:** `auth.py`, `security.py`, Redis/session middleware, expiry scripts.
- **Editor/routing:** `survey_editor.py`, `survey_routing.py`, `frontend/src/editor/`, `frontend/src/analysis/`, `SurveyRoutingPage.tsx`.
- **Reports:** `report_generator.py`, `reports.py`; проверять HTML/TXT/PDF и snapshots.
- **Bitrix24:** `bitrix_webhook.py`, `bitrix24.py`, `bitrix_crm_fields.py`; сохранять payload compatibility.
- **AI:** `backend/app/services/ai_analysis/`, `ai_analysis_view.py`, `process_ai_analysis_jobs.py`; проверять anonymization/retry/fail path.
- **Doctor portal:** `doctors.py`, `doctor_user.py`, `doctor_portal_routing.py`, `frontend/src/pages/doctors/`; не расширять доступ без требования.
- **SQLAdmin:** destructive actions должны проверять связи и показывать понятные ошибки.
- **Nginx/Vite routing/CSP:** после изменений проверять browser render и console, не только HTTP 200.

## 5. Локальная разработка и проверки

Запуск:

```bash
docker compose up -d --build
```

Миграции:

```bash
docker compose exec backend sh -lc "PYTHONPATH=/app alembic -c alembic.ini upgrade head"
```

Health/status:

```bash
docker compose ps
curl http://localhost:8000/health
```

Локальные URL:

- frontend: `http://localhost:5173`
- backend/docs: `http://localhost:8000/docs`
- redoc: `http://localhost:8000/redoc`
- admin: `http://localhost:8000/admin`
- health: `http://localhost:8000/health`

Проверки под задачу:

- Backend syntax/import: `docker compose exec -T backend python -m py_compile <files>` и/или `docker compose exec -T backend python -c "from app.main import app; print('ok')"`.
- Backend tests: `docker compose exec -T backend python -m pytest -q` или точечные tests из `backend/tests/`, если pytest доступен.
- Frontend: `cd frontend && npm run type-check` или `npm run build`.
- Survey/report changes: пройти локальный e2e путь анкеты, проверить report preview и exports.
- Routing/doctor changes: проверить clinic bucket, правила маршрутизации и доступ врача.
- AI changes: проверить queue status, retry/fail path и отсутствие ПДн в anonymized payload.
- Nginx/Vite/CSP changes: проверить `/api`, `/admin`, `/docs`, `/redoc`, `/openapi.json`, `/health` в браузере.

## 6. Production/deploy policy

Production:

- domain: `https://opros-izdorov.ru`
- server path: `/home/deploy/opros`
- compose: `/home/deploy/opros/docker-compose.prod.yml`
- SSH pattern: `ssh root@147.45.249.254 "cd /home/deploy/opros && <command>"`

Правила:

- Production/SSH/deploy — только после явного подтверждения пользователя.
- Деплой только через Git, не ручным копированием файлов.
- Не деплоить из dirty working tree.
- Текущая модель: отдельный deploy-коммит/ветка `deploy` с runtime-файлами; не деплоить напрямую из общего/чернового коммита.
- Перед deploy назвать: deploy branch/commit hash, runtime changes, migrations, verification plan, rollback/stop plan.
- После deploy сообщить: что проверено, что прошло, какие риски остались.

Шаблон production deploy после подтверждения:

```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && \
  git fetch origin deploy && \
  git checkout deploy && \
  git pull --ff-only origin deploy && \
  docker compose -f docker-compose.prod.yml up -d --build && \
  docker compose -f docker-compose.prod.yml exec -w /app backend sh -lc 'PYTHONPATH=/app alembic -c alembic.ini upgrade head'"
```

Remote checks:

```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml ps"
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml logs --tail=50 backend"
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml logs --tail=50 nginx"
```

Если менялись workers, проверять logs: `opros-session-cleanup`, `opros-bitrix-field-sync`, `opros-ai-analysis-worker`.

Emergency stop только по явной команде:

```bash
ssh root@147.45.249.254 "cd /home/deploy/opros && docker compose -f docker-compose.prod.yml down"
```

`down -v` удаляет volumes/data — использовать только при прямом явном указании.

## 7. Known pitfalls

- Production docs зависят от backend flags (`DEBUG`, `ENABLE_API_DOCS`) и Nginx/CSP.
- `/docs`, `/redoc`, `/openapi.json` проверять вместе.
- SPA fallback может замаскировать backend routes; особенно `/health`.
- CSP может сломать Swagger/ReDoc/SQLAdmin assets при HTTP 200.
- После `.env` changes пересоздавать backend и связанные workers.
- Worker health не равен бизнес-успеху; при AI changes проверять failed/running jobs.
- Локальный compose не должен отправлять данные в production Bitrix24 без явного намерения.
