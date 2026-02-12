# Автоматическое завершение сессий опроса

## Описание

Реализован механизм автоматического завершения неактивных сессий опроса через 2 часа после их создания. Это обеспечивает:

- **Безопасность данных** - своевременная очистка незавершённых сессий
- **Защита от накопления** - предотвращение бесконечного хранения открытых сессий
- **Соответствие требованиям** - соблюдение временных ограничений для медицинских данных

## Как это работает

### 1. Создание сессии

При вызове `POST /api/v1/survey/start` создаётся новая сессия с временем истечения:

```python
expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
```

Клиент получает `expires_at` в ответе:

```json
{
  "session_id": "uuid...",
  "current_node_id": "start",
  "expires_at": "2026-02-12T17:36:03.123456+00:00"
}
```

### 2. Визуальный таймер

На странице опроса отображается обратный отсчёт времени (`SessionTimer` компонент):

- **Зелёный** - более 15 минут до истечения
- **Жёлтый** - от 5 до 15 минут
- **Красный** - менее 5 минут

Формат отображения: `01:45:23` (часы:минуты:секунды)

### 3. Обработка истечения

#### На фронтенде

Когда таймер достигает 00:00:00, срабатывает callback `onExpire`:

```typescript
const handleSessionExpired = () => {
  alert('Время сессии истекло. Опрос будет автоматически завершён.')
  navigate('/')
}
```

#### На бэкенде

**Автоматическая очистка (фоновая задача)**:

- Запускается каждые 15 минут
- Находит все сессии с `expires_at < now()` и статусом `in_progress`
- Переводит их в статус `abandoned`
- Логирует количество закрытых сессий

**Проверка при запросах**:

При попытке отправить ответ на истёкшую сессию:

```python
if session.expires_at and session.expires_at < datetime.now(timezone.utc):
    raise HTTPException(
        status_code=410,  # Gone
        detail="Сессия истекла. Пожалуйста, начните заново."
    )
```

## Структура БД

### Миграция 003

Добавлена колонка `expires_at` в таблицу `survey_sessions`:

```sql
ALTER TABLE survey_sessions 
ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN survey_sessions.expires_at 
IS 'Время автоматического истечения сессии';
```

## Конфигурация

### Изменение времени истечения

Чтобы изменить время автоматического завершения:

**Backend** - [backend/app/api/v1/endpoints/survey.py](backend/app/api/v1/endpoints/survey.py):

```python
# Сессия истекает через X часов
session.expires_at = datetime.now(timezone.utc) + timedelta(hours=X)
```

**Frontend** - [frontend/src/components/layout/SessionTimer.tsx](frontend/src/components/layout/SessionTimer.tsx):

Цветовая кодировка настраивается через пороги:

```typescript
const getTimerColor = () => {
  if (remainingSeconds < 5 * 60) return 'text-red-600'     // < 5 мин
  if (remainingSeconds < 15 * 60) return 'text-yellow-600' // < 15 мин
  return 'text-slate-600'                                   // > 15 мин
}
```

### Интервал фоновой очистки

По умолчанию - каждые 15 минут. Изменить можно в [backend/app/main.py](backend/app/main.py):

```python
while True:
    await cleanup_expired_sessions()
    await asyncio.sleep(15 * 60)  # Изменить здесь
```

## Тестирование

### 1. Ручное тестирование

```bash
# Запустить опрос
curl -X POST http://localhost:8000/api/v1/survey/start \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 123, "patient_name": "Тест"}'

# Проверить expires_at в ответе
# Дождаться истечения времени или изменить в БД

# Попытаться отправить ответ
curl -X POST http://localhost:8000/api/v1/survey/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid...",
    "node_id": "question_1",
    "answer": {"selected": "yes"}
  }'

# Ожидается ответ 410 Gone
```

### 2. Проверка фоновой задачи

```bash
# Проверить логи backend
docker compose logs backend -f | grep "очистка"

# Должны появляться записи каждые 15 минут:
# ⏰ Запущена фоновая задача очистки истёкших сессий (каждые 15 мин)
# ⏰ Фоновая очистка: закрыто сессий - 5
```

### 3. Проверка UI таймера

1. Запустить опрос
2. Проверить отображение таймера в header
3. Убедиться в правильности цветовой кодировки
4. Дождаться истечения и проверить редирект

## API Endpoints

### POST /api/v1/survey/start

**Response** (дополнительное поле):

```json
{
  "expires_at": "2026-02-12T17:36:03.123456+00:00"
}
```

### POST /api/v1/survey/answer

**Новая ошибка**:

```json
{
  "status_code": 410,
  "detail": "Сессия истекла. Пожалуйста, начните заново."
}
```

## Файлы изменений

### Backend

- `backend/app/models/models.py` - добавлено поле `expires_at` в модель `SurveySession`
- `backend/app/schemas/schemas.py` - добавлено поле `expires_at` в схему `SurveyStartResponse`
- `backend/app/api/v1/endpoints/survey.py` - логика проверки истечения
- `backend/app/main.py` - фоновая задача очистки
- `backend/scripts/auto_expire_sessions.py` - скрипт очистки истёкших сессий
- `backend/alembic/versions/2026_02_12_0000-003_add_session_expiry.py` - миграция БД

### Frontend

- `frontend/src/components/layout/SessionTimer.tsx` - новый компонент таймера
- `frontend/src/components/layout/index.ts` - экспорт SessionTimer
- `frontend/src/pages/SurveyPage.tsx` - интеграция таймера, обработка истечения
- `frontend/src/pages/HomePage.tsx` - передача `expires_at` в store
- `frontend/src/store/surveyStore.ts` - добавлено поле `expiresAt`
- `frontend/src/types/survey.ts` - обновлены типы

## Запуск миграции

```bash
# Применить миграцию
docker compose exec backend python -m alembic upgrade head

# Перезапустить backend
docker compose restart backend
```

## Мониторинг

### Проверка статистики через админку

```sql
-- Количество истёкших сессий
SELECT COUNT(*) 
FROM survey_sessions 
WHERE status = 'abandoned' 
  AND expires_at < NOW();

-- Активные сессии близкие к истечению
SELECT id, patient_name, expires_at, 
       expires_at - NOW() as time_left
FROM survey_sessions
WHERE status = 'in_progress'
  AND expires_at < NOW() + INTERVAL '30 minutes'
ORDER BY expires_at;
```

## Возможные улучшения

1. **Предупреждение за N минут** - показать модальное окно "У вас осталось 10 минут"
2. **Продление сессии** - кнопка "Продлить на 1 час"
3. **Настройка через админку** - изменение времени истечения в UI
4. **Отправка уведомлений** - email/SMS перед истечением сессии
5. **Pause/Resume** - возможность приостановить таймер
