import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bs4 import BeautifulSoup

# ====== ПЕРЕМЕННЫЕ ИЗ ОКРУЖЕНИЯ ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_API_VERSION = "5.131"
TOP_LIMIT = int(os.getenv("TOP_LIMIT", 10))  # можно менять через переменные

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ====== ЛОГИРОВАНИЕ ======
logging.basicConfig(level=logging.INFO)

# ====== ПОИСК ТРЕКОВ ======
def search_vk_audio(query, count=20):
    url = "https://api.vk.com/method/audio.search"
    params = {
        "q": query,
        "count": count,
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION
    }
    response = requests.get(url, params=params).json()
    if "response" in response:
        return response["response"]["items"]
    return []

# ====== ПОИСК ПУБЛИЧНЫХ ПЛЕЙЛИСТОВ ======
def find_playlists(track_id, owner_id):
    playlists = []

    track_url = f"https://vk.com/audio{owner_id}_{track_id}"
    response = requests.get(track_url, headers=HEADERS)
    if response.status_code != 200:
        return playlists

    soup = BeautifulSoup(response.text, "html.parser")

    for pl_block in soup.select(".audio_playlist_row"):
        try:
            title_tag = pl_block.select_one(".audio_playlist_title")
            link_tag = pl_block.select_one("a.audio_playlist_link")
            plays_tag = pl_block.select_one(".audio_playlist_plays")

            title = title_tag.text.strip() if title_tag else "Без названия"
            url = "https://vk.com" + link_tag["href"] if link_tag else track_url

            total_plays = 0
            if plays_tag:
                plays_text = plays_tag.text.strip().replace(" ", "").replace("прослушивания", "").replace("тыс.", "000")
                total_plays = int(''.join(filter(str.isdigit, plays_text)))

            playlists.append({
                "title": title,
                "url": url,
                "total_plays": total_plays
            })
        except Exception:
            continue

    return playlists

# ====== КОМАНДА /find ======
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Используйте: /find <название песни>")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"Ищу треки для: {query}...")

    tracks = search_vk_audio(query)
    if not tracks:
        await update.message.reply_text("Треки не найдены.")
        return

    all_playlists = []
    for track in tracks:
        playlists = find_playlists(track_id=track["id"], owner_id=track["owner_id"])
        all_playlists.extend(playlists)

    all_playlists.sort(key=lambda x: x["total_plays"], reverse=True)

    if not all_playlists:
        await update.message.reply_text("Плейлисты не найдены.")
        return

    msg = "Топ плейлистов:\n\n"
    for pl in all_playlists[:TOP_LIMIT]:
        msg += f"{pl['title']} — {pl['total_plays']} прослушиваний\n{pl['url']}\n\n"

    await update.message.reply_text(msg)

# ====== ЗАПУСК БОТА ======
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not VK_TOKEN:
        raise ValueError("Переменные окружения TELEGRAM_TOKEN и VK_TOKEN должны быть установлены!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("find", find))
    print("Бот запущен...")
    app.run_polling()
