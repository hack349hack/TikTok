FROM python:3.11-slim


ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1


# Системные зависимости для Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
curl fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 \
libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxkbcommon0 \
libxrandr2 xdg-utils && rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Установка Chromium для Playwright
RUN python -m playwright install --with-deps chromium


COPY src/ ./src/
COPY README.md amvera.yaml .env.sample ./


CMD ["python", "-m", "src.bot"]
