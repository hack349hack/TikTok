import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === НАСТРОЙКИ ЧЕРЕЗ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # если не задано → 0
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # по умолчанию 60 секунд

if not API_TOKEN:
    raise ValueError("❌ Переменная окружения API_TOKEN не задана!")

# Список звуков (пример)
SOUND_URLS = [
    {"name": "Популярный звук", "url": "https://www.tiktok.com/music/sound-12345"},
    {"name": "Весёлый бит", "url": "https://www.tiktok.com/music/sound-67890"},
]

# Словарь просмотренных видео
seen_videos = {s["url"]: [] for s in SOUND_URLS}

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)

# === БОТ ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# --- ФУНКЦИИ ДЛЯ ПАРСИНГА ---
def get_latest_videos(sound_url: str, limit: int = 5):
    """Парсит последние видео по ссылке на звук"""
    try:
        r = requests.get(sound_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        video_elements = [a["href"] for a in soup.find_all("a", href=True) if "/video/" in a["href"]]
        return video_elements[:limit]
    except Exception as e:
        print(f"Ошибка парсинга {sound_url}: {e}")
        return []


# --- КОМАНДА START ---
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Список звуков", callback_data="list_sounds")],
    ])
    await message.answer("Привет! 👋\nЯ помогу следить за видео по звукам TikTok.", reply_markup=kb)


# --- СПИСОК ЗВУКОВ ---
@dp.callback_query(F.data == "list_sounds")
async def list_sounds(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    for idx, sound in enumerate(SOUND_URLS):
        kb.add(
            InlineKeyboardButton(text=f"🎵 {sound['name']}", callback_data=f"sound_{idx}")
        )
    await callback.message.answer("Выбери звук:", reply_markup=kb)
    await callback.answer()


# --- ВЫБОР ЗВУКА ---
@dp.callback_query(F.data.startswith("sound_"))
async def sound_options(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕓 5 последних (история)", callback_data=f"history_{idx}")],
        [InlineKeyboardButton(text="✨ 5 последних (новое)", callback_data=f"latest_{idx}")],
    ])
    await callback.message.answer(f"🎵 {SOUND_URLS[idx]['name']}\nВыберите действие:", reply_markup=kb)
    await callback.answer()


# --- ИСТОРИЯ (из seen_videos) ---
@dp.callback_query(F.data.startswith("history_"))
async def show_history(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    sound = SOUND_URLS[idx]
    videos = seen_videos.get(sound["url"], [])[:5]

    if not videos:
        await callback.message.answer("❌ В истории пока нет видео")
    else:
        text = f"🎬 История 5 последних видео ({sound['name']}):\n"
        for i, v in enumerate(videos, start=1):
            text += f"{i}. {v}\n"
        await callback.message.answer(text)

    await callback.answer()


# --- НОВЫЕ (парсинг сайта) ---
@dp.callback_query(F.data.startswith("latest_"))
async def show_latest(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    sound = SOUND_URLS[idx]
    videos = get_latest_videos(sound["url"])

    if not videos:
        await callback.message.answer("❌ Не удалось получить новые видео")
    else:
        text = f"✨ 5 новых видео ({sound['name']}):\n"
        for i, v in enumerate(videos, start=1):
            text += f"{i}. {v}\n"
        await callback.message.answer(text)

    await callback.answer()


# --- ФОНОВАЯ ПРОВЕРКА ---
async def check_new_videos():
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, "✅ Бот запущен и начал проверку новых видео")
    while True:
        for sound in SOUND_URLS:
            latest = get_latest_videos(sound["url"], limit=1)
            if latest:
                last_video = latest[0]
                if last_video not in seen_videos[sound["url"]]:
                    seen_videos[sound["url"]].insert(0, last_video)
                    if ADMIN_ID:
                        await bot.send_message(ADMIN_ID, f"🔔 Новое видео ({sound['name']}): {last_video}")
        await asyncio.sleep(CHECK_INTERVAL)


# --- ЗАПУСК ---
async def main():
    asyncio.create_task(check_new_videos())  # фоновая задача
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
