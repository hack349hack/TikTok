import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
import os
import json

# === ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
TOKEN = os.getenv("TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))

# === НАСТРОЙКИ ===
HISTORY_FILE = 'seen_videos.json'
SOUNDS_FILE = 'sounds.json'
SOUNDS_PER_PAGE = 5

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

OWNER_ID = None
rename_state = {}
seen_videos = {}
SOUND_URLS = []

# === ЗАГРУЗКА ИСТОРИИ ===
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'r') as f:
        try:
            seen_videos = json.load(f)
        except:
            seen_videos = {}

# === ЗАГРУЗКА ЗВУКОВ ===
if os.path.exists(SOUNDS_FILE):
    with open(SOUNDS_FILE, 'r') as f:
        try:
            SOUND_URLS = json.load(f)
        except:
            SOUND_URLS = []

# === FSM СОСТОЯНИЯ ===
class AddSoundStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()

# === КЛАВИАТУРЫ ===
def get_main_keyboard():
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound"),
                types.InlineKeyboardButton(text="📃 Список звуков", callback_data="list_sounds")
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
            types.InlineKeyboardButton(
                text=f"🗑 {sound.get('name') or 'Без имени'}",
                callback_data=f"remove_sound_{i}"
            ),
            types.InlineKeyboardButton(
                text=f"✏️ {sound.get('name') or 'Без имени'}",
                callback_data=f"rename_sound_{i}"
            ),
            types.InlineKeyboardButton(
                text=f"🎬 5 последних видео (история)",
                callback_data=f"last_videos_history_{i}"
            ),
            types.InlineKeyboardButton(
                text=f"🎬 5 последних видео (новое)",
                callback_data=f"last_videos_new_{i}"
            )
        ])

    inline_keyboard.append([types.InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound")])

    nav_buttons = []
    if start > 0:
        nav_buttons.append(types.InlineKeyboardButton(text='⬅️ Назад', callback_data=f'page_{page-1}'))
    if end < len(SOUND_URLS):
        nav_buttons.append(types.InlineKeyboardButton(text='➡️ Вперёд', callback_data=f'page_{page+1}'))
    if nav_buttons:
        inline_keyboard.append(nav_buttons)

    return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# === ПРОВЕРКА НОВЫХ ВИДЕО ===
async def check_new_videos():
    global seen_videos, SOUND_URLS, OWNER_ID
    while True:
        for idx, sound in enumerate(SOUND_URLS):
            sound_url = sound['url']
            sound_name = sound.get('name') or f'#{idx+1}'
            try:
                r = requests.get(sound_url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")
                video_elements = soup.find_all("a", href=True)
                for a in video_elements:
                    if "/video/" in a["href"]:
                        video_url = a["href"]
                        if sound_url not in seen_videos:
                            seen_videos[sound_url] = []
                        if video_url not in seen_videos[sound_url]:
                            seen_videos[sound_url].append(video_url)
                            with open(HISTORY_FILE, 'w') as f:
                                json.dump(seen_videos, f)

                            keyboard_inline = types.InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [types.InlineKeyboardButton(text="▶️ Открыть в TikTok", url=video_url)],
                                    [
                                        types.InlineKeyboardButton(text="🗑 Удалить звук", callback_data=f"remove_sound_{idx}"),
                                        types.InlineKeyboardButton(text="✏️ Переименовать звук", callback_data=f"rename_sound_{idx}")
                                    ]
                                ]
                            )
                            caption_text = f"🆕 Новый ролик под звуком: {sound_name}"
                            if OWNER_ID:
                                await bot.send_message(chat_id=OWNER_ID, text=caption_text, reply_markup=keyboard_inline)

            except Exception as e:
                print("Ошибка:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# === ОБРАБОТЧИКИ КОМАНД ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

# Добавление звука
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
    name = message.text if message.text.lower() != 'нет' else None
    SOUND_URLS.append({'url': url, 'name': name})
    with open(SOUNDS_FILE, 'w') as f:
        json.dump(SOUND_URLS, f)
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=get_main_keyboard())
    await state.clear()

# Список звуков
@dp.callback_query(lambda c: c.data == "list_sounds")
async def callback_list_sounds(callback: types.CallbackQuery):
    kb = build_sounds_keyboard()
    if kb:
        await callback.message.answer("📃 Список звуков:", reply_markup=kb)
    else:
        await callback.message.answer("❌ Список пуст")
    await callback.answer()

# Удаление и переименование
@dp.callback_query(lambda c: c.data.startswith("remove_sound_"))
async def callback_remove_sound(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    if 0 <= idx < len(SOUND_URLS):
        removed = SOUND_URLS.pop(idx)
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await callback.message.edit_text(f"🗑 Звук удалён: {removed.get('name') or removed['url']}", reply_markup=get_main_keyboard())
        await callback.answer()

rename_state = {}
@dp.callback_query(lambda c: c.data.startswith("rename_sound_"))
async def callback_rename_sound(callback: types.CallbackQuery):
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
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await message.answer(f"✅ Звук переименован: {message.text}", reply_markup=get_main_keyboard())
        return

# Последние видео
@dp.callback_query(lambda c: c.data.startswith("last_videos_"))
async def callback_last_videos(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    mode = parts[2]  # history или new
    idx = int(parts[3])
    sound_url = SOUND_URLS[idx]['url']

    if mode == "history":
        last_videos = seen_videos.get(sound_url, [])[-5:]
    else:  # "new"
        try:
            r = requests.get(sound_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            video_elements = [a["href"] for a in soup.find_all("a", href=True) if "/video/" in a["href"]]
            last_videos = video_elements[:5]
        except Exception as e:
            print("Ошибка при парсинге последних видео:", e)
            last_videos = []

    if not last_videos:
        await callback.answer("❌ Видео пока нет", show_alert=True)
        return

    text = f"🎬 5 последних видео под звуком {SOUND_URLS[idx].get('name') or 'Без имени'} ({mode}):\n"
    for i, v in enumerate(last_videos, start=1):
        text += f"{i}. {v}\n"

    await callback.message.answer(text)
    await callback.answer()

# === ЗАПУСК БОТА ===
async def main():
    asyncio.create_task(check_new_videos())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
