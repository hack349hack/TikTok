import re
from typing import List, Tuple

MUSIC_URL_FMT = "https://www.tiktok.com/music/original-sound-{mid}"

async def fetch_music_videos(
    music_id: str,
    http_proxy: str | None = None,
    limit: int = 10
) -> Tuple[List[dict], int]:
    """
    Получает последние видео по music_id.
    Возвращает список словарей с видео и метку времени последнего видео.
    """
    # Заглушка для примера
    items = [{"id": f"video{i}", "url": f"https://tiktok.com/@user/video{i}", "ts": i} for i in range(limit)]
    last_ts = max(item["ts"] for item in items) if items else 0
    return items, last_ts

def music_id_from_input(text: str) -> str | None:
    """
    Извлекает music_id из ссылки или возвращает число, если это ID.
    Работает со ссылками с кириллицей и латиницей.
    """
    text = text.strip()
    # Берём последнюю группу цифр длиной 16+
    match = re.search(r"(\d{16,})", text)
    if match:
        return match.group(1)
    return None

def discover_new_sounds_by_hashtag(tag: str, limit: int = 10) -> List[str]:
    """
    Заглушка для поиска новых звуков по хэштегу.
    """
    return [str(7344858713896913666 + i) for i in range(limit)]
    
