import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Логирование
logging.basicConfig(level=logging.INFO)

# --- Переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # кому слать уведомления
if not BOT_TOKEN:
    raise ValueError("❌ Укажи BOT_TOKEN в переменных окружения!")

# --- Настройки ---
SOUND_URLS = [
    "https://www.tiktok.com/music/original-sound-1234567890",
    "https://www.tiktok.com/music/original-sound-9876543210"
]
CHECK_INTERVAL = 60  # раз в сколько секунд проверять новые видео

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Временное хранилище ---
last_videos = {url: [] for url in SOUND_URLS}


# ==== Парсинг последних видео TikTok ====
async def fetch_last_videos(sound_url, limit=5):
    """
    Заглушка парсинга TikTok.
    Здесь можно подключить реальный парсер API / playwright / selenium.
    Пока возвращает тестовые ссылки.
    """
    # эмуляция разных видео по звуку
    return [f"{sound_url}?video={i}" for i in range(1, limit + 1)]


# ==== Проверка новых видео ====
async def check_new_videos():
    while True:
        for sound in SOUND_URLS:
            try:
                new_videos = await fetch_last_videos(sound)
                old = set(last_videos.get(sound, []))
                fresh = [v for v in new_videos if v not in old]

                if fresh:
                    last_videos[sound] = new_videos
                    for video in fresh:
                        msg = f"📢 Новое видео по звуку:\n{sound}\n▶ {video}"
                        if CHAT_ID:
                            await bot.send_message(CHAT_ID, msg)
                        else:
                            logging.warning("CHAT_ID не задан, уведомление не отправлено")

            except Exception as e:
                logging.error(f"Ошибка при проверке звука {sound}: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


# ==== Кнопки ====
def main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 5 последних видео", callback_data="last5")],
        [InlineKeyboardButton(text="🎧 Список звуков", callback_data="list_sounds")]
    ])
    return kb


# ==== Обработчики ====
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Я TikTok бот.\nВыбирай действие:", reply_markup=main_keyboard())


@dp.callback_query(F.data == "last5")
async def last5_videos(callback: types.CallbackQuery):
    text = "🎵 5 последних видео по каждому звуку:\n\n"
    for sound in SOUND_URLS:
        videos = await fetch_last_videos(sound, 5)
        last_videos[sound] = videos
        text += f"\n🔊 {sound}\n"
        for v in videos:
            text += f"▶ {v}\n"
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "list_sounds")
async def list_sounds(callback: types.CallbackQuery):
    if not SOUND_URLS:
        await callback.message.answer("⚠️ Список звуков пуст. Добавь ссылки в SOUND_URLS.")
        await callback.answer()
        return

    text = "🎧 Доступные звуки:\n\n"
    for i, url in enumerate(SOUND_URLS, start=1):
        text += f"{i}. {url}\n"

    if len(text) > 4000:  # защита от краша
        text = text[:4000] + "\n... обрезано"

    await callback.message.answer(text)
    await callback.answer()


# ==== Запуск ====
async def main():
    # Запускаем проверку новых видео в фоне
    asyncio.create_task(check_new_videos())

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
