# Чеклист подготовки к продаже

## Аудит

- [x] Проверить git status и структуру репозитория.
- [x] Выполнить baseline frontend checks.
- [x] Выполнить baseline backend checks или зафиксировать блокер окружения.
- [x] Выполнить первичный dependency/dead-code scan.
- [x] Сохранить итоговый аудиторский отчёт.

## Безопасная настройка

- [x] Добавить `.env.example` без секретов.
- [x] Добавить production preflight с позитивными и негативными тестами.
- [x] Удалить чувствительные идентификаторы из логов.
- [x] Добавить regression test политики логирования.

## Эксплуатация

- [x] Добавить liveness/readiness endpoints и тесты.
- [x] Добавить CI quality gates.
- [x] Описать установку, upgrade, backup/restore, monitoring и rollback.

## Коммерциализация

- [x] Описать границы поставки и модель лицензирования.
- [x] Описать onboarding заказчика и пакет внедрения.
- [x] Сформировать roadmap к multi-tenant SaaS.

## Финальная проверка

- [x] Backend tests проходят.
- [x] Frontend type-check, lint и build проходят.
- [x] Dependency audit не содержит high/critical уязвимостей.
- [x] Compose configuration проходит валидацию.
- [x] Production backend/frontend images собираются в чистом Linux-контексте.
- [x] Выполнен финальный code review.
