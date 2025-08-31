import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound"),
                InlineKeyboardButton(
                    text="📃 Список звуков",
                    callback_data="list_sounds" if SOUND_URLS else "no_sounds"
                )
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
            InlineKeyboardButton(
                text=f"🗑 {sound.get('name') or 'Без имени'}",
                callback_data=f"remove_sound_{i}"
            ),
            InlineKeyboardButton(
                text=f"✏️ {sound.get('name') or 'Без имени'}",
                callback_data=f"rename_sound_{i}"
            ),
            InlineKeyboardButton(
                text=f"🎬 5 последних видео",
                callback_data=f"last_videos_{i}"
            ),
            InlineKeyboardButton(
                text=f"🆕 Свежие видео",
                callback_data=f"fresh_videos_{i}"
            )
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

# === ПРОВЕРКА НОВЫХ ВИДЕО ===
async def check_new_videos():
    global seen_videos, SOUND_URLS
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

                            try:
                                r_video = requests.get(video_url, headers={"User-Agent": "Mozilla/5.0"})
                                soup_video = BeautifulSoup(r_video.text, "html.parser")
                                meta_thumb = soup_video.find("meta", property="og:image")
                                thumbnail_url = meta_thumb["content"] if meta_thumb else None
                            except:
                                thumbnail_url = None

                            keyboard_inline = InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [InlineKeyboardButton(text="▶️ Открыть в TikTok", url=video_url)],
                                    [
                                        InlineKeyboardButton(text="🗑 Удалить звук", callback_data=f"remove_sound_{idx}"),
                                        InlineKeyboardButton(text="✏️ Переименовать звук", callback_data=f"rename_sound_{idx}")
                                    ]
                                ]
                            )

                            caption_text = f"🆕 Новый ролик под звуком: {sound_name}"

                            if thumbnail_url:
                                await bot.send_photo(chat_id=OWNER_ID, photo=thumbnail_url, caption=caption_text, reply_markup=keyboard_inline)
                            else:
                                await bot.send_message(chat_id=OWNER_ID, text=caption_text, reply_markup=keyboard_inline)

            except Exception as e:
                print("Ошибка:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# === ОБРАБОТЧИКИ КОМАНД ===
@dp.message(Command("start"))
async def start_cmd(message: Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def inline_add_sound(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_get_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("✏️ Теперь пришли название звука (или напиши 'нет' для пропуска):")
    await state.set_state(AddSoundStates.waiting_for_name)

@dp.message(AddSoundStates.waiting_for_name)
async def add_sound_get_name(message: Message, state: FSMContext):
    data = await state.get_data()
    url = data['url']
    name = message.text if message.text.lower() != 'нет' else None
    SOUND_URLS.append({'url': url, 'name': name})
    with open(SOUNDS_FILE, 'w') as f:
        json.dump(SOUND_URLS, f)
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=get_main_keyboard())
    await state.clear()

# === CALLBACK: последние видео из истории ===
@dp.callback_query(lambda c: c.data.startswith("last_videos_"))
async def callback_last_videos(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    sound_url = SOUND_URLS[idx]['url']
    last_videos = seen_videos.get(sound_url, [])[-5:]
    if not last_videos:
        await callback.answer("❌ Видео пока нет", show_alert=True)
        return
    text = f"🎬 5 последних видео под звуком {SOUND_URLS[idx].get('name') or 'Без имени'}:\n"
    for i, v in enumerate(reversed(last_videos), start=1):
        text += f"{i}. {v}\n"
    await callback.message.answer(text)
    await callback.answer()

# === CALLBACK: свежие видео с сайта ===
@dp.callback_query(lambda c: c.data.startswith("fresh_videos_"))
async def callback_fresh_videos(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    sound_url = SOUND_URLS[idx]['url']
    try:
        r = requests.get(sound_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        video_elements = [a["href"] for a in soup.find_all("a", href=True) if "/video/" in a["href"]]
        last_5 = video_elements[-5:]
        if not last_5:
            await callback.answer("❌ Видео не найдено", show_alert=True)
            return
        text = f"🎬 5 свежих видео под звуком {SOUND_URLS[idx].get('name') or 'Без имени'}:\n"
        for i, v in enumerate(reversed(last_5), start=1):
            text += f"{i}. {v}\n"
        await callback.message.answer(text)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

# === CALLBACK: список звуков ===
@dp.callback_query(lambda c: c.data.startswith("list_sounds"))
async def callback_list_sounds(callback: CallbackQuery):
    kb = build_sounds_keyboard()
    if kb:
        await callback.message.answer("📃 Список звуков:", reply_markup=kb)
    else:
        await callback.message.answer("❌ Список пуст.")
    await callback.answer()

# === CALLBACK: нет звуков ===
@dp.callback_query(lambda c: c.data == "no_sounds")
async def callback_no_sounds(callback: CallbackQuery):
    await callback.answer("❌ Список звуков пуст", show_alert=True)

# === CALLBACK: навигация по страницам ===
@dp.callback_query(lambda c: c.data.startswith("page_"))
async def callback_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    kb = build_sounds_keyboard(page)
    if kb:
        await callback.message.edit_reply_markup(kb)
    await callback.answer()

# === CALLBACK: удалить звук ===
@dp.callback_query(lambda c: c.data.startswith("remove_sound_"))
async def callback_remove_sound(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    if idx < len(SOUND_URLS):
        removed = SOUND_URLS.pop(idx)
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await callback.message.answer(f"🗑 Звук удален: {removed.get('name') or removed['url']}")
        kb = build_sounds_keyboard()
        if kb:
            await callback.message.edit_reply_markup(kb)
    await callback.answer()

# === CALLBACK: переименовать звук ===
@dp.callback_query(lambda c: c.data.startswith("rename_sound_"))
async def callback_rename_sound(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    rename_state[callback.from_user.id] = idx
    await callback.message.answer("✏️ Введи новое название звука:")
    await state.set_state(AddSoundStates.waiting_for_name)
    await callback.answer()

# === FSM: переименование звука ===
@dp.message(AddSoundStates.waiting_for_name)
async def rename_sound(message: Message, state: FSMContext):
    idx = rename_state.get(message.from_user.id)
    if idx is not None and idx < len(SOUND_URLS):
        SOUND_URLS[idx]['name'] = message.text
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await message.answer(f"✅ Звук переименован: {message.text}", reply_markup=get_main_keyboard())
        rename_state.pop(message.from_user.id)
    await state.clear()

# === ЗАПУСК БОТА ===
if __name__ == "__main__":
    # Запускаем проверку новых видео параллельно
    asyncio.create_task(check_new_videos())
    # Стартуем long polling
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
