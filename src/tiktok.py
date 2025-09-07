import re
import aiohttp

MUSIC_URL_FMT = "https://www.tiktok.com/music/{slug}-{music_id}"


def music_id_from_input(text: str) -> str | None:
    """
    Извлекает music_id из:
    - ссылки вида https://www.tiktok.com/music/название-123456789
    - просто ID (число)
    """
    # match full music link
    match = re.search(r"music/[A-Za-z0-9%_-]+-(\d+)", text)
    if match:
        return match.group(1)

    # match plain digits
    match = re.search(r"\b(\d{5,})\b", text)
    if match:
        return match.group(1)

    return None


async def fetch_music_videos(music_id: str):
    """
    Получает список видео по music_id.
    Возвращает список {url, ts} и последний ts.
    """
    url = f"https://www.tiktok.com/music/original-{music_id}"
    api = f"https://www.tiktok.com/api/music/item_list/?musicID={music_id}&count=20"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"TikTok API error {resp.status}")
            data = await resp.json()

    videos = []
    last_ts = 0
    for item in data.get("itemList", []):
        video_url = f"https://www.tiktok.com/@{item['author']['uniqueId']}/video/{item['id']}"
        ts = int(item["createTime"])
        videos.append({"url": video_url, "ts": ts})
        last_ts = max(last_ts, ts)

    return videos, last_ts
