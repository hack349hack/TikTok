import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from TikTokApi import TikTokApi

# --- Переменные окружения ---
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))  # id пользователя
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))

if not TOKEN or not OWNER_ID:
    raise ValueError("Укажи TOKEN и OWNER_ID в переменных окружения!")

# --- Настройки ---
SOUNDS_FILE = "sounds.json"
HISTORY_FILE = "seen_videos.json"
SOUNDS_PER_PAGE = 5

# --- Инициализация ---
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)
api = TikTokApi()

# --- Загрузка данных ---
if os.path.exists(SOUNDS_FILE):
    with open(SOUNDS_FILE, "r") as f:
        SOUND_URLS = json.load(f)
else:
    SOUND_URLS = []

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        seen_videos = json.load(f)
else:
    seen_videos = {}

rename_state = {}

# --- FSM ---
class AddSoundStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()

# --- Клавиатуры ---
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

def build_sounds_keyboard(page: int = 0):
    start = page * SOUNDS_PER_PAGE
    end = start + SOUNDS_PER_PAGE
    sounds_page = SOUND_URLS[start:end]
    if not sounds_page:
        return None

    inline_keyboard = []
    for i, sound in enumerate(sounds_page, start=start):
        inline_keyboard.append([
            InlineKeyboardButton(text=f"🗑 {sound.get('name') or 'Без имени'}", callback_data=f"remove_sound_{i}"),
            InlineKeyboardButton(text=f"✏️ {sound.get('name') or 'Без имени'}", callback_data=f"rename_sound_{i}"),
            InlineKeyboardButton(text="🎬 Последние видео", callback_data=f"last_videos_{i}")
        ])
    inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound")])

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'page_{page-1}'))
    if end < len(SOUND_URLS):
        nav_buttons.append(InlineKeyboardButton(text='➡️ Вперёд', callback_data=f'page_{page+1}'))
    if nav_buttons:
        inline_keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# --- Проверка новых видео ---
async def check_new_videos():
    while True:
        for idx, sound in enumerate(SOUND_URLS):
            try:
                sound_url = sound['url']
                name = sound.get('name') or f"#{idx+1}"
                posts = api.by_sound(sound_url, count=50)
                if sound_url not in seen_videos:
                    seen_videos[sound_url] = []

                for post in posts:
                    video_id = post['id']
                    if video_id not in seen_videos[sound_url]:
                        seen_videos[sound_url].append(video_id)
                        with open(HISTORY_FILE, "w") as f:
                            json.dump(seen_videos, f)
                        video_link = f"https://www.tiktok.com/@{post['author']['uniqueId']}/video/{video_id}"
                        await bot.send_message(
                            OWNER_ID,
                            text=f"🆕 Новый ролик под звуком {name}:\n{video_link}"
                        )
            except Exception as e:
                print("Ошибка при проверке новых видео:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# --- Обработчики ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def inline_add_sound(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_get_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("✏️ Теперь пришли название звука (или 'нет'):")
    await state.set_state(AddSoundStates.waiting_for_name)

@dp.message(AddSoundStates.waiting_for_name)
async def add_sound_get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    url = data['url']
    name = message.text if message.text.lower() != "нет" else None
    SOUND_URLS.append({"url": url, "name": name})
    with open(SOUNDS_FILE, "w") as f:
        json.dump(SOUND_URLS, f)
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=get_main_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data == "list_sounds")
async def callback_list_sounds(callback: types.CallbackQuery):
    kb = build_sounds_keyboard()
    if kb:
        await callback.message.answer("📃 Список звуков:", reply_markup=kb)
    else:
        await callback.message.answer("❌ Список пуст")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("last_videos_"))
async def callback_last_videos(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    sound = SOUND_URLS[idx]
    sound_url = sound["url"]
    name = sound.get("name") or f"#{idx+1}"

    try:
        posts = api.by_sound(sound_url, count=50)
        last_five = posts[:5]
    except Exception as e:
        print("Ошибка при получении видео:", e)
        last_five = []

    if not last_five:
        await callback.answer("❌ Видео пока нет", show_alert=True)
        return

    text = f"🎬 Последние 5 видео под звуком {name}:\n"
    for i, post in enumerate(last_five, start=1):
        video_link = f"https://www.tiktok.com/@{post['author']['uniqueId']}/video/{post['id']}"
        text += f"{i}. {video_link}\n"

    await callback.message.answer(text)
    await callback.answer()

# --- Запуск бота ---
async def main():
    asyncio.create_task(check_new_videos())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
