# Установка Opros

## 1. Модель поставки

Для первого коммерческого релиза используйте **отдельный инстанс на одну
клинику**. Это изолирует данные и настройки и не требует небезопасной имитации
multi-tenancy.

## 2. Требования

- Linux x86_64, 4 vCPU, 8 ГБ RAM, 40 ГБ SSD как стартовая конфигурация;
- Docker Engine и Docker Compose v2;
- домен и DNS A/AAAA;
- открытые 80/443, закрытые снаружи PostgreSQL и Redis;
- внешний backup storage, не расположенный на том же сервере;
- SMTP/monitoring/Bitrix24/OpenRouter — только если соответствующая функция нужна.

Размеры ресурсов являются стартовыми, а не SLA: перед договором нужна нагрузочная
проверка на ожидаемом количестве одновременных пациентов и размере отчётов.

## 3. Подготовка

```bash
git clone <customer-repository-url> opros
cd opros
cp .env.example .env
chmod 600 .env
```

Сгенерируйте каждое секретное значение независимо:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Обязательные решения до запуска:

1. публичный `FRONTEND_URL` и точный `CORS_ORIGINS_STR`;
2. отдельные `SECRET_KEY`, `JWT_SECRET_KEY`, пароли PostgreSQL/Redis/admin;
3. Bitrix24 URL, входящий токен, воронки и поле ссылки;
4. сроки хранения и процесс удаления данных;
5. включать ли AI. По умолчанию он выключен.

Никогда не вставляйте секреты в тикеты, логи или сообщения поддержки.

## 4. Проверка конфигурации

```bash
docker compose --env-file .env -f docker-compose.prod.yml config -q
docker compose -f docker-compose.prod.yml run --rm migrate python -m scripts.preflight
```

Preflight должен завершиться `Production preflight: OK`. Warning об отключённой
интеграции допустим только когда это осознанное решение.

## 5. TLS

Production Nginx ожидает сертификаты в `certbot/conf`. Получите сертификат
утверждённым для инфраструктуры заказчика способом до переключения трафика.
Не запускайте медицинский production по HTTP.

## 6. Первый запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl --fail https://your-domain.example/health/live
curl --fail https://your-domain.example/health/ready
```

`migrate` является одноразовым сервисом: успешный статус `Exited (0)` ожидаем.
Frontend builder также завершает работу после копирования статических файлов.

## 7. Первичная настройка

1. Войти в `/admin` и сразу проверить учётные данные.
2. Импортировать/активировать версию опросника.
3. Настроить routing и clinic bucket.
4. Создать врачей с минимально необходимыми правами.
5. Выполнить тестовый Bitrix webhook на тестовой сделке без реального пациента.
6. Пройти анкету синтетического пациента и проверить HTML/TXT/PDF.
7. Убедиться, что AI выключен либо получает только утверждённый обезличенный payload.

## 8. Приёмочные критерии

- `/health/ready` возвращает 200;
- миграции находятся на head;
- тестовый опрос завершается, snapshot воспроизводится;
- отчёт доступен только авторизованным ролям;
- в логах отсутствуют ФИО, контакты, IP, Bitrix/session IDs и токены;
- backup создан, restore отрепетирован на отдельной среде;
- rollback SHA и ответственный за переключение записаны.
