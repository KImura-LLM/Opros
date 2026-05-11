# Opros Wiki

Актуально на: 2026-05-11  
Назначение: внутренняя документация проекта, правила разработки, эксплуатации и деплой-процесса.

## 1. Что такое Opros

**Opros** — production PWA-платформа для предварительного медицинского опроса пациента перед визитом к врачу. Система собирает жалобы, анамнез, ответы по JSON-опроснику, формирует врачебный отчёт, передаёт результат в Bitrix24 и предоставляет административные инструменты для настройки логики.

Проект работает с медицински чувствительными и персональными данными. Любое изменение backend, frontend, отчётов, Bitrix-интеграции, маршрутизации или инфраструктуры считается потенциально высокорисковым.

Основные функции:

- одноразовая JWT-ссылка на опрос из Bitrix24;
- сбор согласия пациента на обработку данных;
- JSON-driven прохождение анкеты;
- сохранение ответов и истории прохождения;
- генерация HTML/TXT/PDF отчётов;
- rule-based системный анализ для врача;
- AI-анализ ответов через OpenRouter с обезличиванием;
- отправка результатов и PDF в Bitrix24;
- админ-панель SQLAdmin;
- визуальный редактор опросников и правил;
- маршрутизация опросов/врачей/клиник;
- врачебный портал;
- фоновая очистка и истечение сессий.

## 2. Технологический стек

### Backend

- Python 3.10+
- FastAPI
- SQLAlchemy async
- Alembic
- PostgreSQL
- Redis
- SQLAdmin
- Pydantic / pydantic-settings
- httpx
- Loguru
- WeasyPrint
- Gunicorn + Uvicorn workers в production

### Frontend

- React 18
- TypeScript
- Vite
- Zustand
- Tailwind CSS
- React Router
- PWA manifest/service worker
- @xyflow/react для визуального редактора

### Инфраструктура

- Docker Compose для local/dev и production
- Nginx как reverse proxy
- PostgreSQL как основная БД
- Redis для session/cache
- Bitrix24 REST/webhook интеграция
- OpenRouter API для AI-анализа

## 3. Основная структура репозитория

```text
backend/
  app/
    api/v1/endpoints/       FastAPI endpoints
    admin/                  SQLAdmin views/templates
    core/                   config, database, redis, middleware, security
    models/                 SQLAlchemy модели
    schemas/                Pydantic схемы
    services/               бизнес-логика
  alembic/                  миграции БД
  data/                     JSON-конфигурации опросников
  scripts/                  фоновые/служебные скрипты
  tests/                    backend-тесты

frontend/
  src/
    pages/                  страницы приложения
    components/             UI-компоненты
    store/                  Zustand stores
    api/                    API-клиенты
    editor/                 визуальный редактор опросника
    analysis/               редактор правил анализа

nginx/                      reverse proxy конфиги
docs/                       документация/wiki
docker-compose.yml          локальная сборка
docker-compose.prod.yml     production сборка
```

## 4. Ключевые backend-модули

### `backend/app/main.py`

Точка входа FastAPI. Подключает middleware, API routes, админку, health endpoint, документацию API в зависимости от настроек окружения.

### `backend/app/core/config.py`

Единая конфигурация проекта. Все новые environment variables должны добавляться сюда. Секреты нельзя хардкодить и нельзя коммитить в репозиторий.

Критичные группы настроек:

- database/redis;
- JWT/security;
- CORS/frontend URL;
- Bitrix24;
- OpenRouter/AI analysis;
- admin credentials;
- environment/debug flags.

### `backend/app/api/v1/endpoints/survey.py`

Критичный endpoint прохождения опроса:

- старт сессии;
- сохранение ответа;
- переходы назад;
- завершение опроса;
- постановка фоновых задач отчёта/AI.

Любые изменения требуют end-to-end проверки реального прохождения анкеты.

### `backend/app/services/survey_engine.py`

JSON-driven движок опросника. Именно здесь должна жить логика переходов, условий, валидации и определения следующего вопроса.

Нельзя переносить branching-логику в React-компоненты.

### `backend/app/services/report_generator.py`

Формирует HTML/TXT/PDF содержимое отчёта. Содержит:

- данные пациента/врача;
- ответы по группам;
- AI-блок, если он успешно сохранён;
- rule-based системный анализ;
- безопасное экранирование HTML;
- snapshot-совместимые структуры.

### `backend/app/services/bitrix24.py`

Bitrix24 REST-клиент. Отвечает за:

- timeline comments;
- загрузку PDF;
- работу с leads/deals;
- обработку ошибок интеграции.

Изменения здесь могут повлиять на CRM-процесс клиники.

### `backend/app/services/ai_analysis/`

