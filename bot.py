import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import os
import json

# === НАСТРОЙКИ ===
TOKEN = os.getenv("TOKEN", "8098428478:AAGJJKaREHjQgGPFudgyH1pc_UzzqJUrcgE")
CHECK_INTERVAL = 300  # Проверка новых видео каждые N секунд
HISTORY_FILE = 'seen_videos.json'
SOUNDS_FILE = 'sounds.json'
SOUNDS_PER_PAGE = 5  # Кол-во звуков на одной странице

bot = Bot(token=TOKEN)
dp = Dispatcher()
OWNER_ID = None
rename_state = {}  # Для хранения состояния переименования
seen_videos = {}
SOUND_URLS = []  # Список словарей: [{'url':..., 'name':...}]

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

# === КЛАВИАТУРА ===
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton('➕ Добавить звук'), KeyboardButton('📃 Список звуков')]
    ],
    resize_keyboard=True
)

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
                        time_tag = a.find_next("span")
                        try:
                            video_time = datetime.strptime(time_tag.text.strip(), '%Y-%m-%d %H:%M')
                        except:
                            video_time = datetime.now()

                        if sound_url not in seen_videos:
                            seen_videos[sound_url] = []

                        if video_url not in seen_videos[sound_url] and video_time > datetime.now() - timedelta(days=1):
                            seen_videos[sound_url].append(video_url)
                            with open(HISTORY_FILE, 'w') as f:
                                json.dump(seen_videos, f)

                            # Миниатюра видео
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
                                    [InlineKeyboardButton(text="🗑 Удалить звук", callback_data=f"remove_sound_{idx}"),
                                     InlineKeyboardButton(text="✏️ Переименовать звук", callback_data=f"rename_sound_{idx}")]
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

# === СТАРТ БОТА ===
@dp.message(Command("start"))
async def start_cmd(message: Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=keyboard)

# === ДОБАВЛЕНИЕ ЗВУКА ===
@dp.message(Command("add_sound"))
async def add_sound_cmd(message: Message):
    global SOUND_URLS
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2:
        url = parts[1]
        name = parts[2] if len(parts) == 3 else None
        SOUND_URLS.append({'url': url, 'name': name})
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await message.answer(f"✅ Звук добавлен: {name or url}")
    else:
        await message.answer("❌ Использование: /add_sound <ссылка> [название]")

# === ОТПРАВКА СТРАНИЦЫ СО СПИСКОМ ЗВУКОВ ===
async def send_sounds_page(message: Message, page: int = 0):
    start = page * SOUNDS_PER_PAGE
    end = start + SOUNDS_PER_PAGE
    sounds_page = SOUND_URLS[start:end]

    if not sounds_page:
        await message.answer("❌ На этой странице звуков нет.")
        return

    text = "📃 Список звуков:\n"
    for i, sound in enumerate(sounds_page, start=start + 1):
        name = sound.get('name') or 'Без имени'
        text += f"{i}. {name} — {sound['url']}\n"

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    for i, sound in enumerate(sounds_page, start=start):
        inline_keyboard.add(
            InlineKeyboardButton(text=f"🗑 {sound.get('name') or 'Без имени'}", callback_data=f"remove_sound_{i}"),
            InlineKeyboardButton(text=f"✏️ {sound.get('name') or 'Без имени'}", callback_data=f"rename_sound_{i}")
        )

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'page_{page-1}'))
    if end < len(SOUND_URLS):
        nav_buttons.append(InlineKeyboardButton(text='➡️ Вперёд', callback_data=f'page_{page+1}'))
    if nav_buttons:
        inline_keyboard.row(*nav_buttons)

    await message.answer(text, reply_markup=inline_keyboard)

# === ОБРАБОТКА КНОПОК ===
@dp.message()
async def handle_buttons(message: Message):
    if message.text == '➕ Добавить звук':
        await message.answer('Используй команду /add_sound <ссылка> [название]')
    elif message.text == '📃 Список звуков':
        await send_sounds_page(message, page=0)

@dp.callback_query(lambda c: c.data.startswith('page_'))
async def callback_page(callback: CallbackQuery):
    page = int(callback.data.split('_')[1])
    await send_sounds_page(callback.message, page)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("remove_sound_"))
async def callback_remove_sound(callback: CallbackQuery):
    global SOUND_URLS
    idx = int(callback.data.split("_")[-1])
    if 0 <= idx < len(SOUND_URLS):
        removed = SOUND_URLS.pop(idx)
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        name = removed.get('name') or removed['url']
        await callback.message.edit_text(f"🗑 Звук удалён: {name}", reply_markup=None)
        await callback.answer("Звук удалён")

@dp.callback_query(lambda c: c.data.startswith("rename_sound_"))
async def callback_rename_sound(callback: CallbackQuery):
    idx = int(callback.data.split("_")[-1])
    if 0 <= idx < len(SOUND_URLS):
        rename_state[callback.from_user.id] = idx
        await callback.message.answer("✏️ Введи новое имя для этого звука:")
        await callback.answer()

@dp.message()
async def handle_rename(message: Message):
    if message.from_user.id in rename_state:
        idx = rename_state.pop(message.from_user.id)
        SOUND_URLS[idx]['name'] = message.text
        with open(SOUNDS_FILE, 'w') as f:
            json.dump(SOUND_URLS, f)
        await message.answer(f"✅ Звук переименован: {message.text}")
        return

# === ЗАПУСК БОТА ===
async def main():
    asyncio.create_task(check_new_videos())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
