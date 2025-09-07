# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
COPY bot.py .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Переменные окружения (будут подхватываться из Amvera)
ENV TELEGRAM_TOKEN=$TELEGRAM_TOKEN
ENV VK_TOKEN=$VK_TOKEN
ENV TOP_LIMIT=$TOP_LIMIT

# Запуск бота
CMD ["python", "bot.py"]
