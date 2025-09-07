import asyncio
import httpx
from datetime import datetime
from .storage import save_new_video, get_known_video_ids

BASE_MUSIC_API = "https://www.tiktok.com/api/music/item_list/"

async def fetch_videos_by_music(music_id: str, count: int = 30):
    """
    Получаем последние видео по music_id.
    Возвращает список новых видео.
    """
    known_ids = get_known_video_ids(music_id)
    new_videos = []

    params = {"musicID": music_id, "count": count}
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_MUSIC_API, params=params, headers=headers)
        data = resp.json()

    for aweme in data.get("aweme_list", []):
        vid = aweme["aweme_id"]
        if vid not in known_ids:
            new_videos.append({
                "aweme_id": vid,
                "desc": aweme.get("desc", ""),
                "author": aweme.get("author", {}).get("nickname", ""),
                "create_time": datetime.fromtimestamp(aweme.get("create_time", 0)),
                "video_url": aweme.get("video", {}).get("play_addr", {}).get("url_list", [None])[0]
            })
            save_new_video(music_id, vid)
    return new_videos


async def monitor_music(bot, music_id: str, chat_id: int, interval: int = 180):
    """
    Фоновый мониторинг новых видео по music_id
    и отправка в Telegram каждые `interval` секунд.
    """
    while True:
        try:
            new_videos = await fetch_videos_by_music(music_id)
            for video in new_videos:
                text = f"🎵 Новое видео под звук:\n\n{video['desc']}\nАвтор: {video['author']}\nСсылка: https://www.tiktok.com/@{video['author']}/video/{video['aweme_id']}"
                if video["video_url"]:
                    await bot.send_video(chat_id, video["video_url"], caption=text)
                else:
                    await bot.send_message(chat_id, text)
        except Exception as e:
            print("Ошибка мониторинга музыки:", e)
        await asyncio.sleep(interval)
        
