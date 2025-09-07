import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")

SETTINGS = Settings()
