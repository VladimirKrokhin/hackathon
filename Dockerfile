# Используем официальный Python образ
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 

# Обновляем систему и устанавливаем необходимые пакеты для playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libpango-1.0-0 \
    libcairo2 \
    libgtk-3-0 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы управления зависимостями
COPY pyproject.toml uv.lock ./

# Устанавливаем uv
RUN pip install uv

# Устанавливаем зависимости с помощью uv
RUN uv sync --locked

# Устанавливаем playwright со всеми браузерами (без указания кастомного пути)
RUN uv run playwright install --with-deps chromium

# Копируем исходный код
COPY src/ ./src/

# Устанавливаем переменные окружения по умолчанию
ENV PYTHONPATH=/app/src
ENV UV_CACHE_DIR=/app/.cache/uv

WORKDIR /app/src

# Запускаем приложение
CMD ["bash", "-c", "uv run main.py"]