Модуль AI-анализа через OpenRouter:

- `anonymizer.py` — формирует обезличенный payload;
- `prompt.py` — системный и пользовательский prompt;
- `schemas.py` — строгая структура ответа модели;
- `openrouter_client.py` — HTTP-клиент OpenRouter;
- `service.py` — orchestration, retry/failure handling, запись результата;
- `backend/scripts/process_ai_analysis_jobs.py` — worker DB-backed очереди.

AI-анализ не заменяет системный rule-based анализ и не должен задерживать пациента при завершении опроса.

## 5. Ключевые frontend-модули

### `frontend/src/pages/SurveyPage.tsx`

Основной пользовательский поток анкеты. Должен оставаться тонким UI-слоем, без хардкода медицинской логики ветвления.

### `frontend/src/store/surveyStore.ts`

Zustand store состояния прохождения. Нельзя сохранять персональные данные пациента в `localStorage`.

### `frontend/src/api/surveyApi.ts`

API-клиент опросника. Должен сохранять совместимость с backend contract.

### `frontend/src/editor/`

Визуальный редактор опросника. Использует graph-based представление и должен сохранять JSON-driven модель.

### `frontend/src/pages/SurveyRoutingPage.tsx`

Интерфейс настройки маршрутизации. Изменения нужно проверять вместе с backend routing endpoints.

## 6. Модель данных

Основные таблицы:

- `survey_configs` — версии JSON-опросников и правила анализа;
- `survey_sessions` — сессии прохождения, статус, Bitrix-связка, snapshot отчёта;
- `survey_answers` — ответы пациента по `node_id`;
- `survey_ai_analyses` — статус и результат AI-анализа;
- `audit_logs` — аудит;
- doctor/routing таблицы — врачебный портал, клиники, настройки видимости и маршрутизации.

Миграции создаются только через Alembic и должны быть идемпотентны относительно текущего состояния production БД.

## 7. Опросник и JSON-driven правила

Главное правило: поведение анкеты определяется JSON-конфигурацией и backend-движком, а не условными конструкциями в UI.

Нельзя:

- хардкодить переходы между вопросами в React;
- добавлять медицинскую branching-логику в компоненты;
- менять структуру JSON без проверки валидатором;
- удалять node_id, если на них завязаны ответы, отчёты, правила или маршрутизация;
- менять смысл существующих answer value без миграционного плана.

После изменения опросника нужно проверить:

1. JSON валиден.
2. Старт опроса работает.
3. Ответы сохраняются.
4. Ветки переходят корректно.
5. Завершение создаёт отчёт.
6. Отчёт содержит ожидаемые ответы.

## 8. Отчёты

Система поддерживает:

- HTML preview;
- HTML export;
- PDF export через WeasyPrint;
- TXT export;
- report snapshot в `survey_sessions.report_snapshot`.

Особенности:

- snapshot нужен для стабильности уже завершённых отчётов;
- регенерация отчёта не должна без явного действия повторно вызывать OpenRouter;
- AI-блок отображается выше rule-based системного анализа;
- rule-based системный анализ нельзя удалять или смешивать с AI;
- HTML должен экранировать пользовательские ответы.

## 9. AI-анализ через OpenRouter

AI-анализ запускается после завершения опроса в фоне через DB-backed очередь.

Поток:

1. Пациент завершает опрос.
2. Backend быстро фиксирует `completed` и создаёт/обновляет `SurveyAiAnalysis` со статусом `pending`.
3. Worker забирает pending-задачу.
4. Anonymizer собирает только фактически заданные вопросы и ответы.
5. OpenRouter получает только обезличенный clinical payload.
6. Ответ модели валидируется как строгий JSON.
7. Успешный результат сохраняется в `survey_ai_analyses`.
8. Report snapshot обновляется с AI-блоком.
9. Если AI недоступен, отчёт остаётся доступным без AI-блока.

В OpenRouter запрещено передавать:

- ФИО пациента;
- ФИО врача;
- `SurveySession.id`;
- `lead_id` / Bitrix ID;
- телефоны, email, адреса;
- token/token_hash/JWT;
- IP/user-agent;
- сырые CRM payload;
- секреты и environment variables.

AI не должен:

- ставить диагноз;
- назначать лечение;
- назначать дозировки;
- заменять врача;
- утверждать факты, которых нет в ответах.

AI может:

- выделять красные флаги;
- формировать краткое резюме;
- указывать зоны внимания;
- предлагать врачу уточняющие вопросы;
- присваивать `overall_priority`: `red`, `yellow`, `green`.

## 10. Bitrix24

Bitrix24 используется для CRM-процесса:

