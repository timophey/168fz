# Multi-stage build
FROM python:3.11-slim as builder

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /root/.local

# Копируем исходный код
COPY . .

# Создаем необходимые директории
RUN mkdir -p dictionaries/data sync/cache app/web/static app/web/templates

# Устанавливаем переменные окружения
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV DICTIONARIES_DIR=/app/dictionaries/data

# Экспонируем порт
EXPOSE 8000

# Запуск приложения
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
