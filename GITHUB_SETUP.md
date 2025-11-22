# Настройка GitHub Self-Hosted Runner

Этот файл содержит инструкции по настройке GitHub Self-Hosted Runner на удаленном сервере для автоматического деплоя Telegram бота.
Предполагается, что бот развертывается на Debian-based дистрибутиве.

## Установка GitHub Runner на сервер

### 1. Подготовка сервера
```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите необходимые пакеты
sudo apt install -y curl wget git unzip jq docker.io docker-compose

# Включите и запустите Docker
sudo systemctl enable docker
sudo systemctl start docker

# Добавьте текущего пользователя в группу docker
sudo usermod -aG docker $USER

# Перезайдите или выполните:
newgrp docker
```

### 2. Создание пользователя для runner
```bash
# Создайте отдельного пользователя для GitHub runner
sudo useradd -m -s /bin/bash github-runner
sudo usermod -aG docker github-runner

# Переключитесь на этого пользователя
sudo su - github-runner
```

### 3. Скачивание и установка GitHub Runner
```bash
# Перейдите в домашнюю директорию пользователя
cd /home/github-runner

# Скачайте последнюю версию GitHub Actions Runner
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64.tar.gz

# Создайте директорию для runner
mkdir actions-runner && cd actions-runner

# Распакуйте архив
tar xzf ../actions-runner-linux-x64.tar.gz
```

### 4. Регистрация runner в GitHub репозитории
```bash
# Перейдите в директорию с runner
cd /home/github-runner/actions-runner

# Запустите конфигурацию (замените YOUR_USERNAME и YOUR_REPO)
./config.sh --url https://github.com/YOUR_USERNAME/YOUR_REPO --token YOUR_TOKEN

# Где взять token:
# В GitHub: Settings → Actions → Runners → Add runner → New self-hosted runner
# Скопируйте registration token
```

### 5. Настройка автозапуска runner
```bash
# Создайте systemd сервис
sudo nano /etc/systemd/system/github-runner.service
```

Добавьте в файл:
```ini
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
User=github-runner
Group=github-runner
WorkingDirectory=/home/github-runner/actions-runner
ExecStart=/home/github-runner/actions-runner/run.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Включите и запустите сервис
sudo systemctl enable github-runner
sudo systemctl start github-runner

# Проверьте статус
sudo systemctl status github-runner
```

## Подготовка проекта на сервере

После установки runner, подготовьте проект на том же сервере:

### 1. Создание структуры директорий
```bash
# Перейдите в рабочую директорию
cd /var/app

# Создайте директорию workspace если её нет
mkdir -p workspace

# Перейдите в workspace
cd workspace
```

### 2. Клонирование репозитория
```bash
# Клонируйте ваш репозиторий
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git hackathon

# Перейдите в директорию проекта
cd hackathon
```

### 3. Настройка переменных окружения
```bash
# Скопируйте и настройте .env файл
cp .env.example .env

# Отредактируйте .env файл с реальными значениями
nano .env

# Установите правильные права для владельца проекта
sudo chown -R publiccoon:publiccoon /var/app/workspace
```

### 4. Проверка настройки
```bash
# Проверьте что всё настроено правильно
ls -la

# Убедитесь что .env файл существует
cat .env | head -5  # показать первые 5 строк для проверки

# Проверьте доступ к Docker
docker --version
docker-compose --version

# Проверьте права доступа
whoami
groups
```

## Как использовать

### Автоматический деплой
При каждом пуше в ветку `main` на сервере автоматически запустится деплой:
1. Остановка текущих контейнеров
2. Получение последних изменений из GitHub
3. Пересборка Docker образов
4. Запуск новых контейнеров

### Ручное управление
В GitHub перейдите во вкладку **Actions** → **Control Bot Service** → **Run workflow**:

Выберите действие:
- **restart** - перезапуск сервиса (по умолчанию)
- **start** - запуск сервиса
- **stop** - остановка сервиса

## Структура файлов

```
.github/
  workflows/
    deploy.yml      # Автоматический деплой при пуше в main
    control.yml     # Ручное управление сервисом
workspace/          # Директория проекта на сервере (клонируется runner'ом)
```

## Мониторинг

Проверить статус containers на сервере:
```bash
cd /var/app/workspace/hackathon
docker-compose ps
```

Посмотреть логи:
```bash
docker-compose logs -f publichun-bot
```

Посмотреть статус GitHub runner:
```bash
sudo systemctl status github-runner
```

## Устранение неполадок

### Runner не запускается
```bash
# Проверьте статус сервиса
sudo systemctl status github-runner

# Посмотрите логи
sudo journalctl -u github-runner -f

# Перезапустите сервис
sudo systemctl restart github-runner
```

### Контейнеры не запускаются
```bash
# Проверьте логи сборки
cd /var/app/workspace/hackathon
docker-compose logs

# Проверьте переменные окружения
cat .env

# Проверьте Docker
docker --version
docker-compose --version
```

### Workflow не выполняется
1. Проверьте что runner зарегистрирован в GitHub
2. Убедитесь что runner онлайн в Settings → Actions → Runners
3. Проверьте логи runner:
   ```bash
   sudo journalctl -u github-runner --since "1 hour ago"
   ```

### Проблемы с доступом к Docker
```bash
# Убедитесь что пользователь в группе docker
groups github-runner

# Перезапустите сервис если нужно
sudo systemctl restart github-runner
```

