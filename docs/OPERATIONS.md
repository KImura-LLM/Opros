# Эксплуатация Opros

## Production checklist

- [ ] Зафиксирован Git SHA и создан backup.
- [ ] `scripts.preflight` и CI прошли.
- [ ] Изменения миграций просмотрены, время/lock impact оценены.
- [ ] Есть rollback/stop criteria и ответственный.
- [ ] Нет секретов/ПДн в diff и логах.
- [ ] После обновления проверяются liveness, readiness и синтетический опрос.

## Health и мониторинг

- `/health/live` — процесс отвечает; используйте для container liveness.
- `/health/ready` — доступны PostgreSQL и Redis; используйте для снятия из балансировки.
- Сигналы для alerting: доля 5xx, p95/p99 API latency, readiness failures,
  возраст pending AI jobs, ошибки Bitrix delivery, место диска и успешность backup.
- Не используйте patient/session/deal ID как metric labels и не отправляйте body
  запросов в telemetry.

Health workers в Compose подтверждает только существование процесса, а не
бизнес-успех. Для worker SLA нужен отдельный монитор очереди/последнего успешного
запуска.

## Backup

Пример логического backup:

```bash
mkdir -p backups
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "backups/opros-$(date +%F-%H%M).dump"
```

Требования:

- шифрование в покое и при передаче;
- копия вне production-хоста;
- retention утверждён владельцем данных;
- контроль доступа и журнал скачиваний;
- регулярная restore-репетиция.

## Restore

Restore выполнять сначала на изолированной среде:

```bash
cat backups/opros-YYYY-MM-DD-HHMM.dump | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

После restore применить Alembic migration, проверить readiness и синтетический
опрос. Команда `--clean` разрушительна: не выполнять против production без
утверждённого recovery-плана.

## Обновление

```bash
git fetch origin
git checkout <approved-sha>
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl --fail https://your-domain.example/health/ready
```

Compose сначала выполняет preflight и миграции. Для несовместимой миграции нужен
отдельный expand/migrate/contract релиз, а не автоматический downgrade.

## Rollback

1. Остановить переключение при readiness failure, росте 5xx или нарушении отчётов.
2. Сохранить логи без ПДн и состояние контейнеров.
3. Вернуть предыдущий проверенный Git SHA и образы.
4. Не выполнять Alembic downgrade автоматически. Восстановить БД из backup, если
   новая схема несовместима.
5. Повторить smoke test.

## Инциденты

- Скомпрометированный секрет: отозвать/сменить его, перезапустить затронутые
  сервисы, проверить журналы доступа.
- Недоступен Bitrix/OpenRouter: patient flow не должен терять локальный snapshot;
  проверить retry/fail queue.
- Недоступен Redis: readiness становится 503; rate limit работает fail-open —
  Nginx rate limiting должен оставаться включён.
- Утечка ПДн: прекратить распространение логов, сохранить forensic evidence и
  действовать по утверждённому юридическому плану уведомлений.
