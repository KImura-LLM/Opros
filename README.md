# 🏥 Опросник пациента — PWA для предварительного сбора анамнеза

Веб-приложение для автоматического сбора жалоб и анамнеза пациентов перед приёмом врача. Работает как PWA (Progressive Web App), интегрируется с CRM Битрикс24. Доступ — по одноразовой JWT-ссылке.

> 📚 Вся документация по деплою и интеграциям хранится отдельно от репозитория (менеджер паролей / внутренняя Wiki).

---

## 🚀 Быстрый старт

```bash
# Клонировать репозиторий и создать .env (по образцу ниже)
cp .env.example .env

# Запустить в dev-режиме
docker compose up -d

# Запустить в prod-режиме
docker compose -f docker-compose.prod.yml up -d
```

| Сервис | URL |
|---|---|
| Фронтенд (Vite dev) | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1 |
| Swagger / OpenAPI | http://localhost:8000/docs |
| Админ-панель | http://localhost:8000/admin |

---

## 🏗 Архитектура

```
nginx (reverse proxy + SSL / Let's Encrypt)
    ├── frontend  (React 18 + Vite, :5173)
    └── backend   (FastAPI + Uvicorn, :8000)
            ├── PostgreSQL 15  (основная БД)
            └── Redis 7        (сессии / кэш)
```

### Сервисы Docker Compose

| Контейнер | Образ | Dev | Prod | Назначение |
|---|---|---|---|---|
| `opros-nginx` | nginx:alpine | ✅ | ✅ | Реверс-прокси, SSL-терминация |
| `opros-certbot` | certbot/certbot | — | ✅ | Автообновление TLS-сертификатов |
| `opros-backend` | custom (Python) | ✅ | ✅ | FastAPI приложение |
| `opros-frontend` | custom (Node) | ✅ | — | React / Vite (HMR) |
| `opros-frontend-builder` | custom (Node) | — | ✅ | Сборка статических файлов |
| `opros-session-cleanup` | custom (Python) | — | ✅ | Фоновый воркер истечения сессий |
| `opros-postgres` | postgres:15-alpine | ✅ | ✅ | Основная БД |
| `opros-redis` | redis:7-alpine | ✅ | ✅ | Сессии и кэш |

---

## 💻 Технический стек

### Backend
| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.10+ | Язык |
| FastAPI | 0.109 | ASGI-фреймворк |
| Pydantic v2 | 2.5 | Валидация данных |
| SQLAlchemy (async) | 2.0 | ORM |
| asyncpg | 0.29 | Драйвер PostgreSQL |
| Alembic | 1.13 | Миграции БД |
| Redis-py | 5.0 | Клиент Redis |
| python-jose | 3.3 | JWT |
| WeasyPrint | 59 | Генерация PDF |
| SQLAdmin | 0.16 | Админ-панель |
| Loguru | 0.7 | Логирование |
| Gunicorn | 21.2 | Production-сервер |

### Frontend
| Компонент | Версия | Назначение |
|---|---|---|
| React | 18.2 | UI-фреймворк |
| TypeScript | 5.3 | Строгая типизация |
| Vite | 5.0 | Сборка / HMR |
| React Router | v6 | Роутинг |
| Zustand | 4.4 | Управление состоянием |
| Tailwind CSS | 3.4 | Стилизация (Mobile First) |
| Framer Motion | 10 | Анимации переходов |
| @xyflow/react | 12 | Визуальный редактор графа |
| vite-plugin-pwa | 0.17 | PWA / Service Worker |
| lucide-react | 0.303 | Иконки |

---

## 📁 Структура проекта

