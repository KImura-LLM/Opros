# Opros

Production PWA для медицинских опросов: JSON-driven анкеты, отчёты
HTML/TXT/PDF, врачебный портал, маршрутизация, Bitrix24 и опциональный
обезличенный AI-анализ.

> Opros обрабатывает медицински чувствительные данные. Перед реальным
> внедрением заказчик обязан определить правовые основания обработки,
> сроки хранения, роли доступа, договоры с внешними обработчиками и порядок
> реагирования на инциденты.

## Быстрый локальный запуск

Требования: Docker Desktop с Compose v2, Git, 4+ CPU, 8+ ГБ RAM.

```powershell
Copy-Item .env.example .env
# Заменить CHANGE-ME значения. Для локальной разработки:
# ENVIRONMENT=development, DEBUG=true, FRONTEND_URL=http://localhost:5173
docker compose up -d --build
docker compose exec -T backend python -m pytest -q
```

Сервисы:

- frontend: <http://localhost:5173>
- backend: <http://localhost:8000>
- API docs в development: <http://localhost:8000/docs>
- admin: <http://localhost:8000/admin>
- liveness: <http://localhost:8000/health/live>
- readiness: <http://localhost:8000/health/ready>

## Production

1. Выполнить [инструкцию установки](docs/INSTALLATION.md).
2. Пройти [production checklist](docs/OPERATIONS.md#production-checklist).
3. Запускать только из чистого, проверенного Git SHA:

```bash
docker compose --env-file .env -f docker-compose.prod.yml config -q
docker compose -f docker-compose.prod.yml run --rm migrate python -m scripts.preflight
docker compose -f docker-compose.prod.yml up -d --build
curl --fail https://your-domain.example/health/ready
```

Production Compose автоматически выполняет preflight и Alembic migration до
старта backend/workers. Значения секретов preflight никогда не печатает.

## Проверки

```powershell
.\scripts\run_local_checks.ps1
```

Или отдельно:

```bash
python -m pytest backend/tests -q
cd frontend
npm ci
npm run type-check
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
```

## Документация

- [Установка и первичная настройка](docs/INSTALLATION.md)
- [Эксплуатация, backup, restore, monitoring и rollback](docs/OPERATIONS.md)
- [Архитектура и доменные правила](docs/PROJECT_WIKI.md)
- [Аудит готовности продукта](docs/PRODUCTIZATION_AUDIT.md)
- [Модель продажи и roadmap](docs/COMMERCIALIZATION.md)

## Границы текущего продукта

- Рекомендуемая модель поставки: отдельный self-hosted инстанс на клинику.
- Это не медицинское изделие и не заменяет решение врача без отдельной
  юридической и клинической квалификации.
- Полноценные SaaS multi-tenancy, биллинг и license server в текущую поставку
  не входят; план развития описан в `docs/COMMERCIALIZATION.md`.
- Секреты хранятся только в `.env`/secret manager и не редактируются в SQLAdmin.
