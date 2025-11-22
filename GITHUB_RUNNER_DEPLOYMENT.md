# Развертывание GitHub Self-Hosted Runner

## Предварительные требования
- Сервер с Ubuntu 20.04+Debian 10+
- Минимум 2 CPU, 8GB RAM, 20GB хранилище
- Установленный Docker 20.10+
- Доступ к GitHub организации/репозиторию

## 1. Получение токена для регистрации

### Personal Access Token (для организации)
```
Settings → Developer settings → Personal access tokens → Fine-grained tokens
```
Разрешения:
- Organization self-hosted runners
- Organization administration (read/write)

### Organization-wide token (для repo)
```
Settings → Actions → Runners → New runner → Copy the registration command
```

## 2. Установка Runner

```bash
# Создание пользователя runner
sudo useradd --create-home --shell /bin/bash runner
sudo usermod -aG docker runner

# Переход под пользователя
sudo su - runner

# Скачивание и установка
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf actions-runner-linux-x64-2.311.0.tar.gz
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN
```

## 3. Настройка как системного сервиса

```bash
# Выход из пользователя runner
exit

# Создание службового файла
sudo tee /etc/systemd/system/github-runner.service > /dev/null <<EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
ExecStart=/home/runner/actions-runner/run.sh
User=runner
WorkingDirectory=/home/runner/actions-runner
KillMode=process
KillSignal=SIGTERM
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск
sudo systemctl daemon-reload
sudo systemctl enable github-runner
sudo systemctl start github-runner
```

## 4. Проверка работы

```bash
# Статус сервиса
sudo systemctl status github-runner

# Логи
sudo journalctl -u github-runner -f

# Проверка в GitHub
# https://github.com/YOUR_ORG/YOUR_REPO/actions → Runners
```

## 5. Конфигурация для Docker проектов

### Установка Docker в runner окружении
```bash
# Под пользователем runner
sudo su - runner
docker --version
docker ps
```

### Тестирование с вашим проектом
```yaml
# workflows/deploy.yml
jobs:
  deploy:
    runs-on: self-hosted  # Использует ваш runner
    steps:
    - uses: actions/checkout@v4
    - name: Deploy
      run: |
        docker compose build
        docker compose up -d
```

## Обслуживание

### Обновление runner
```bash
sudo su - runner
cd actions-runner
./config.sh --check  # Проверка обновлений
sudo systemctl restart github-runner
```

### Логи и диагностика
```bash
# Просмотр логов runner
cat ~/actions-runner/_diag/Runner_*.log

# Очистка дискового пространства
sudo docker system prune -af
```

### Удаление runner
```bash
# Остановка и удаление
sudo systemctl stop github-runner
sudo systemctl disable github-runner
sudo rm /etc/systemd/system/github-runner.service

# Удаление под пользователем
sudo rm -rf /home/runner/actions-runner
sudo userdel -r runner
```