```
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Роутеры API
│   │   │   ├── auth.py           # Авторизация (JWT)
│   │   │   ├── survey.py         # Прохождение опроса
│   │   │   ├── survey_editor.py  # CRUD редактора + правила анализа
│   │   │   ├── reports.py        # Отчёты (HTML/PDF/TXT)
│   │   │   ├── analytics.py      # Дашборд статистики
│   │   │   └── bitrix_webhook.py # Входящие вебхуки Б24
│   │   ├── services/
│   │   │   ├── survey_engine.py      # Движок опросника
│   │   │   ├── report_generator.py   # Генератор отчётов
│   │   │   └── bitrix24.py           # HTTP-клиент Битрикс24
│   │   ├── models/models.py      # SQLAlchemy-модели
│   │   ├── schemas/schemas.py    # Pydantic-схемы
│   │   ├── core/                 # config, database, redis, security, middleware, log_utils
│   │   └── admin/                # SQLAdmin (setup.py + HTML-шаблоны)
│   ├── data/
│   │   ├── survey_structure.json    # Опросник v1
│   │   └── survey_structure_v2.json # Опросник v2 (расширенный)
│   ├── alembic/versions/         # Миграции БД
│   └── scripts/                  # Утилиты (seed, cleanup, expire)
│
└── frontend/
    └── src/
        ├── pages/           # HomePage, SurveyPage, CompletePage, ErrorPage, EditorPage, AnalysisEditorPage
        ├── components/
        │   ├── inputs/      # SingleChoice, MultiChoice, PainScale, BodyMap, TextInput
        │   └── layout/      # Layout, Branding, SessionTimer, ErrorBoundary
        ├── editor/          # Визуальный редактор (@xyflow): SurveyNode, NodeEditor, NodePalette,
        │                    #   EdgeEditor, GroupsPanel, PreviewModal, Toolbar
        ├── analysis/        # Редактор правил анализа: AnalysisEditor, store, types
        ├── store/           # Zustand (surveyStore.ts)
        ├── api/             # HTTP-клиент (surveyApi.ts)
        ├── hooks/           # Кастомные React-хуки
        ├── utils/           # Утилиты
        └── types/           # TypeScript-типы
```

---

## 🔌 API Endpoints (`/api/v1`)

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/auth/validate` | Валидация JWT-токена, создание сессии |
| `POST` | `/auth/generate-token` | Генерация JWT-токена (dev/admin) |
| `GET` | `/survey/config` | Получить конфигурацию опросника |
| `POST` | `/survey/start` | Инициализировать сессию опроса |
| `POST` | `/survey/answer` | Сохранить ответ, получить следующий узел |
| `GET` | `/survey/progress/{session_id}` | Получить прогресс сессии |
| `POST` | `/survey/back` | Вернуться к предыдущему вопросу |
| `POST` | `/survey/complete` | Завершить опрос, отправить в Б24 |
| `GET` | `/editor/surveys` | Список конфигураций опросников |
| `GET` | `/editor/surveys/{id}` | Получить конфигурацию по ID |
| `POST` | `/editor/surveys` | Создать новую конфигурацию |
| `PUT` | `/editor/surveys/{id}` | Обновить JSON-конфиг |
| `DELETE` | `/editor/surveys/{id}` | Удалить конфигурацию |
| `POST` | `/editor/validate-structure` | Валидировать JSON-структуру |
| `POST` | `/editor/duplicate` | Дублировать конфигурацию |
| `POST` | `/editor/export` | Экспортировать конфигурацию |
| `POST` | `/editor/import` | Импортировать конфигурацию |
| `GET` | `/editor/node-types` | Список доступных типов узлов |
| `GET/PUT` | `/editor/{survey_id}/analysis-rules` | Правила анализа опросника |
| `GET` | `/reports/{session_id}/preview` | HTML-предпросмотр отчёта |
| `GET` | `/reports/{session_id}/export/html` | Скачать HTML-отчёт |
| `GET` | `/reports/{session_id}/export/pdf` | Скачать PDF-отчёт |
| `GET` | `/reports/{session_id}/export/txt` | Скачать TXT-отчёт |
| `POST` | `/reports/{session_id}/regenerate` | Перегенерировать отчёт |
| `GET` | `/analytics/dashboard` | Статистика для дашборда |
| `POST` | `/bitrix/webhook` | Входящий вебхук от Битрикс24 |

---

## 🗄 Модели базы данных

| Таблица | Назначение |
|---|---|
| `survey_configs` | JSON-конфигурации опросников (мультиверсионность) |
| `survey_sessions` | Сессии прохождения (привязаны к `lead_id` Б24) |
| `survey_answers` | Ответы на вопросы (JSONB, по `node_id`) |
| `audit_logs` | Журнал аудита (хранится ≤ 24 ч по 152-ФЗ) |

---

## 🧠 Движок опросника (Survey Engine)

Интерфейс рендерится на основе JSON-графа. Логика **не хардкодится в компонентах**.

### Типы узлов (`type`)
| Тип | Описание |
|---|---|
| `single_choice` | Один вариант из списка (карточки) |
| `multi_choice` | Несколько вариантов |
| `scale_1_10` | Шкала боли |
| `body_map` | Интерактивная схема тела |
| `text_input` | Свободный текстовый ввод |
| `info_screen` | Информационный экран |

### Версии опросника
- **v1** — базовый (`survey_structure.json`)
- **v2** — расширенный, включает `body_location`, `pain_character`, фильтры по системам (`resp_filter`, `cardio_filter`, `gastro_filter` и др.)

Версия определяется автоматически по наличию специфичных узлов.

---

## 🔬 Редактор правил анализа

Модуль анализа позволяет задавать автоматические выводы на основе ответов:

- **AnalysisEditorPage** — отдельная страница редактора правил
- Правила задаются через JSON и привязываются к конкретной версии опросника
- API: `GET/PUT /api/v1/editor/{survey_id}/analysis-rules`
- Хранится как часть конфигурации опросника в таблице `survey_configs`

---

## 📊 Отчёты и аналитика

- **HTML-отчёт** — структурированный, готов для вставки в Битрикс24 (метод `crm.timeline.comment.add`)
- **PDF-отчёт** — генерация через WeasyPrint, пригоден для печати
- **TXT-отчёт** — текстовый формат для копирования
- **Дашборд аналитики** — динамика опросов по дням, топ ответов, воронка прохождения, среднее время

---

## 🔐 Безопасность и 152-ФЗ

| Механизм | Реализация |
|---|---|
| **JWT Auth** | Одноразовые токены (`?token=...`), хэш хранится в БД |
| **Rate Limiting** | `RateLimitMiddleware` (FastAPI) + Nginx |
| **CORS** | Строгий список `CORS_ORIGINS` из `.env` |
| **Согласие ПДн** | Блокирующий экран, `consent_given` фиксируется в БД |
| **Очистка данных** | `AuditLog` — TTL 24 ч, `scripts/cleanup.py` |
| **Авто-истечение сессий** | Фоновая задача + `scripts/auto_expire_sessions.py` |
| **Нет PII в localStorage** | Состояние только в RAM (Zustand) и Redis |
| **Проверка секретов** | При запуске проверяются дефолтные значения `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD` |

---

## 📡 Интеграции

### Битрикс24
- **Авторизация:** JWT-ссылка `?token=<JWT>` с `lead_id` и `entity_type` (DEAL / LEAD)
- **Отправка результатов:** `crm.timeline.comment.add` (HTML-комментарий в ленту)
- **Загрузка PDF:** через диск Битрикс24, прикрепление к сделке
- **Входящий вебхук:** `/api/v1/bitrix/webhook` — обработка событий от Б24
- **Фильтрация воронок:** `BITRIX24_ALLOWED_CATEGORIES` (список ID через запятую, пусто = все)

---

## ⚙️ Переменные окружения (`.env`)

```dotenv
# Общие
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=замените-на-случайную-строку
FRONTEND_URL=https://your-domain.com

