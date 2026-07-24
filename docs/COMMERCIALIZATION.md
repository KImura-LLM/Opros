# План продажи Opros

## Позиционирование

Продукт: self-hosted платформа предвизитного сбора анамнеза для клиник с
настраиваемыми опросниками, отчётами, врачебным порталом и CRM-интеграцией.

Не обещать:

- постановку диагноза или замену врача;
- соответствие закону «из коробки» без обследования процессов заказчика;
- zero downtime/SLA без измерений и резервной инфраструктуры;
- SaaS multi-tenancy в текущей версии.

## Коммерческие пакеты

### Pilot

- один инстанс, одна клиника;
- установка, branding, один опросник, одна Bitrix24 воронка;
- обучение администратора;
- 30 дней ограниченной поддержки.

### Standard

- несколько версий опросников и routing;
- врачебный портал, отчёты, backup monitoring;
- staging среда, регламент обновлений;
- рабочее время поддержки и квартальный security update.

### Enterprise

- HA database/Redis, несколько app replicas;
- SSO/RBAC, audit export, индивидуальные retention policies;
- интеграционный адаптер, SLA, DR drill;
- выделенный контур и сопровождение.

Цена должна разделяться на лицензию, внедрение, инфраструктуру и поддержку.
Не включайте неопределённые интеграционные доработки в фиксированную лицензию.

## Процесс продажи

1. Discovery: объём пациентов, роли, CRM, опросники, retention, SLA.
2. Security/legal questionnaire и data-flow diagram.
3. Пилот только на синтетических/обезличенных данных.
4. Приёмка по измеримым критериям из `INSTALLATION.md`.
5. Договор на внедрение, DPA/поручение обработки, SLA и support boundaries.
6. Production rollout с backup/rollback и ответственными.
7. 14/30-дневный success review: completion rate, ошибки, время врача.

## Лицензирование

Практичный первый вариант:

- годовая лицензия на один deployment/клинику;
- подписка на обновления и security fixes;
- отдельная стоимость внедрения и интеграций;
- офлайн license file с подписью, grace period и без блокировки patient flow;
- при недействительной лицензии блокировать административные изменения, но не
  прохождение активной анкеты и доступ к уже созданным медицинским данным.

License server не должен получать ПДн или стабильные patient identifiers.

## Roadmap

### 0–30 дней: продаваемый пилот

- закрыть P0/P1 из аудита;
- Playwright E2E и staging restore drill;
- support/runbook templates и release notes;
- SBOM, image scanning, подписанные release artifacts.

### 30–90 дней: управляемые интеграции

- integration status page и безопасный test connection;
- versioned feature flags/timeouts/retries;
- worker heartbeat, metrics, alerting;
- branding и clinic profile без правки кода.

### 90–180 дней: enterprise

- RBAC/SSO, immutable audit trail;
- HA reference architecture и DR automation;
- tenant isolation design. Только после threat model решить: shared SaaS либо
  сохранить отдельные контуры.

## Метрики продукта

- доля завершённых опросов;
- медианное время заполнения;
- доля успешной доставки отчётов;
- время настройки новой клиники;
- число инцидентов/ручных вмешательств на 1000 опросов;
- restore success rate и фактические RPO/RTO.

Метрики не должны содержать ФИО, контакты, session/deal IDs или свободный текст.
