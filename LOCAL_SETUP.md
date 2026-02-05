# 📖 Инструкция по локальному запуску проекта

## 🚀 Запуск проекта

### 1. Предварительные требования

Убедитесь, что установлены:
- **Docker** (версия 24.0+)
- **Docker Compose** (версия 2.20+)
- **Git**

```bash
# Проверка версий
docker --version
docker compose version
```

### 2. Клонирование и настройка

```bash
# Клонировать репозиторий
git clone <url-репозитория>
cd Opros

# Создать файл .env (если ещё не создан)
cp .env.example .env
# или отредактировать существующий .env
```

### 3. Настройка переменных окружения

Отредактируйте `.env` файл. Для локальной разработки можно оставить значения по умолчанию:

```env
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-super-secret-key-change-in-production
POSTGRES_PASSWORD=your-strong-password-here
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
```

### 4. Запуск контейнеров

```bash
# Сборка и запуск всех сервисов в фоновом режиме
docker compose up -d --build
```

### 5. Проверка статуса

```bash
# Проверить что все контейнеры запущены
docker compose ps
```

Ожидаемый вывод:
```
NAME              STATUS
opros-backend     running (healthy)
opros-frontend    running
opros-postgres    running (healthy)
opros-redis       running (healthy)
```

### 6. Применение миграций и загрузка данных (первый запуск)

```bash
# Применить миграции базы данных
docker compose exec backend alembic upgrade head

# Загрузить начальные данные (структуру опросника)
docker compose exec backend python -m scripts.seed
```

### 7. Открытие приложения

| Сервис | URL |
|--------|-----|
| 🌐 Frontend | http://localhost:5173 |
| 🐍 Backend API | http://localhost:8000 |
| 📚 API Docs (Swagger) | http://localhost:8000/docs |
| 📖 API Docs (ReDoc) | http://localhost:8000/redoc |
| 👤 Админ-панель | http://localhost:8000/admin |

---

## 🛑 Остановка проекта

### Вариант 1: Остановка с сохранением данных (рекомендуется)

```bash
# Остановить все контейнеры, сохранив volumes (данные БД и Redis)
docker compose down
```

### Вариант 2: Полная очистка (удаление данных)

```bash
# Остановить контейнеры И удалить volumes (все данные будут потеряны!)
docker compose down -v
```

### Вариант 3: Остановка отдельного сервиса

```bash
# Остановить только backend
docker compose stop backend

# Запустить обратно
docker compose start backend
```

---

## 🔄 Полезные команды для разработки

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f backend
docker compose logs -f frontend
```

### Перезапуск сервисов

```bash
# Перезапустить все
docker compose restart

# Перезапустить один сервис
docker compose restart backend
```

### Пересборка после изменений

```bash
# Пересобрать и перезапустить
docker compose up -d --build

# Пересобрать конкретный сервис
docker compose up -d --build backend
```

### Вход в контейнер

```bash
# Backend (Python)
docker compose exec backend bash

# База данных (PostgreSQL)
docker compose exec postgres psql -U opros_user opros_db

# Redis
docker compose exec redis redis-cli
```

### Генерация тестового токена

```bash
# Через curl (Linux/macOS)
curl -X POST "http://localhost:8000/api/v1/auth/generate-token?lead_id=123&patient_name=Иван"

# Через PowerShell (Windows)
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/auth/generate-token?lead_id=123&patient_name=Иван"
```

---

## ⚠️ Типичные проблемы и решения

### Порт занят

```bash
# Windows PowerShell - проверить что занимает порт
netstat -ano | findstr :5173
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :5173
lsof -i :8000
```

**Решение:** Остановите процесс, занимающий порт, или измените порты в `docker-compose.yml`.

### Контейнер не запускается

```bash
# Посмотреть логи конкретного контейнера
docker compose logs backend

# Проверить конфигурацию
docker compose config
```

### Проблемы с базой данных

```bash
# Пересоздать БД (данные будут удалены!)
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed
```

### Docker не запущен

**Windows:** Убедитесь, что Docker Desktop запущен (иконка в трее).

**Linux:** 
```bash
sudo systemctl start docker
```

### Ошибки при сборке образов

```bash
# Очистить кэш Docker и пересобрать
docker compose build --no-cache
docker compose up -d
```

---

## 📋 Краткая шпаргалка

| Действие | Команда |
|----------|---------|
| Запуск | `docker compose up -d --build` |
| Остановка | `docker compose down` |
| Логи | `docker compose logs -f` |
| Статус | `docker compose ps` |
| Перезапуск | `docker compose restart` |
| Полная очистка | `docker compose down -v` |