# PostgreSQL
POSTGRES_USER=opros_user
POSTGRES_PASSWORD=надёжный-пароль
POSTGRES_DB=opros_db
POSTGRES_HOST=postgres

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=надёжный-пароль-redis

# JWT
JWT_SECRET_KEY=замените-на-случайную-строку
JWT_EXPIRATION_HOURS=48

# Админ-панель
ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный-пароль

# Битрикс24
BITRIX24_WEBHOOK_URL=https://your-bitrix.bitrix24.ru/rest/...
BITRIX24_INCOMING_TOKEN=токен-входящего-вебхука
BITRIX24_ALLOWED_CATEGORIES=19,25   # Пусто = все воронки

# Опционально
RATE_LIMIT_PER_MINUTE=60
CORS_ORIGINS_STR=https://your-domain.com
```

---

## 🗃 Миграции БД

```bash
# Применить миграции
docker compose exec backend alembic upgrade head

# Создать новую миграцию
docker compose exec backend alembic revision --autogenerate -m "описание"
```

---

## 🛠 Скрипты обслуживания (`backend/scripts/`)

| Скрипт | Назначение |
|---|---|
| `seed.py` | Загрузить начальную конфигурацию опросника в БД |
| `cleanup.py` | Очистить устаревшие audit-логи (152-ФЗ) |
| `auto_expire_sessions.py` | Перевести просроченные сессии в `abandoned` (запускается как `opros-session-cleanup` в prod) |
| `test_session_expiry.py` | Проверить логику истечения сессий |

---

