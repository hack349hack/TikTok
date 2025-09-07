# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
COPY src ./src
COPY .env.sample .env

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Создаём __pycache__ и делаем src пакетом
RUN touch src/__init__.py

# Переменные окружения (токен через Amwera)
ENV TELEGRAM_TOKEN=${TELEGRAM_TOKEN}

# Команда запуска через пакет src
CMD ["python", "-m", "src.bot"]
