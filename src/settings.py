import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SETTINGS:
    # Токен Telegram бота
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    # ID чата для админ-уведомлений (опционально)
    admin_chat_id: Optional[str] = os.getenv("ADMIN_CHAT_ID")
    # Интервал проверки новых видео в секундах
    poll_interval_sec: int = int(os.getenv("POLL_INTERVAL_SEC", "180"))
    # HTTP прокси для TikTok (если нужно)
    http_proxy: Optional[str] = os.getenv("HTTP_PROXY")
