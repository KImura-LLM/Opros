# 🚀 Информация о работающем сервере «Опросник пациента»

> **Статус:** Проект развёрнут и работает в production  
> **Дата деплоя:** Февраль 2026  
> **Важно:** Все изменения и отладка теперь выполняются **только на сервере**

---

## 📍 Где работает проект

### Основные адреса

| Сервис | URL |
|--------|-----|
| **Сайт опросника** | https://opros-izdorov.ru |
| **Админ-панель** | https://opros-izdorov.ru/admin/ |
| **API Backend** | https://opros-izdorov.ru/api/ |
| **Документация API** | https://opros-izdorov.ru/docs |

### Сервер

| Параметр | Значение |
|----------|----------|
| **Провайдер** | Timeweb Cloud |
| **IP-адрес** | `147.45.249.254` |
| **Домен** | `opros-izdorov.ru` |
| **Операционная система** | Ubuntu (последняя версия) |
| **Рабочая директория** | `/home/deploy/opros` |

---

## 🔐 Данные для доступа

### SSH-доступ к серверу

```bash
ssh deploy@147.45.249.254
u9*_.tnHfoESEt "пароль"
```

**Пароль пользователя `deploy`:** `porol220088`

> ⚠️ **Важно:** Всегда работайте от пользователя `deploy`, а не от `root`!

---

### Админ-панель

**URL:** https://opros-izdorov.ru/admin/

| Поле | Значение |
|------|----------|
| **Логин** | `opros_admin` |
| **Пароль** | `Adm1n_0proS_2026wZ` |

---

### База данных PostgreSQL

| Параметр | Значение |
|----------|----------|
| **Host** | `postgres` (внутри Docker) |
| **Port** | `5432` |
| **Database** | `opros_db` |
| **User** | `opros_user` |
| **Password** | `Pg_secur3_Opr0s_2026xQ` |

**Подключение с сервера:**

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U opros_user -d opros_db
```

---

### Redis

| Параметр | Значение |
|----------|----------|
| **Host** | `redis` (внутри Docker) |
| **Port** | `6379` |
| **Password** | `R3d1s_Secur3_0pr0s_vK` |

**Подключение с сервера:**

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a R3d1s_Secur3_0pr0s_vK
```

---

### Битрикс24 Integration

| Параметр | Значение |
|----------|----------|
| **Webhook URL** | `https://izdorov.bitrix24.ru/rest/217109/z1oeeyul4xht5g33/` |
| **Incoming Token** | `245234asdufhb9oas94` |
| **Category ID** | `19` |

---

## 🛠 Как работать с сервером

### 1. Подключение для отладки

**Подключитесь к серверу:**

```bash
ssh deploy@147.45.249.254
```

**Перейдите в директорию проекта:**

```bash
cd /home/deploy/opros
```

---

### 2. Просмотр логов

**Все логи:**

```bash
docker compose -f docker-compose.prod.yml logs -f
```

**Логи конкретного сервиса:**

```bash
# Backend
docker compose -f docker-compose.prod.yml logs -f backend

# Nginx
docker compose -f docker-compose.prod.yml logs -f nginx

# PostgreSQL
docker compose -f docker-compose.prod.yml logs -f postgres

# Redis
docker compose -f docker-compose.prod.yml logs -f redis
```

---

### 3. Проверка статуса контейнеров

```bash
docker compose -f docker-compose.prod.yml ps
```

**Ожидаемый результат:**

```
NAME                     STATUS              PORTS
opros-nginx              Up                  0.0.0.0:80->80, 0.0.0.0:443->443
opros-backend            Up (healthy)        8000/tcp
opros-postgres           Up (healthy)        5432/tcp
opros-redis              Up (healthy)        6379/tcp
opros-certbot            Up
```

---

### 4. Перезапуск сервисов

**Перезапустить все:**

```bash
docker compose -f docker-compose.prod.yml restart
```

**Перезапустить конкретный сервис:**