- создание/обработка ссылок на опрос;
- связь с lead/deal;
- добавление комментариев в timeline;
- загрузка PDF;
- получение/использование custom fields;
- фильтрация по allowed categories.

Локальная разработка не должна отправлять тестовые данные в production Bitrix24. В локальном `docker-compose.yml` webhook должен быть отключён или заменён тестовым значением.

При изменении Bitrix-кода обязательно проверить:

- входящий webhook;
- формирование ссылки;
- фильтры категорий;
- timeline comment;
- PDF upload;
- отсутствие секретов в логах.

## 11. Админ-панель

SQLAdmin используется для внутренних операций:

- просмотр сессий и ответов;
- управление опросниками;
- маршрутизация;
- мониторинг AI-задач;
- ручной retry failed AI-задачи;
- просмотр отчётов и snapshot.

При добавлении новой admin view нужно:

1. Создать отдельный view-класс.
2. Зарегистрировать его в `backend/app/admin/setup.py`.
3. Проверить доступность `/admin`.
4. Проверить, что sensitive fields не раскрываются без необходимости.

## 12. Безопасность и приватность

Проект обрабатывает медицинские и персональные данные. Базовые правила:

- не коммитить `.env`, ключи, токены, пароли, приватные сертификаты;
- не писать секреты в README/docs/issues/logs;
- не хранить patient-sensitive данные в frontend `localStorage`;
- не логировать JWT, token_hash, OpenRouter key, Bitrix webhook;
- не отправлять production данные во внешние тестовые сервисы;
- не отключать CORS/security/rate limit ради удобства;
- не расширять публичные endpoints без явной причины;
- не считать HTTP 200 доказательством корректной работы UI;
- не использовать production/SSH без прямого запроса пользователя.

## 13. Что делать нельзя

Категорически нельзя:

1. Деплоить напрямую с рабочей ветки `main`.
2. Выполнять production deploy без deploy-коммита.
3. Патчить production-код вручную на сервере, кроме явно согласованного emergency hotfix.
4. Коммитить `.env` и любые секреты.
5. Передавать персональные данные в OpenRouter.
6. Заменять rule-based системный анализ AI-анализом.
7. Делать завершение опроса зависимым от скорости внешнего AI API.
8. Хардкодить логику опросника во frontend.
9. Удалять/переименовывать node_id без анализа последствий.
10. Менять Bitrix payload format без обратной совместимости.
11. Смешивать документационные/spec/test изменения с deploy-коммитом.
12. Делать широкие рефакторинги рядом с точечной задачей.
13. Деплоить без миграций, если изменена модель БД.
14. Считать контейнер `up` достаточной проверкой production.
15. Оставлять worker без мониторинга статусов failed/running.

## 14. Локальный запуск

Базовый local flow:

```bash
docker compose up -d --build
```

Миграции:

```bash
docker compose exec backend sh -lc "PYTHONPATH=/app alembic -c alembic.ini upgrade head"
```

Проверки:

```bash
docker compose ps
curl http://localhost:8000/health
```

Локальные URL:

- frontend: `http://localhost:5173`
- backend docs: `http://localhost:8000/docs`
- admin: `http://localhost:8000/admin`
- health: `http://localhost:8000/health`

## 15. Переменные окружения

Ключевые группы переменных:

- `DATABASE_URL`, `POSTGRES_*`;
- `REDIS_URL`;
- `SECRET_KEY`, `JWT_SECRET_KEY`;
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`;
- `FRONTEND_URL`, `CORS_ORIGINS`;
- `BITRIX24_WEBHOOK_URL`, `BITRIX24_ALLOWED_CATEGORIES`;
- `AI_ANALYSIS_ENABLED`;
- `OPENROUTER_API_KEY`;
- `OPENROUTER_BASE_URL`;
- `OPENROUTER_MODEL`;
- `OPENROUTER_TIMEOUT_SECONDS`;
- `AI_ANALYSIS_MAX_ATTEMPTS`;
- `AI_ANALYSIS_PROMPT_VERSION`;
- `AI_ANALYSIS_ZDR_REQUIRED`.

Секреты хранятся только вне Git. Для документации использовать имена переменных без значений.

## 16. Тестирование

Минимальная проверка перед коммитом backend-логики:

```bash
python -m pytest backend/tests -q
```

Если зависимости установлены только в локальной `.venv`:

```bash
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Для изменений отчётов обязательно проверить:

- HTML preview;
- PDF export;
- TXT export;
- snapshot/regenerate;
- наличие/отсутствие AI-блока по статусу задачи.

Для frontend изменений:

```bash
cd frontend
npm run build
```

## 17. Новая Git/deploy-модель

С 2026-05-11 структура подготовки изменений делится на два типа коммитов.

