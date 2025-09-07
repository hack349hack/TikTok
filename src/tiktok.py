import asyncio
from typing import List, Tuple, Optional
from dataclasses import dataclass
import httpx
import re

MUSIC_URL_FMT = "https://www.tiktok.com/music/original-sound-{mid}"


@dataclass
class TikTokVideo:
    id: str
    desc: str
    create_time: int
    author: str

    def link(self) -> str:
        return f"https://www.tiktok.com/@{self.author}/video/{self.id}"


def music_id_from_input(text: str) -> Optional[str]:
    """Пытаемся извлечь music_id из ссылки или текста"""
    match = re.search(r"(?:/music/|original-sound-)(\d+)", text)
    return match.group(1) if match else None


async def fetch_music_videos(music_id: str, http_proxy: Optional[str] = None, limit: int = 20) -> Tuple[List[TikTokVideo], Optional[str]]:
    """
    Fetch recent videos for a TikTok music (sound) id.
    Возвращает кортеж (список TikTokVideo, название звука)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    url = f"https://www.tiktok.com/music/original-sound-{music_id}"
    async with httpx.AsyncClient(proxies=http_proxy, headers=headers, timeout=15) as client:
        resp = await client.get(url)
        text = resp.text

    # парсим минимально через регулярку
    title_match = re.search(r'<h1.*?>(.*?)</h1>', text)
    title = title_match.group(1) if title_match else None

    # получаем видео из страницы (здесь простая заглушка, можно через API/Playwright)
    video_ids = re.findall(r'/video/(\d+)"', text)
    author = "unknown"
    items = [TikTokVideo(id=vid, desc="", create_time=0, author=author) for vid in video_ids[:limit]]

    return items, title


async def discover_new_sounds_by_hashtag(tag: str, http_proxy: Optional[str] = None, limit: int = 10) -> List[Tuple[str, Optional[str]]]:
    """
    Ищет новые звуки по хэштегу
    Возвращает список кортежей (music_id, title)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    url = f"https://www.tiktok.com/tag/{tag}"
    async with httpx.AsyncClient(proxies=http_proxy, headers=headers, timeout=15) as client:
        resp = await client.get(url)
        text = resp.text

    # простая заглушка: ищем все music_id
    mids = re.findall(r'/music/original-sound-(\d+)', text)
    return [(mid, None) for mid in mids[:limit]]


# Пример синхронной обертки для вызова без async
def fetch_music_videos_sync(*args, **kwargs):
    return asyncio.run(fetch_music_videos(*args, **kwargs))


def discover_new_sounds_by_hashtag_sync(*args, **kwargs):
    return asyncio.run(discover_new_sounds_by_hashtag(*args, **kwargs))
  
