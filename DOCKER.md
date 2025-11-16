# Запуск Публикун-бота в Docker

Это руководство поможет вам запустить Telegram-бота Публикун в Docker-контейнере.

## 📋 Предварительные требования

- Docker Engine 20.10+
- Docker Compose v2.0+
- Токен Telegram-бота от [@BotFather](https://t.me/botfather)
- API ключи Yandex Cloud для YandexGPT

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
# Перейти в директорию проекта
cd hackathon/

# Скопировать файл переменных окружения
cp .env.example .env

# Отредактировать файл .env и добавить ваши ключи
nano .env
```

Заполните файл `.env` вашими данными:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
YANDEXGPT_API_KEY=YOUR_YANDEX_API_KEY
YANDEXGPT_CATALOG_ID=YOUR_YANDEX_CATALOG_ID
FUSION_BRAIN_API_KEY=YOUR_FUSION_BRAIN_API_KEY
FUSION_BRAIN_SECRET_KEY=YOUR_FUSION_BRAIN_SECRET_KEY
DEBUG=True
```

### 2. Сборка и запуск контейнера

#### Вариант 1: С помощью Docker Compose (рекомендуется)

```bash
# Сборка и запуск в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

#### Вариант 2: С помощью Docker

```bash
# Сборка образа
docker build -t publichun-bot .

# Запуск контейнера
docker run -d \
  --name publichun-bot \
  --env-file .env \
  -v publichun-playwright-cache:/home/app/.cache \
  -v $(pwd)/src/ngo_data.db:/app/src/ngo_data.db \
  publichun-bot
```

## 🔧 Управление контейнером

### Просмотр логов

```bash
# Логи в реальном времени
docker-compose logs -f publichun-bot

# Логи за последние 100 строк
docker-compose logs --tail=100 publichun-bot
```

### Перезапуск бота

```bash
# Полная пересборка и перезапуск
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Простой перезапуск
docker-compose restart publichun-bot
```

### Остановка

```bash
# Остановка контейнера
docker-compose down

# Остановка с удалением томов (осторожно!)
docker-compose down -v
```

### Проверка состояния контейнера

```bash
# Статус всех контейнеров
docker-compose ps

# Статус конкретного контейнера
docker-compose ps publichun-bot

# Использование ресурсов
docker stats publichun-bot
```

### Подключение к контейнеру (для отладки)

```bash
# Подключение к контейнеру
docker-compose exec publichun-bot bash

# Запуск Python shell в контейнере
docker-compose exec publichun-bot python