### 17.1. Общий коммит

Общий коммит находится в основной рабочей ветке и может содержать полный контекст задачи:

- код;
- тесты;
- документацию;
- wiki;
- вспомогательные локальные инструкции;
- не-production спецификации, если они нужны для истории задачи;
- изменения, которые не должны напрямую попадать в production deploy.

Назначение общего коммита — сохранить полный контекст разработки и ревью.

### 17.2. Deploy-коммит

Deploy-коммит создаётся отдельно в ветке `deploy` и содержит только файлы, необходимые для запуска проекта в production/local runtime:

- backend runtime код;
- frontend runtime код;
- миграции БД;
- production/local compose файлы;
- nginx конфиги;
- package/requirements lock files;
- scripts, которые реально нужны runtime/maintenance;
- статические assets frontend.

Deploy-коммит не должен содержать:

- specs;
- thoughts;
- черновики;
- тесты, если они не нужны для runtime;
- локальные отладочные артефакты;
- `.env`;
- логи;
- `.venv`, `node_modules`, build outputs;
- IDE/cache файлы;
- документацию, если она не требуется для запуска.

### 17.3. Правило деплоя

Деплой выполняется **только с deploy-коммита из ветки `deploy`**.

Нельзя деплоить:

- напрямую из `main`;
- из общего коммита;
- из dirty working tree;
- из коммита, где смешаны runtime изменения и specs/черновики;
- без понимания, какие миграции будут применены.

Перед production deploy нужно явно назвать:

1. hash deploy-коммита;
2. список runtime изменений;
3. миграции;
4. план проверки;
5. rollback/stop план.

В этой задаче деплой **не выполняется**.

## 18. Production deployment policy

Production-домен: `https://opros-izdorov.ru`.

Deployment выполняется только после явной команды пользователя. По умолчанию все действия выполняются локально.

Базовый production flow по Git:

1. Подготовить общий коммит в `main`.
2. Подготовить deploy-коммит в `deploy`.
3. Проверить локально сборку и миграции.
4. Получить явное подтверждение на deploy.
5. На сервере подтянуть только разрешённый deploy-коммит/ветку.
6. Выполнить `docker compose -f docker-compose.prod.yml up -d --build`.
7. Применить Alembic migrations.
8. Проверить health, docs/admin, survey flow, reports, Bitrix logs.

Без явной команды пользователя production/SSH не использовать.

## 19. Проверочный чеклист перед deploy-коммитом

- [ ] Нет `.env` и секретов в staged files.
- [ ] Нет specs/thoughts/черновиков.
- [ ] Нет логов/cache/build outputs.
- [ ] Есть все runtime файлы.
- [ ] Миграции добавлены, если менялись модели.
- [ ] `docker-compose.prod.yml` соответствует новым сервисам.
- [ ] Worker добавлен, если нужна фоновая обработка.
- [ ] Локальная миграция прошла.
- [ ] Локальный backend health OK.
- [ ] Критичные tests/build выполнены или явно указано, почему нет.

## 20. Особенности работы с AI-анализом

- OpenRouter API key должен быть ASCII-валидным.
- Нельзя выводить ключ в терминал или лог.
- Worker должен корректно переводить stuck/running задачи в failed или retry.
- При невалидном JSON от модели задача должна retry до лимита.
- Отчёт должен оставаться доступным без AI.
- Snapshot должен фиксировать метаданные AI: model, status, included, analysis_id, prompt_version, overall_priority.
- Ручной retry должен быть доступен только из админского контура.

## 21. Особенности локальной разработки

- Локальный compose должен быть безопасен относительно production Bitrix.
- После изменения `.env` нужно пересоздать backend/worker контейнеры.
- После изменения модели БД нужно применить Alembic migration.
- После изменения frontend package нужно обновлять lockfile.
- После изменения Vite routing нужно проверить `/api`, `/admin`, `/docs`, `/redoc`, `/health`, чтобы SPA fallback не маскировал backend routes.

## 22. Минимальный end-to-end сценарий проверки

1. Запустить local stack.
2. Применить миграции.
3. Открыть frontend.
4. Создать/получить survey token.
5. Пройти опрос до конца.
6. Проверить, что session стала `completed`.
7. Проверить report preview.
8. Проверить PDF/TXT export.
9. Проверить AI status в admin/БД.
10. Если AI succeeded — проверить AI-блок в начале отчёта.
11. Убедиться, что локально не ушли реальные данные в Bitrix.

## 23. Правило изменения документации

`docs/` — единственное место для актуальной wiki проекта.

Папки `specs` и черновые `thoughts` не должны использоваться как источник production-документации. Если нужна постановка задачи, после реализации её нужно перенести в wiki или удалить.