```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

### 5. Вход в контейнер для отладки

**Backend:**

```bash
docker compose -f docker-compose.prod.yml exec backend bash
```

**PostgreSQL:**

```bash
docker compose -f docker-compose.prod.yml exec postgres bash
```

**Redis:**

```bash
docker compose -f docker-compose.prod.yml exec redis sh
```

---

### 6. Обновление кода на сервере

> ⚠️ **Внимание:** Для внесения изменений в проект необходимо работать **только на сервере**!

**Шаг 1 — Подключитесь к серверу:**

```bash
ssh deploy@147.45.249.254
cd /home/deploy/opros
```

**Шаг 2 — Если проект на GitHub, обновите код:**

```bash
git pull
```

**Шаг 3 — Пересоберите и перезапустите:**

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**Шаг 4 — Если изменились модели БД, выполните миграции:**

```bash
docker compose -f docker-compose.prod.yml exec -e PYTHONPATH=/app backend alembic upgrade head
```

---

### 7. Проверка здоровья системы

**Backend API:**

```bash
curl -s http://localhost:8000/health
```

**PostgreSQL:**

```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready
```

**Redis:**

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a R3d1s_Secur3_0pr0s_vK ping
```

---

## 🔧 Быстрые команды для отладки

### Просмотр переменных окружения

```bash
cat .env
```

### Проверка конфигурации Nginx

```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Просмотр занятого места

```bash
docker system df
```

### Очистка старых образов и контейнеров

```bash
docker system prune -a
```

### Проверка использования ресурсов

```bash
docker stats
```

---

## ⚠️ Важные напоминания

1. **Все изменения вносятся на сервере** — локальная разработка больше не используется для production.

2. **Не останавливайте контейнеры без необходимости** — это прервёт работу опросника для пациентов.

3. **Перед перезапуском проверьте логи** — чтобы понять причину проблемы.

4. **Бэкапы базы данных** — рекомендуется настроить автоматическое резервное копирование:

   ```bash
   docker compose -f docker-compose.prod.yml exec postgres pg_dump -U opros_user opros_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

5. **SSL-сертификат обновляется автоматически** — Certbot делает это каждые 12 часов.

6. **Мониторинг места на диске:**

   ```bash
   df -h
   ```

---

## 📞 Контакты и ресурсы

| Ресурс | Ссылка |
|--------|--------|
| **Панель Timeweb Cloud** | https://cloud.timeweb.com |
| **Панель Reg.ru (DNS)** | https://reg.ru |
| **Битрикс24** | https://izdorov.bitrix24.ru |
| **GitHub (если используется)** | Ваш репозиторий |

---

## 🚨 Что делать при проблемах

### Сайт не открывается

1. Проверьте статус контейнеров: `docker compose -f docker-compose.prod.yml ps`
2. Проверьте логи Nginx: `docker compose -f docker-compose.prod.yml logs nginx`
3. Проверьте DNS: `nslookup opros-izdorov.ru` (на своём компьютере)

### Ошибка 502 Bad Gateway

1. Backend не отвечает
2. Проверьте: `docker compose -f docker-compose.prod.yml logs backend`
3. Перезапустите: `docker compose -f docker-compose.prod.yml restart backend`

### Ошибка подключения к базе данных

1. Проверьте статус PostgreSQL: `docker compose -f docker-compose.prod.yml ps postgres`
2. Проверьте пароль в `.env`: `grep POSTGRES_PASSWORD .env`
3. Проверьте соединение: `docker compose -f docker-compose.prod.yml exec postgres pg_isready`

### Проблемы с сессиями (пациенты вылетают)

1. Проверьте Redis: `docker compose -f docker-compose.prod.yml logs redis`
2. Проверьте: `docker compose -f docker-compose.prod.yml exec redis redis-cli -a R3d1s_Secur3_0pr0s_vK ping`

---

## 📊 Мониторинг

### Просмотр активных сессий

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a R3d1s_Secur3_0pr0s_vK
# В консоли Redis:
KEYS session:*
```

### Количество записей в БД

```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U opros_user -d opros_db -c "SELECT COUNT(*) FROM sessions;"
docker compose -f docker-compose.prod.yml exec postgres psql -U opros_user -d opros_db -c "SELECT COUNT(*) FROM answers;"
```

---

## 📝 Обновлено

**Дата последнего обновления:** 15 февраля 2026  
**Статус:** Production — Активен ✅
