import re
from typing import List, Tuple

# Шаблон ссылки для сообщений
MUSIC_URL_FMT = "https://www.tiktok.com/music/original-sound-{mid}"

async def fetch_music_videos(
    music_id: str,
    http_proxy: str | None = None,
    limit: int = 10
) -> Tuple[List[dict], None]:
    """
    Заглушка для парсинга видео по music_id.
    В реальном боте можно использовать TikTokApi или httpx запросы.
    Возвращает список словарей с видео.
    """
    # Пример возвращаемых видео
    return [{"id": f"video{i}", "url": f"https://tiktok.com/@user/video{i}"} for i in range(limit)], None

def music_id_from_input(text: str) -> str | None:
    """
    Извлекает music_id из ссылки или возвращает текст, если это уже ID.
    Работает с ссылками:
    - https://www.tiktok.com/music/Снова-один-7344858713896913666
    - https://www.tiktok.com/music/7344858713896913666
    - 7344858713896913666
    """
    text = text.strip()
    # Ищем последнюю группу цифр длиной 16+ в ссылке
    match = re.search(r"/(\d{16,})", text)
    if match:
        return match.group(1)
    # Если это просто число
    if text.isdigit() and len(text) >= 16:
        return text
    return None

def discover_new_sounds_by_hashtag(tag: str, limit: int = 10) -> List[str]:
    """
    Заглушка для поиска новых звуков по хэштегу.
    Возвращает список music_id.
    """
    return [str(7344858713896913666 + i) for i in range(limit)]
    
