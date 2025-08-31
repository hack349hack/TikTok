import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State

# Логирование
logging.basicConfig(level=logging.INFO)

# --- Переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # кому слать уведомления
if not BOT_TOKEN:
    raise ValueError("❌ Укажи BOT_TOKEN в переменных окружения!")

# --- Настройки ---
CHECK_INTERVAL = 60  # раз в сколько секунд проверять новые видео

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Временное хранилище ---
SOUND_URLS = []
last_videos = {}

# ==== Состояния ====
class AddSound(StatesGroup):
    waiting_for_url = State()


# ==== Парсинг последних видео TikTok ====
async def fetch_last_videos(sound_url, limit=5):
    """
    Заглушка парсинга TikTok.
    Здесь можно подключить реальный парсер API / playwright / selenium.
    Пока возвращает тестовые ссылки.
    """
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

            except Exception as e:
                logging.error(f"Ошибка при проверке звука {sound}: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


# ==== Кнопки ====
def main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 5 последних видео", callback_data="last5")],
        [InlineKeyboardButton(text="🎧 Список звуков", callback_data="list_sounds")],
        [InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound")]
    ])
    return kb


# ==== Обработчики ====
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Я TikTok бот.\nВыбирай действие:", reply_markup=main_keyboard())


@dp.callback_query(F.data == "last5")
async def last5_videos(callback: types.CallbackQuery):
    if not SOUND_URLS:
        await callback.message.answer("⚠️ Список звуков пуст. Добавь ссылки кнопкой '➕ Добавить звук'")
        await callback.answer()
        return

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
        await callback.message.answer("⚠️ Список звуков пуст.")
        await callback.answer()
        return

    text = "🎧 Доступные звуки:\n\n"
    for i, url in enumerate(SOUND_URLS, start=1):
        text += f"{i}. {url}\n"

    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "add_sound")
async def add_sound(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Отправь мне ссылку на звук TikTok:")
    await state.set_state(AddSound.waiting_for_url)
    await callback.answer()


@dp.message(AddSound.waiting_for_url)
async def process_add_sound(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ Это не похоже на ссылку. Попробуй ещё раз.")
        return

    SOUND_URLS.append(url)
    last_videos[url] = []
    await message.answer(f"✅ Звук добавлен!\nТеперь отслеживаю:\n{url}", reply_markup=main_keyboard())
    await state.clear()


# ==== Запуск ====
async def main():
    asyncio.create_task(check_new_videos())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
