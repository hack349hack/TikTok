import os
import json
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ===== ЛОГИ =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== ПЕРЕМЕННЫЕ =====
TOKEN = os.getenv("TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
HISTORY_FILE = "seen_videos.json"
SOUNDS_FILE = "sounds.json"
SOUNDS_PER_PAGE = 5

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

OWNER_ID = None
rename_state = {}
seen_videos = {}
SOUND_URLS = []

# ===== ЗАГРУЗКА JSON =====
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        seen_videos = json.load(f)

if os.path.exists(SOUNDS_FILE):
    with open(SOUNDS_FILE, "r") as f:
        SOUND_URLS = json.load(f)

# ===== FSM СОСТОЯНИЯ =====
class AddSoundStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()

# ===== КЛАВИАТУРЫ =====
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("➕ Добавить звук", callback_data="add_sound"),
             InlineKeyboardButton("📃 Список звуков", callback_data="list_sounds")]
        ]
    )

def build_sounds_keyboard(page: int = 0):
    start = page * SOUNDS_PER_PAGE
    end = start + SOUNDS_PER_PAGE
    sounds_page = SOUND_URLS[start:end]
    if not sounds_page:
        return None

    inline_keyboard = []
    for i, sound in enumerate(sounds_page, start=start):
        inline_keyboard.append([
            InlineKeyboardButton(f"🗑 {sound.get('name') or 'Без имени'}", callback_data=f"remove_sound_{i}"),
            InlineKeyboardButton(f"✏️ {sound.get('name') or 'Без имени'}", callback_data=f"rename_sound_{i}"),
            InlineKeyboardButton("🎬 5 последних видео", callback_data=f"last_videos_{i}")
        ])
    inline_keyboard.append([InlineKeyboardButton("➕ Добавить звук", callback_data="add_sound")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# ===== SELENIUM =====
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

async def fetch_latest_videos(url, limit=5):
    try:
        driver = get_driver()
        logger.info(f"Парсинг URL: {url}")
        driver.get(url)
        asyncio.sleep(2)
        elements = driver.find_elements(By.XPATH, "//a[contains(@href,'/video/')]")
        videos = [e.get_attribute("href") for e in elements]
        driver.quit()
        return videos[:limit]
    except Exception as e:
        logger.error(f"Ошибка при парсинге видео: {e}")
        return []

# ===== ПРОВЕРКА НОВЫХ ВИДЕО =====
async def check_new_videos():
    global seen_videos
    while True:
        for idx, sound in enumerate(SOUND_URLS):
            sound_url = sound['url']
            videos = await fetch_latest_videos(sound_url)
            if sound_url not in seen_videos:
                seen_videos[sound_url] = []
            new_videos = [v for v in videos if v not in seen_videos[sound_url]]
            for v in new_videos:
                seen_videos[sound_url].append(v)
                logger.info(f"Найден новый ролик под звуком {sound.get('name')}: {v}")
                if OWNER_ID:
                    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("▶️ Открыть в TikTok", url=v))
                    await bot.send_message(chat_id=OWNER_ID, text=f"🆕 Новый ролик: {sound.get('name')}", reply_markup=keyboard)
            with open(HISTORY_FILE, "w") as f:
                json.dump(seen_videos, f)
        await asyncio.sleep(CHECK_INTERVAL)

# ===== ОБРАБОТЧИКИ =====
@dp.message(Command("start"))
async def start_cmd(message: Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def add_sound_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("✏️ Введи название звука или 'нет' для пропуска:")
    await state.set_state(AddSoundStates.waiting_for_name)

@dp.message(AddSoundStates.waiting_for_name)
async def add_sound_name(message: Message, state: FSMContext):
    data = await state.get_data()
    url = data['url']
    name = message.text if message.text.lower() != "нет" else None
    SOUND_URLS.append({"url": url, "name": name})
    with open(SOUNDS_FILE, "w") as f:
        json.dump(SOUND_URLS, f)
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=get_main_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data == "list_sounds")
async def list_sounds(callback: CallbackQuery):
    kb = build_sounds_keyboard()
    if kb:
        await callback.message.answer("📃 Список звуков:", reply_markup=kb)
    else:
        await callback.message.answer("❌ Список пуст")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("last_videos_"))
async def last_videos_cb(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    sound = SOUND_URLS[idx]
    videos = await fetch_latest_videos(sound['url'])
    if not videos:
        await callback.answer("❌ Видео пока нет", show_alert=True)
        return
    text = f"🎬 5 последних видео под звуком {sound.get('name') or 'Без имени'}:\n"
    for i, v in enumerate(videos, 1):
        text += f"{i}. {v}\n"
    await callback.message.answer(text)
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    asyncio.create_task(check_new_videos())
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
