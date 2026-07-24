# Аудит готовности Opros к продаже

Дата: 2026-07-24. Объект: текущий репозиторий Opros.

## Резюме

Проект имеет рабочее функциональное ядро и production Compose, но до аудита не
имел воспроизводимой клиентской установки, CI quality gates, dependency gate,
readiness probe и полной эксплуатационной документации. В коде также были логи
с IP, Bitrix/session/analysis IDs и частями токенов.

Этот проход устраняет перечисленные блокеры и фиксирует то, что нельзя честно
объявить завершённым без staging/production испытаний.

## Результаты проверок

- frontend: type-check, ESLint и production build — успешно;
- `npm audit --omit=dev` — 0 уязвимостей;
- backend в Docker с PostgreSQL/Redis и применёнными миграциями — 81 passed;
- production Compose syntax/config — успешно;
- production backend/frontend images — успешно собраны из чистых Docker contexts;
- browser smoke через Playwright: desktop/mobile error state отображается,
  console errors/warnings отсутствуют;
- Linux container PDF smoke на WeasyPrint 69.0 — корректный `%PDF`;
- `/health/live` и `/health/ready` локально возвращают 200.

## Исправлено

- добавлен безопасный `.env.example` и fail-fast production preflight;
- миграции и frontend packaging сделаны одноразовыми зависимостями старта;
- добавлены `/health/live` и `/health/ready`;
- чувствительные идентификаторы удалены из logger calls, добавлен regression guard;
- React Router обновлён до patched 7.18.x;
- Python security patches: pydantic-settings 2.14.2, WeasyPrint 69.0,
  SQLAdmin 0.25.1 и python-multipart 0.0.32;
- добавлены CI проверки backend/frontend/package/compose;
- README заменён актуальной картой документации;
- добавлены setup, operations и commercialization runbooks.

## Мёртвый код и документация

Проверки `vulture --min-confidence 90`, `knip` и Ruff использованы только как
источник кандидатов, после чего каждый кандидат проверялся вручную:

- `vulture` отметил `cls` в Pydantic `@field_validator` — это ложноположительное
  срабатывание;
- `knip` отметил публичные TypeScript-типы и helper, используемый внутри модуля.
- удалён `backend/app/core/log_utils.py`: после запрета логирования ПДн все три
  masking helper стали доказанно неиспользуемыми;
- удалены подтверждённо неиспользуемые Python imports/локальные переменные.

Массовое удаление не выполнялось: для production-медицинского проекта сомнительное
«очищение» опаснее нескольких экспортов. Устаревшее содержимое README удалено, а
архитектурная wiki сохранена как единственный подробный reference.

Каталоги `.agent/` и `.agents/` относятся к локальному agent tooling, не попадают
в runtime image как исполняемый код и требуют отдельного решения владельца
репозитория о поставке исходников. Удалять их автоматически нельзя.

## Открытые риски

| Приоритет | Риск | Что нужно до первой продажи |
|---|---|---|
| P0 | Нет подтверждённой restore-репетиции | Restore на staging, измерить RPO/RTO |
| P0 | Нет юридической/клинической квалификации продукта | Договоры, 152-ФЗ, роль медизделия, consent/retention review |
| P1 | Нет frontend E2E suite | Playwright: magic link → survey → report, doctor/admin access |
| P1 | Worker health поверхностный | Метрика heartbeat/last success и alert по queue age |
| P1 | Нет измеренного SLA/нагрузочного профиля | k6/Locust сценарий с PDF и webhook dependencies |
| P1 | Single-tenant архитектура | Продавать только отдельным инстансом на клинику |
| P2 | Нет централизованных метрик/tracing | OpenTelemetry/Prometheus с bounded labels |
| P2 | Настройки интеграций только через env | Добавить защищённый integration settings UI с secret references |

`pip-audit` оставляет только `PYSEC-2026-1325` в транзитивном `ecdsa` от
`python-jose`. Уязвимый ECDSA code path не используется: production preflight
запрещает алгоритмы кроме HS256. CI фиксирует это как явное точечное исключение;
при переходе на ES256/ES384 исключение необходимо удалить и заменить JWT-библиотеку.

## Рекомендованные настройки админки

Следующий безопасный вертикальный срез:

1. read-only страница «Состояние интеграций» без значений секретов;
2. test connection для Bitrix/OpenRouter с audit event без payload/ID;
3. включение функций и timeout/retry через БД, но секреты — только по ссылке на
   secret manager/environment;
4. versioned configuration и rollback;
5. RBAC: оператор может тестировать, только owner меняет конфигурацию.

Не следует помещать webhook URL, API keys и JWT secrets в обычные SQLAdmin поля.

## Вывод

Репозиторий подготовлен к **пилотной self-hosted поставке**, но маркировка
«полностью отказоустойчив» допустима только после закрытия P0/P1, staging
recovery drill и согласованного SLA.
