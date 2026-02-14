# Полная инструкция по деплою "Опросник пациента" на сервер

## Оглавление

1. [Выбор сервера](#1-выбор-сервера)
2. [Покупка и настройка VPS](#2-покупка-и-настройка-vps)
3. [Первое подключение к серверу](#3-первое-подключение-к-серверу)
4. [Настройка безопасности сервера](#4-настройка-безопасности-сервера)
5. [Установка Docker](#5-установка-docker)
6. [Покупка домена](#6-покупка-домена)
7. [Загрузка проекта на сервер](#7-загрузка-проекта-на-сервер)
8. [Настройка переменных окружения](#8-настройка-переменных-окружения)
9. [Настройка Nginx под ваш домен](#9-настройка-nginx-под-ваш-домен)
10. [Получение SSL-сертификата](#10-получение-ssl-сертификата)
11. [Запуск проекта](#11-запуск-проекта)
12. [Проверка работоспособности](#12-проверка-работоспособности)
13. [Обновление проекта](#13-обновление-проекта)
14. [Решение проблем](#14-решение-проблем)

---

## 1. Выбор сервера

### Рекомендуемый хостинг: Timeweb Cloud

**Почему Timeweb Cloud:**
- Российская компания, серверы расположены в России (Москва, Санкт-Петербург)
- Полностью русскоязычный интерфейс и поддержка
- Отличное соотношение цена/качество
- Простой и понятный интерфейс для новичков
- Оплата в рублях (карты РФ, ЮMoney, СБП)
- Соответствует требованиям 152-ФЗ (персональные данные на территории РФ)

**Сайт:** https://timeweb.cloud

### Рекомендуемая конфигурация сервера

Для вашего проекта (FastAPI + React + PostgreSQL + Redis + Nginx) нужен:

| Параметр | Минимум | Рекомендуемое |
|----------|---------|---------------|
| CPU | 2 vCPU | 2 vCPU |
| RAM | 2 ГБ | 4 ГБ |
| Диск | 30 ГБ NVMe | 50 ГБ NVMe |
| ОС | Ubuntu 22.04 | Ubuntu 22.04 |
| Трафик | Безлимит | Безлимит |

**Примерная стоимость:** 600–900 ₽/мес (тариф "Cloud 4" или аналогичный)

> **Альтернативные хостинги (если Timeweb не подходит):**
> - **Selectel** (selectel.ru) — более корпоративный, дороже, но очень надёжный
> - **Reg.ru VPS** (reg.ru) — популярный регистратор доменов с VPS
> - **FirstVDS** (firstvds.ru) — бюджетный вариант

---

## 2. Покупка и настройка VPS

### Шаг 2.1 — Регистрация на Timeweb Cloud

1. Откройте браузер и перейдите на **https://timeweb.cloud**
2. Нажмите кнопку **"Регистрация"** в правом верхнем углу
3. Заполните форму:
   - Введите ваш **email**
   - Придумайте **пароль**
   - Нажмите **"Зарегистрироваться"**
4. Подтвердите email, перейдя по ссылке в письме

### Шаг 2.2 — Создание сервера (VPS)

1. После входа в панель управления, в левом меню нажмите **"Облачные серверы"**
2. Нажмите кнопку **"Создать"** (большая синяя кнопка)
3. **Выбор ОС:** 
   - Нажмите на вкладку **"Операционная система"**
   - Выберите **Ubuntu 22.04 LTS** (нажмите на неё, чтобы она подсветилась)
4. **Выбор конфигурации:**
   - Прокрутите вниз до раздела **"Конфигурация"**
   - Выберите тариф с **2 vCPU, 4 ГБ RAM, 50 ГБ NVMe**
   - Это примерно 700–900 ₽/мес
5. **Регион:**
   - Выберите **Москва** или **Санкт-Петербург** (что ближе к вашим пользователям)
6. **Имя сервера:**
   - Введите понятное имя, например: `opros-production`
7. **SSH-ключ (рекомендуется, но опционально):**
   - Если у вас есть SSH-ключ, загрузите его (мы рассмотрим оба варианта подключения)
   - Если нет — пропустите, будете подключаться по паролю
8. Нажмите **"Создать сервер"**
9. **Дождитесь создания** — обычно 1-2 минуты
10. После создания вы увидите:
    - **IP-адрес** сервера (например: `185.104.xxx.xxx`)
    - **Пароль root** (придёт на email или отобразится в панели)

> **ВАЖНО:** Запишите IP-адрес и пароль — они понадобятся для подключения!

### Шаг 2.3 — Пополнение баланса

1. В панели управления нажмите на **иконку кошелька** или **"Баланс"** в верхнем меню
2. Выберите способ оплаты:
   - **Банковская карта** (Visa, MasterCard, МИР)
   - **СБП** (Система быстрых платежей)
   - **ЮMoney**
3. Пополните на нужную сумму (минимум на 1 месяц)

---

## 3. Первое подключение к серверу

### Вариант A: Подключение с Windows через PowerShell (встроенный SSH-клиент)

Windows 10/11 уже имеет встроенный SSH-клиент:

1. Откройте **PowerShell** (нажмите `Win + X`, выберите **"Windows PowerShell"** или **"Терминал"**)
2. Введите команду подключения (замените IP на ваш):

```bash
ssh root@ВАШ_IP_АДРЕС
```

Например:
```bash
ssh root@185.104.123.456
```

3. При первом подключении появится вопрос:
```
The authenticity of host '185.104.123.456' can't be established.
Are you sure you want to continue connecting (yes/no)?
```
Введите **yes** и нажмите **Enter**

4. Введите **пароль** (символы при вводе не отображаются — это нормально!) и нажмите **Enter**

5. Если видите приглашение вида `root@opros-production:~#` — вы подключены!

### Вариант B: Подключение через PuTTY (альтернатива)

1. Скачайте **PuTTY** с официального сайта: https://www.putty.org/
2. Запустите PuTTY
3. В поле **"Host Name (or IP address)"** введите IP вашего сервера
4. Порт: **22** (по умолчанию)
5. Тип подключения: **SSH**
6. Нажмите **"Open"**
7. В появившемся окне:
   - Login: **root**
   - Password: **(ваш пароль)**

### Вариант C: Подключение через терминал Cursor IDE

Можно подключиться прямо из Cursor:
1. Откройте терминал в Cursor (`Ctrl + Ё` или `Ctrl + ~`)
2. Введите:
```bash
ssh root@ВАШ_IP_АДРЕС
```

---

## 4. Настройка безопасности сервера

> Все команды ниже выполняются **на сервере** (после подключения по SSH).

### Шаг 4.1 — Обновление системы

```bash
apt update && apt upgrade -y
```

Эта команда:
- `apt update` — обновляет список доступных пакетов
- `apt upgrade -y` — устанавливает все обновления (`-y` значит "да" на все вопросы)

Подождите завершения (1-3 минуты).

### Шаг 4.2 — Создание нового пользователя (не работать от root!)

```bash
adduser deploy
```

Система попросит:
- **Enter new UNIX password:** — придумайте надёжный пароль и введите его
- **Retype new UNIX password:** — повторите пароль
- Остальные поля (Full Name, Room Number и т.д.) — просто нажимайте **Enter**, чтобы пропустить
- **Is the information correct? [Y/n]** — нажмите **Y** и **Enter**

Теперь дайте пользователю права администратора:
```bash
usermod -aG sudo deploy
```

### Шаг 4.3 — Настройка файрвола (UFW)

```bash
# Установить файрвол (обычно уже установлен)
apt install ufw -y

# Разрешить SSH (чтобы не потерять доступ!)
ufw allow 22/tcp

# Разрешить HTTP и HTTPS (для сайта)
ufw allow 80/tcp
ufw allow 443/tcp

# Включить файрвол
ufw enable
```

При вопросе `Command may disrupt existing SSH connections. Proceed with operation (y|n)?` введите **y**.

Проверьте статус:
```bash
ufw status
```

Вы должны увидеть:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### Шаг 4.4 — Переключение на нового пользователя

```bash
su - deploy
```

Теперь вы работаете от имени пользователя `deploy`. Приглашение сменится на `deploy@opros-production:~$`.

---

## 5. Установка Docker

> Все команды выполняются от пользователя `deploy` (используйте `sudo` перед командами).

### Шаг 5.1 — Установка Docker Engine

Выполните команды **по одной** (копируйте каждую строку отдельно):

```bash
# 1. Установка необходимых пакетов
sudo apt install -y ca-certificates curl gnupg lsb-release

# 2. Добавление GPG-ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 3. Добавление репозитория Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Обновление списка пакетов
sudo apt update

# 5. Установка Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### Шаг 5.2 — Добавление пользователя в группу Docker

Чтобы не писать `sudo` перед каждой командой Docker:

```bash
sudo usermod -aG docker deploy
```

**ВАЖНО:** Чтобы изменения вступили в силу, нужно перелогиниться:

```bash
# Выйти
exit

# Снова войти под deploy
su - deploy
```

### Шаг 5.3 — Проверка установки

```bash
docker --version
docker compose version
```

Вы должны увидеть что-то вроде:
```
Docker version 27.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

Проверим, что Docker работает:
```bash
docker run hello-world
```

Если видите сообщение `Hello from Docker!` — всё работает!

### Шаг 5.4 — Установка Git

```bash
sudo apt install -y git
git --version
```

---

## 6. Покупка домена

Для работы SSL-сертификата (HTTPS) вам нужен домен. 

### Где купить домен

Рекомендуемые регистраторы:
1. **Reg.ru** (reg.ru) — самый популярный в России
2. **Timeweb** (timeweb.com/ru/services/domains) — удобно если сервер тоже тут
3. **RU-CENTER** (nic.ru) — старейший регистратор

### Шаг 6.1 — Покупка домена (пример на Reg.ru)

1. Перейдите на **https://reg.ru**
2. В поисковую строку введите желаемое имя домена, например: `opros-clinic.ru`
3. Нажмите **"Проверить"**
4. Если домен свободен — нажмите **"Добавить в корзину"**
   - Зоны `.ru` стоят ~200-300 ₽/год
   - Зоны `.рф` стоят ~200-300 ₽/год
5. Перейдите в корзину и оформите заказ
6. Оплатите домен

### Шаг 6.2 — Привязка домена к серверу (настройка DNS)

После покупки домена нужно указать, что он ведёт на ваш сервер:

1. Войдите в **личный кабинет** Reg.ru (или вашего регистратора)
2. Перейдите в раздел **"Мои домены"**
3. Нажмите на ваш домен
4. Найдите раздел **"DNS-серверы"** или **"Управление DNS"**
5. Перейдите в **"Управление DNS-записями"** (или "Resource records")
6. Создайте/измените **A-запись**:
   - **Тип:** A
   - **Имя:** `@` (или оставьте пустым — это корневой домен)
   - **Значение:** `ВАШ_IP_АДРЕС` (IP сервера, например `185.104.123.456`)
   - **TTL:** 3600 (или оставьте по умолчанию)
7. Нажмите **"Сохранить"**

> **ВАЖНО:** DNS-записи обновляются не мгновенно! Обычно от 15 минут до 24 часов.
> Чаще всего — 30-60 минут.

### Шаг 6.3 — Проверка DNS

Через 15-30 минут проверьте, что домен указывает на ваш сервер. 
На **вашем компьютере** (не на сервере) откройте PowerShell и введите:

```bash
nslookup ваш-домен.ru
```

Если в ответе вы видите IP вашего сервера — DNS настроен!

> **Если у вас пока нет домена** — можно временно работать по IP-адресу (без HTTPS).
> Инструкция по этому варианту — в разделе "Решение проблем".

---

## 7. Загрузка проекта на сервер

У вас есть два способа. Рекомендуется **Способ A** (через Git).

### Способ A: Через Git (рекомендуемый)

#### Шаг 7.1 — Загрузка проекта на GitHub/GitLab

Если проект ещё не на GitHub:

**На вашем компьютере** (в PowerShell/терминале Cursor):

```bash
cd C:\Users\Nikola\Documents\Project\Opros

# Если ещё не инициализирован Git
git init
git add .
git commit -m "Initial commit for production deploy"

# Создайте репозиторий на GitHub (github.com -> New Repository)
# Затем подключите его:
git remote add origin https://github.com/ВАШ_ЛОГИН/opros.git
git branch -M main
git push -u origin main
```

> **Если репозиторий приватный** (рекомендуется!), вам понадобится Personal Access Token.
> На GitHub: Settings → Developer settings → Personal access tokens → Generate new token.

#### Шаг 7.2 — Клонирование проекта на сервер

**На сервере** (подключитесь по SSH):

```bash
# Перейти в домашнюю директорию
cd /home/deploy

# Клонировать проект
git clone https://github.com/ВАШ_ЛОГИН/opros.git

# Перейти в папку проекта
cd opros
```

Если репозиторий приватный, Git попросит ввести логин и пароль (используйте Token вместо пароля).

### Способ B: Через SCP (прямое копирование файлов)

Если не хотите использовать Git, можно скопировать файлы напрямую.

**На вашем компьютере** (в PowerShell):

```bash
# Копирование всей папки проекта на сервер
scp -r C:\Users\Nikola\Documents\Project\Opros deploy@ВАШ_IP:/home/deploy/opros
```

> **Примечание:** Это может занять несколько минут в зависимости от размера проекта и скорости интернета.

---

## 8. Настройка переменных окружения

### Шаг 8.1 — Создание production .env файла

**На сервере**, перейдите в папку проекта и создайте `.env` файл:

```bash
cd /home/deploy/opros
nano .env
```

> **Как пользоваться nano (текстовый редактор):**
> - Просто печатайте текст, как в блокноте
> - Стрелки — перемещение курсора
> - `Ctrl + O` → нажмите `Enter` — сохранить файл
> - `Ctrl + X` — выйти из редактора

### Шаг 8.2 — Вставьте содержимое .env файла

Скопируйте и вставьте следующее (в терминале: правая кнопка мыши для вставки):

```env
# ============================================
# PRODUCTION - Переменные окружения
# ============================================

# Общие настройки
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=ЗАМЕНИТЕ_НА_ДЛИННУЮ_СЛУЧАЙНУЮ_СТРОКУ_1

# База данных PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=opros_user
POSTGRES_PASSWORD=ЗАМЕНИТЕ_НА_НАДЕЖНЫЙ_ПАРОЛЬ_БД
POSTGRES_DB=opros_db
DATABASE_URL=postgresql+asyncpg://opros_user:ЗАМЕНИТЕ_НА_НАДЕЖНЫЙ_ПАРОЛЬ_БД@postgres:5432/opros_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=ЗАМЕНИТЕ_НА_ПАРОЛЬ_REDIS
REDIS_URL=redis://:ЗАМЕНИТЕ_НА_ПАРОЛЬ_REDIS@redis:6379/0
SESSION_TTL=86400

# JWT
JWT_SECRET_KEY=ЗАМЕНИТЕ_НА_ДЛИННУЮ_СЛУЧАЙНУЮ_СТРОКУ_2
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=48

# Битрикс24
BITRIX24_WEBHOOK_URL=https://izdorov.bitrix24.ru/rest/217109/z1oeeyul4xht5g33/
BITRIX24_INCOMING_TOKEN=245234asdufhb9oas94
BITRIX24_CATEGORY_ID=19

# CORS и домены (ЗАМЕНИТЕ на ваш домен!)
CORS_ORIGINS_STR=https://ВАШ-ДОМЕН.ru
FRONTEND_URL=https://ВАШ-ДОМЕН.ru

# Админ-панель (ОБЯЗАТЕЛЬНО измените пароль!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ЗАМЕНИТЕ_НА_НАДЕЖНЫЙ_ПАРОЛЬ_АДМИНА

# Безопасность
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_RETENTION_HOURS=24

# Docker
COMPOSE_PROJECT_NAME=opros
```

### Шаг 8.3 — Генерация надёжных паролей и ключей

**ВАЖНО:** Не используйте примеры выше дословно! Сгенерируйте настоящие пароли.

Для генерации случайных строк выполните на сервере:

```bash
# Генерация SECRET_KEY (32 символа)
openssl rand -hex 32

# Генерация JWT_SECRET_KEY (32 символа)
openssl rand -hex 32

# Генерация пароля БД (20 символов)
openssl rand -base64 20

# Генерация пароля Redis (20 символов)
openssl rand -base64 20

# Генерация пароля админки (16 символов)
openssl rand -base64 16
```

Каждая команда выдаст случайную строку — скопируйте их и подставьте в `.env` файл.

### Шаг 8.4 — Проверка .env файла

Убедитесь, что все значения заменены:

```bash
# Показать .env файл (проверить глазами)
cat .env

# Проверить, что нет "ЗАМЕНИТЕ" в файле
grep "ЗАМЕНИТЕ" .env
```

Если `grep` ничего не вывел — все значения заменены!

> **ВНИМАНИЕ:** В значении `DATABASE_URL` пароль должен совпадать с `POSTGRES_PASSWORD`!
> В значении `REDIS_URL` пароль должен совпадать с `REDIS_PASSWORD`!

---

## 9. Настройка Nginx под ваш домен

### Шаг 9.1 — Изменить конфигурацию Nginx

```bash
nano nginx/conf.d/default.conf
```

Найдите строки (используйте `Ctrl + W` для поиска в nano):
```
server_name _;
```

Замените **обе** строки `server_name _;` на:
```
server_name ВАШ-ДОМЕН.ru;
```

Также найдите строки с SSL-сертификатами:
```
ssl_certificate /etc/letsencrypt/live/your-domain.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.ru/privkey.pem;
```

Замените `your-domain.ru` на ваш реальный домен:
```
ssl_certificate /etc/letsencrypt/live/ВАШ-ДОМЕН.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ВАШ-ДОМЕН.ru/privkey.pem;
```

Сохраните: `Ctrl + O` → `Enter` → `Ctrl + X`

---

## 10. Получение SSL-сертификата

SSL-сертификат нужен для HTTPS (защищённое соединение). Мы используем **бесплатный** сертификат от Let's Encrypt.

### Шаг 10.1 — Временная конфигурация Nginx (только HTTP)

Сначала нужно запустить Nginx только с HTTP, чтобы Let's Encrypt мог проверить владение доменом.

Создайте временный конфиг:

```bash
# Сохранить оригинальный конфиг
cp nginx/conf.d/default.conf nginx/conf.d/default.conf.backup

# Создать временный конфиг (только HTTP)
cat > nginx/conf.d/default.conf << 'NGINX_TEMP'
server {
    listen 80;
    listen [::]:80;
    server_name ВАШ-ДОМЕН.ru;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Server is running';
        add_header Content-Type text/plain;
    }
}
NGINX_TEMP
```

> **ВАЖНО:** Замените `ВАШ-ДОМЕН.ru` на ваш реальный домен в команде выше!

### Шаг 10.2 — Создать директории для Certbot

```bash
mkdir -p certbot/conf
mkdir -p certbot/www
```

### Шаг 10.3 — Запустить Nginx временно

```bash
# Запустить только Nginx (без backend и БД)
docker compose -f docker-compose.prod.yml up -d nginx
```

> Если появится ошибка о frontend_build volume — это нормально на первом запуске.
> Выполните:
> ```bash
> docker volume create opros_frontend_build
> docker compose -f docker-compose.prod.yml up -d nginx
> ```

Проверить, что Nginx работает:
```bash
docker ps
```

Вы должны увидеть контейнер `opros-nginx` со статусом `Up`.

### Шаг 10.4 — Получить SSL-сертификат

```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email ваш-email@mail.ru \
  --agree-tos \
  --no-eff-email \
  -d ВАШ-ДОМЕН.ru
```

> **Замените:**
> - `ваш-email@mail.ru` — на ваш реальный email (для уведомлений об истечении сертификата)
> - `ВАШ-ДОМЕН.ru` — на ваш реальный домен

Если всё прошло успешно, вы увидите:
```
Congratulations! Your certificate and chain have been saved at:
/etc/letsencrypt/live/ВАШ-ДОМЕН.ru/fullchain.pem
```

### Шаг 10.5 — Восстановить полный конфиг Nginx

```bash
# Вернуть оригинальный конфиг
cp nginx/conf.d/default.conf.backup nginx/conf.d/default.conf

# Остановить временный Nginx
docker compose -f docker-compose.prod.yml down
```

---

## 11. Запуск проекта

### Шаг 11.1 — Сборка и запуск всех сервисов

```bash
cd /home/deploy/opros

# Сборка всех Docker-образов и запуск
docker compose -f docker-compose.prod.yml up -d --build
```

Эта команда:
- `-f docker-compose.prod.yml` — использует production-конфигурацию
- `up` — запускает все сервисы
- `-d` — в фоновом режиме (detached)
- `--build` — пересобирает образы

**Первая сборка займёт 3-10 минут** (скачивание базовых образов + сборка).

### Шаг 11.2 — Проверка статуса контейнеров

```bash
docker compose -f docker-compose.prod.yml ps
```

Все контейнеры должны иметь статус **"Up"** (или "Up (healthy)"):

```
NAME                    STATUS              PORTS
opros-nginx             Up                  0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
opros-backend           Up (healthy)        8000/tcp
opros-postgres          Up (healthy)        5432/tcp
opros-redis             Up (healthy)        6379/tcp
opros-frontend-builder  Up
opros-certbot           Up
```

### Шаг 11.3 — Выполнение миграций базы данных

```bash
# Запуск миграций Alembic
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Эта команда:
- `exec backend` — выполняет команду внутри контейнера backend
- `alembic upgrade head` — применяет все миграции базы данных

Вы должны увидеть:
```
INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, Initial migration
INFO  [alembic.runtime.migration] Running upgrade xxxx -> yyyy, ...
```

### Шаг 11.4 — Проверка логов (если что-то пошло не так)

```bash
# Логи всех сервисов
docker compose -f docker-compose.prod.yml logs

# Логи конкретного сервиса (например, backend)
docker compose -f docker-compose.prod.yml logs backend

# Логи в реальном времени (следить за ошибками)
docker compose -f docker-compose.prod.yml logs -f backend

# Выход из режима просмотра логов: Ctrl + C
```

---

## 12. Проверка работоспособности

### Шаг 12.1 — Проверка через браузер

1. Откройте браузер на вашем компьютере
2. Перейдите по адресу: **https://ВАШ-ДОМЕН.ru**
3. Вы должны увидеть интерфейс опросника

### Шаг 12.2 — Проверка API

```bash
# На сервере — проверка здоровья backend
curl http://localhost:8000/health

# Или через домен
curl https://ВАШ-ДОМЕН.ru/api/v1/health
```

### Шаг 12.3 — Проверка админ-панели

1. Откройте в браузере: **https://ВАШ-ДОМЕН.ru/admin/**
2. Введите логин и пароль, которые указали в `.env`:
   - **Username:** admin (или что указали в `ADMIN_USERNAME`)
   - **Password:** (пароль из `ADMIN_PASSWORD`)

### Шаг 12.4 — Проверка всех компонентов

```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Проверка PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Проверка Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

Ожидаемые ответы:
- PostgreSQL: `/var/run/postgresql:5432 - accepting connections`
- Redis: `PONG`

---

## 13. Обновление проекта

Когда вы внесли изменения в код и хотите обновить сервер:

### Вариант A: Через Git (рекомендуемый)

**На вашем компьютере:**
```bash
git add .
git commit -m "описание изменений"
git push
```

**На сервере:**
```bash
cd /home/deploy/opros

# Получить новый код
git pull

# Пересобрать и перезапустить
docker compose -f docker-compose.prod.yml up -d --build

# Если изменились модели БД — запустить миграции
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Вариант B: Обновление только backend

```bash
docker compose -f docker-compose.prod.yml up -d --build backend
```

### Вариант C: Обновление только frontend

```bash
# Удалить старую сборку
docker volume rm opros_frontend_build

# Пересобрать frontend
docker compose -f docker-compose.prod.yml up -d --build frontend-builder

# Перезапустить Nginx (чтобы подхватил новую сборку)
docker compose -f docker-compose.prod.yml restart nginx
```

---

## 14. Решение проблем

### Проблема: Контейнер не запускается

```bash
# Посмотреть логи проблемного контейнера
docker compose -f docker-compose.prod.yml logs backend

# Перезапустить конкретный сервис
docker compose -f docker-compose.prod.yml restart backend
```

### Проблема: Ошибка 502 Bad Gateway

Это значит Nginx не может подключиться к backend:
```bash
# Проверить, запущен ли backend
docker compose -f docker-compose.prod.yml ps backend

# Посмотреть логи backend
docker compose -f docker-compose.prod.yml logs backend

# Перезапустить
docker compose -f docker-compose.prod.yml restart backend
```

### Проблема: Ошибка подключения к базе данных

```bash
# Проверить статус PostgreSQL
docker compose -f docker-compose.prod.yml logs postgres

# Проверить что пароль в DATABASE_URL совпадает с POSTGRES_PASSWORD
grep POSTGRES_PASSWORD .env
grep DATABASE_URL .env
```

### Проблема: SSL-сертификат не работает

```bash
# Проверить, что сертификат получен
ls certbot/conf/live/

# Принудительно обновить сертификат
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Перезапустить Nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Проблема: Работа без домена (временно по IP)

Если домен ещё не куплен/не настроен, можно запустить без SSL:

1. Замените `nginx/conf.d/default.conf` на упрощённый вариант:

```bash
cat > nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
```

2. Обновите `.env`:
```
CORS_ORIGINS_STR=http://ВАШ_IP
FRONTEND_URL=http://ВАШ_IP
```

3. Перезапустите:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

4. Откройте в браузере: `http://ВАШ_IP`

### Проблема: Нехватка памяти

```bash
# Проверить использование памяти
free -h

# Создать swap-файл (если RAM < 4 ГБ)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Сделать постоянным (чтобы swap работал после перезагрузки)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Полная переустановка (если всё сломалось)

```bash
cd /home/deploy/opros

# Остановить всё
docker compose -f docker-compose.prod.yml down

# Удалить все данные (ОСТОРОЖНО — удалит базу данных!)
docker compose -f docker-compose.prod.yml down -v

# Запустить заново
docker compose -f docker-compose.prod.yml up -d --build

# Запустить миграции
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Краткая шпаргалка команд

| Действие | Команда |
|----------|---------|
| Запустить проект | `docker compose -f docker-compose.prod.yml up -d` |
| Остановить проект | `docker compose -f docker-compose.prod.yml down` |
| Пересобрать и запустить | `docker compose -f docker-compose.prod.yml up -d --build` |
| Посмотреть статус | `docker compose -f docker-compose.prod.yml ps` |
| Посмотреть логи | `docker compose -f docker-compose.prod.yml logs -f` |
| Логи конкретного сервиса | `docker compose -f docker-compose.prod.yml logs backend` |
| Перезапустить сервис | `docker compose -f docker-compose.prod.yml restart backend` |
| Миграции БД | `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head` |
| Зайти в контейнер | `docker compose -f docker-compose.prod.yml exec backend bash` |
| Подключиться к серверу | `ssh deploy@ВАШ_IP` |
| Обновить код | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |

---

## Порядок действий (чек-лист)

- [ ] 1. Зарегистрироваться на Timeweb Cloud
- [ ] 2. Создать сервер (Ubuntu 22.04, 2 CPU, 4 GB RAM)
- [ ] 3. Подключиться по SSH
- [ ] 4. Обновить систему (`apt update && apt upgrade -y`)
- [ ] 5. Создать пользователя `deploy`
- [ ] 6. Настроить файрвол (UFW)
- [ ] 7. Установить Docker и Docker Compose
- [ ] 8. Установить Git
- [ ] 9. Купить домен (опционально, можно потом)
- [ ] 10. Настроить DNS (A-запись → IP сервера)
- [ ] 11. Загрузить проект на сервер (git clone)
- [ ] 12. Создать `.env` файл с production-настройками
- [ ] 13. Настроить Nginx (указать домен)
- [ ] 14. Получить SSL-сертификат (Let's Encrypt)
- [ ] 15. Запустить проект (`docker compose up -d --build`)
- [ ] 16. Выполнить миграции БД (`alembic upgrade head`)
- [ ] 17. Проверить работоспособность в браузере
- [ ] 18. Проверить админ-панель
