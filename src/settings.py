from __future__ import annotations
import os
from pydantic import BaseModel


class Settings(BaseModel):
telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
admin_chat_id: int | None = int(os.getenv("ADMIN_CHAT_ID", "0") or 0) or None
poll_interval_sec: int = int(os.getenv("POLL_INTERVAL_SEC", "180"))
http_proxy: str | None = os.getenv("HTTP_PROXY") or None


SETTINGS = Settings()
