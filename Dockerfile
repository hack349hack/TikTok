# Используем официальный slim-образ Python
FROM python:3.11-slim

# Рабочая директория в контейнере
WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Запускаем модуль src.bot
CMD ["python", "-m", "src.bot"]
