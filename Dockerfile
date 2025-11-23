# Используем официальный Python образ
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 

# Обновляем систему и устанавливаем необходимые пакеты для playwright и PIL
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
    fonts-noto-cjk \
    fonts-noto-mono \
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

# Устанавливаем шрифты с поддержкой кириллицы
RUN apt-get update && apt-get install -y \
    fonts-crosextra-caladea \
    fonts-crosextra-carlito \
    fonts-dejavu-extra \
    fonts-liberation2 \
    fonts-linuxlibertine \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-noto-ui-core \
    fonts-opensymbol \
    fonts-sil-gentium \
    fonts-sil-gentium-basic \
    && rm -rf /var/lib/apt/lists/*

# Создаем символические ссылки для совместимости с PIL
RUN mkdir -p /usr/share/fonts/truetype && \
    ln -sf /usr/share/fonts/opentype /usr/share/fonts/truetype/opentype 2>/dev/null || true

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
