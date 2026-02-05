# 🚀 Руководство по деплою PWA "Опросник пациента"

## Содержание

1. [Требования](#требования)
2. [Подготовка сервера](#подготовка-сервера)
3. [Настройка DNS](#настройка-dns)
4. [Конфигурация переменных окружения](#конфигурация-переменных-окружения)
5. [Деплой через CI/CD](#деплой-через-cicd)
6. [Ручной деплой](#ручной-деплой)
7. [Настройка SSL](#настройка-ssl)
8. [Настройка Битрикс24](#настройка-битрикс24)
9. [Мониторинг и логи](#мониторинг-и-логи)
10. [Резервное копирование](#резервное-копирование)
11. [Обновление приложения](#обновление-приложения)
12. [Troubleshooting](#troubleshooting)

---

## Требования

### Минимальные требования к серверу

| Параметр | Значение |
|----------|----------|
| CPU | 2 vCPU |
| RAM | 4 GB |
| Диск | 40 GB SSD |
| ОС | Ubuntu 22.04 LTS |

### Рекомендуемые требования (production)

| Параметр | Значение |
|----------|----------|
| CPU | 4 vCPU |
| RAM | 8 GB |
| Диск | 80 GB SSD |
| ОС | Ubuntu 22.04 LTS |

### Необходимое ПО

- Docker 24.0+
- Docker Compose 2.20+
- Git
- Certbot (для SSL)

---

## Подготовка сервера

### 1. Создание виртуальной машины в Yandex Cloud

```bash
# Через Yandex Cloud CLI
yc compute instance create \
  --name opros-server \
  --zone ru-central1-a \
  --cores 2 \
  --memory 4GB \
  --core-fraction 100 \
  --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=40 \
  --network-interface subnet-name=default-ru-central1-a,nat-ip-version=ipv4 \
  --ssh-key ~/.ssh/id_rsa.pub
```

### 2. Подключение к серверу

```bash
ssh -i ~/.ssh/id_rsa ubuntu@<IP_АДРЕС_СЕРВЕРА>
```

### 3. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 4. Установка Docker

```bash
# Установка зависимостей
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Перезайти в сессию или выполнить
newgrp docker
```

### 5. Проверка Docker

```bash
docker --version
docker compose version
```

### 6. Создание директории проекта

```bash
sudo mkdir -p /opt/opros
sudo chown $USER:$USER /opt/opros
```

### 7. Настройка firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## Настройка DNS

### В Yandex Cloud DNS или у вашего DNS-провайдера

Создайте A-записи:

| Тип | Имя | Значение |
|-----|-----|----------|
| A | opros.yourdomain.ru | IP_СЕРВЕРА |
| A | api.opros.yourdomain.ru | IP_СЕРВЕРА |

Подождите 5-15 минут для распространения DNS.

### Проверка DNS

```bash
nslookup opros.yourdomain.ru
dig opros.yourdomain.ru
```

---

## Конфигурация переменных окружения

### 1. Создание .env файла

```bash
cd /opt/opros
nano .env
```

### 2. Содержимое .env файла

```env
# ============================================
# Общие настройки
# ============================================
ENVIRONMENT=production
DEBUG=false

# ВАЖНО: Сгенерируйте уникальные ключи!
# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=ваш-уникальный-секретный-ключ-минимум-32-символа
JWT_SECRET_KEY=ваш-уникальный-jwt-ключ-минимум-32-символа

# ============================================
# База данных PostgreSQL
# ============================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=opros_user
POSTGRES_PASSWORD=сгенерируйте-сложный-пароль
POSTGRES_DB=opros_db

# ============================================
# Redis
# ============================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=сгенерируйте-пароль-для-redis

# ============================================
# JWT настройки
# ============================================
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=48

# ============================================
# Битрикс24 интеграция
# ============================================
# Получите webhook URL в настройках Битрикс24
BITRIX24_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/1/your-webhook-token/

# ============================================
# CORS и Frontend
# ============================================
CORS_ORIGINS_STR=https://opros.yourdomain.ru
FRONTEND_URL=https://opros.yourdomain.ru

# ============================================
# Админка
# ============================================
ADMIN_USERNAME=admin
ADMIN_PASSWORD=сложный-пароль-для-админки

# ============================================
# Rate Limiting
# ============================================
RATE_LIMIT_PER_MINUTE=60

# ============================================
# Хранение данных (152-ФЗ)
# ============================================
AUDIT_LOG_RETENTION_HOURS=24
DATA_RETENTION_HOURS=24
```

### 3. Генерация безопасных ключей

```bash
# Генерация SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Генерация JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Генерация паролей
openssl rand -base64 24
```

---

## Деплой через CI/CD

### 1. Настройка GitHub Secrets

В репозитории GitHub перейдите в **Settings → Secrets and variables → Actions** и добавьте:

| Secret | Описание |
|--------|----------|
| `SERVER_HOST` | IP-адрес или домен сервера |
| `SERVER_USER` | Пользователь SSH (обычно `ubuntu`) |
| `SERVER_SSH_KEY` | Приватный SSH ключ |
| `DOCKER_REGISTRY` | URL Docker registry (опционально) |
| `DOCKER_USERNAME` | Логин Docker registry (опционально) |
| `DOCKER_PASSWORD` | Пароль Docker registry (опционально) |

### 2. Генерация SSH ключа для деплоя

```bash
# На локальной машине
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Скопировать публичный ключ на сервер
ssh-copy-id -i ~/.ssh/github_deploy.pub ubuntu@<IP_СЕРВЕРА>

# Содержимое приватного ключа добавить в GitHub Secret SERVER_SSH_KEY
cat ~/.ssh/github_deploy
```

### 3. Запуск деплоя

Деплой автоматически запускается при push в ветку `main`:

```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

Или вручную через GitHub Actions:
1. Перейдите в **Actions**
2. Выберите workflow **Deploy**
3. Нажмите **Run workflow**

---

## Ручной деплой

### 1. Клонирование репозитория

```bash
cd /opt/opros
git clone https://github.com/your-username/opros.git .
```

### 2. Копирование конфигурации

```bash
# Убедитесь, что .env файл создан (см. выше)
ls -la .env
```

### 3. Запуск приложения

```bash
# Production сборка и запуск
docker compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker compose -f docker-compose.prod.yml ps

# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f
```

### 4. Применение миграций

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 5. Загрузка начальных данных

```bash
docker compose -f docker-compose.prod.yml exec backend python -m scripts.seed
```

---

## Настройка SSL

### Вариант 1: Certbot (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install -y certbot

# Остановка nginx (если запущен вне Docker)
sudo systemctl stop nginx

# Получение сертификата
sudo certbot certonly --standalone \
  -d opros.yourdomain.ru \
  -d api.opros.yourdomain.ru \
  --email admin@yourdomain.ru \
  --agree-tos \
  --no-eff-email

# Сертификаты будут в:
# /etc/letsencrypt/live/opros.yourdomain.ru/fullchain.pem
# /etc/letsencrypt/live/opros.yourdomain.ru/privkey.pem
```

### Вариант 2: Настройка SSL в Nginx (внутри Docker)

Обновите `nginx/nginx.prod.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name opros.yourdomain.ru;

    ssl_certificate /etc/letsencrypt/live/opros.yourdomain.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/opros.yourdomain.ru/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # ... остальная конфигурация
}

server {
    listen 80;
    server_name opros.yourdomain.ru;
    return 301 https://$server_name$request_uri;
}
```

### Автообновление сертификатов

```bash
# Добавить в crontab
sudo crontab -e

# Добавить строку (обновление каждый день в 3:00)
0 3 * * * certbot renew --quiet --post-hook "docker compose -f /opt/opros/docker-compose.prod.yml restart nginx"
```

---

## Настройка Битрикс24

### 1. Создание входящего вебхука

1. Войдите в Битрикс24
2. Перейдите в **Приложения → Вебхуки → Добавить вебхук**
3. Выберите **Входящий вебхук**
4. Укажите права доступа:
   - `crm` — работа с CRM
   - `crm.timeline.comment` — добавление комментариев
5. Скопируйте URL вебхука

### 2. Формат URL вебхука

```
https://your-domain.bitrix24.ru/rest/1/abc123xyz/
```

Где:
- `your-domain` — ваш домен Битрикс24
- `1` — ID пользователя
- `abc123xyz` — токен вебхука

### 3. Проверка интеграции

```bash
# Тест отправки комментария
curl -X POST "https://your-domain.bitrix24.ru/rest/1/abc123xyz/crm.timeline.comment.add" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "ENTITY_ID": "123",
      "ENTITY_TYPE": "deal",
      "COMMENT": "Тестовый комментарий"
    }
  }'
```

---

## Мониторинг и логи

### Просмотр логов

```bash
# Все сервисы
docker compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f nginx

# Последние 100 строк
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Проверка здоровья сервисов

```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats

# Проверка API
curl -s https://opros.yourdomain.ru/api/v1/health | jq
```

### Настройка cron для очистки данных

```bash
# Открыть crontab
crontab -e

# Добавить задачу очистки (каждый час)
0 * * * * docker compose -f /opt/opros/docker-compose.prod.yml exec -T backend python -m scripts.cleanup >> /var/log/opros-cleanup.log 2>&1
```

### Опционально: Sentry для мониторинга ошибок

1. Зарегистрируйтесь на [sentry.io](https://sentry.io)
2. Создайте проект
3. Добавьте DSN в `.env`:

```env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

---

## Резервное копирование

### Скрипт резервного копирования БД

Создайте файл `/opt/opros/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/opros/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/opros_db_$DATE.sql.gz"

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Создание бэкапа
docker compose -f /opt/opros/docker-compose.prod.yml exec -T postgres \
  pg_dump -U opros_user opros_db | gzip > $BACKUP_FILE

# Удаление бэкапов старше 7 дней
find $BACKUP_DIR -name "opros_db_*.sql.gz" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
```

```bash
chmod +x /opt/opros/scripts/backup.sh
```

### Автоматическое резервное копирование

```bash
# Добавить в crontab (каждый день в 2:00)
crontab -e

0 2 * * * /opt/opros/scripts/backup.sh >> /var/log/opros-backup.log 2>&1
```

### Восстановление из бэкапа

```bash
# Распаковка и восстановление
gunzip -c /opt/opros/backups/opros_db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f /opt/opros/docker-compose.prod.yml exec -T postgres \
  psql -U opros_user opros_db
```

---

## Обновление приложения

### Через CI/CD (рекомендуется)

```bash
git pull origin main
git push origin main
# GitHub Actions автоматически выполнит деплой
```

### Ручное обновление

```bash
cd /opt/opros

# Получить изменения
git pull origin main

# Пересобрать и перезапустить
docker compose -f docker-compose.prod.yml up -d --build

# Применить миграции (если есть)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Проверить статус
docker compose -f docker-compose.prod.yml ps
```

### Откат к предыдущей версии

```bash
# Посмотреть историю
git log --oneline -10

# Откатиться к конкретному коммиту
git checkout <commit-hash>

# Пересобрать
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Troubleshooting

### Проблема: Контейнеры не запускаются

```bash
# Проверить логи
docker compose -f docker-compose.prod.yml logs

# Проверить конфигурацию
docker compose -f docker-compose.prod.yml config

# Перезапустить
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Проблема: Ошибка подключения к БД

```bash
# Проверить статус PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Проверить переменные окружения
docker compose -f docker-compose.prod.yml exec backend env | grep POSTGRES
```

### Проблема: Redis недоступен

```bash
# Проверить статус Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Должен ответить: PONG
```

### Проблема: 502 Bad Gateway

```bash
# Проверить что backend запущен
docker compose -f docker-compose.prod.yml ps backend

# Проверить логи nginx
docker compose -f docker-compose.prod.yml logs nginx

# Проверить логи backend
docker compose -f docker-compose.prod.yml logs backend
```

### Проблема: Ошибки CORS

```bash
# Проверить CORS_ORIGINS_STR в .env
grep CORS .env

# Убедитесь, что указаны правильные домены с https://
```

### Проблема: Сертификат SSL истёк

```bash
# Обновить сертификат
sudo certbot renew

# Перезапустить nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Очистка диска

```bash
# Удалить неиспользуемые Docker ресурсы
docker system prune -a --volumes

# Осторожно! Удалит все остановленные контейнеры и неиспользуемые образы
```

---

## Полезные команды

```bash
# Перезапуск всех сервисов
docker compose -f docker-compose.prod.yml restart

# Перезапуск конкретного сервиса
docker compose -f docker-compose.prod.yml restart backend

# Вход в контейнер
docker compose -f docker-compose.prod.yml exec backend bash

# Выполнение команды в контейнере
docker compose -f docker-compose.prod.yml exec backend python -c "print('Hello')"

# Просмотр переменных окружения
docker compose -f docker-compose.prod.yml exec backend env

# Подключение к БД
docker compose -f docker-compose.prod.yml exec postgres psql -U opros_user opros_db
```

---

## Контакты и поддержка

При возникновении проблем:

1. Проверьте раздел [Troubleshooting](#troubleshooting)
2. Изучите логи: `docker compose -f docker-compose.prod.yml logs`
3. Создайте Issue в GitHub репозитории

---

> **Последнее обновление:** Февраль 2026
