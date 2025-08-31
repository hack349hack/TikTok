import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Укажи TOKEN в переменных окружения!")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))

# --- Настройки бота ---
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

OWNER_ID = None
rename_state = {}
SOUND_URLS = []  # [{'url': '...', 'name': '...'}]

# === FSM СОСТОЯНИЯ ===
class AddSoundStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()

# === КЛАВИАТУРЫ ===
def get_main_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound"),
                InlineKeyboardButton(text="📃 Список звуков", callback_data="list_sounds")
            ]
        ]
    )
    return kb

def build_sounds_keyboard():
    kb = InlineKeyboardMarkup()
    for i, sound in enumerate(SOUND_URLS):
        name = sound.get("name") or "Без имени"
        kb.add(
            InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"remove_sound_{i}"),
            InlineKeyboardButton(text=f"✏️ {name}", callback_data=f"rename_sound_{i}"),
            InlineKeyboardButton(text=f"🎬 Последние 5 видео", callback_data=f"last_videos_{i}")
        )
    return kb

# === Selenium: получение свежих видео и фото ===
def get_latest_items(sound_url: str, count: int = 5):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    videos = []
    photos = []

    try:
        logger.info(f"Открываем {sound_url}")
        driver.get(sound_url)
        driver.implicitly_wait(5)

        # Видео
        video_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/video/")]')
        video_data = []
        for elem in video_elements:
            url = elem.get_attribute("href")
            try:
                timestamp = int(elem.get_attribute("data-e2e-ts"))
            except:
                timestamp = 0
            video_data.append((url, timestamp))
        video_data.sort(key=lambda x: x[1], reverse=True)
        videos = [v[0] for v in video_data[:count]]

        # Фото
        photo_elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/photo/")]')
        photo_data = []
        for elem in photo_elements:
            url = elem.get_attribute("href")
            try:
                timestamp = int(elem.get_attribute("data-e2e-ts"))
            except:
                timestamp = 0
            photo_data.append((url, timestamp))
        photo_data.sort(key=lambda x: x[1], reverse=True)
        photos = [p[0] for p in photo_data[:count]]

        logger.info(f"Найдено видео: {len(videos)}, фото: {len(photos)}")

    except Exception as e:
        logger.error(f"Ошибка при получении элементов: {e}")
    finally:
        driver.quit()

    return videos, photos

# === Обработчики ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def add_sound_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_get_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("✏️ Теперь пришли название звука (или напиши 'нет' для пропуска):")
    await state.set_state(AddSoundStates.waiting_for_name)

@dp.message(AddSoundStates.waiting_for_name)
async def add_sound_get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    url = data['url']
    name = message.text if message.text.lower() != 'нет' else None
    SOUND_URLS.append({'url': url, 'name': name})
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=get_main_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data == "list_sounds")
async def list_sounds_cb(callback: CallbackQuery):
    kb = build_sounds_keyboard()
    if kb.inline_keyboard:
        await callback.message.answer("📃 Список звуков:", reply_markup=kb)
    else:
        await callback.message.answer("❌ Список пуст")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("remove_sound_"))
async def remove_sound_cb(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    if 0 <= idx < len(SOUND_URLS):
        removed = SOUND_URLS.pop(idx)
        await callback.message.edit_text(f"🗑 Звук удалён: {removed.get('name') or removed['url']}", reply_markup=get_main_keyboard())
        await callback.answer()

rename_state = {}
@dp.callback_query(lambda c: c.data.startswith("rename_sound_"))
async def rename_sound_cb(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    if 0 <= idx < len(SOUND_URLS):
        rename_state[callback.from_user.id] = idx
        await callback.message.answer("✏️ Введи новое имя для этого звука:")
        await callback.answer()

@dp.message()
async def handle_rename(message: types.Message):
    if message.from_user.id in rename_state:
        idx = rename_state.pop(message.from_user.id)
        SOUND_URLS[idx]['name'] = message.text
        await message.answer(f"✅ Звук переименован: {message.text}", reply_markup=get_main_keyboard())
        return

@dp.callback_query(lambda c: c.data.startswith("last_videos_"))
async def last_videos_cb(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    sound = SOUND_URLS[idx]
    videos, photos = get_latest_items(sound['url'], count=5)
    if not videos and not photos:
        await callback.answer("❌ Видео и фото пока нет", show_alert=True)
        return

    text = f"🎬 Последние видео под звуком {sound.get('name') or 'Без имени'}:\n"
    for i, v in enumerate(videos, start=1):
        text += f"{i}. {v}\n"
    if photos:
        text += "\n📸 Последние фото:\n"
        for i, p in enumerate(photos, start=1):
            text += f"{i}. {p}\n"

    await callback.message.answer(text)
    await callback.answer()

# === Проверка новых видео/фото каждые CHECK_INTERVAL секунд ===
async def check_new_content():
    last_seen = {}  # sound_url -> set of urls
    while True:
        for sound in SOUND_URLS:
            sound_url = sound['url']
            videos, photos = get_latest_items(sound_url, count=5)
            new_items = []
            prev_seen = last_seen.get(sound_url, set())
            for v in videos + photos:
                if v not in prev_seen:
                    new_items.append(v)
            if new_items and OWNER_ID:
                text = f"🆕 Новые видео/фото под звуком {sound.get('name') or 'Без имени'}:\n"
                for i, item in enumerate(new_items, start=1):
                    text += f"{i}. {item}\n"
                await bot.send_message(chat_id=OWNER_ID, text=text)
            last_seen[sound_url] = set(videos + photos)
        await asyncio.sleep(CHECK_INTERVAL)

# === Запуск бота ===
async def main():
    asyncio.create_task(check_new_content())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
