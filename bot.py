import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from TikTokApi import TikTokApi

# --- Переменные окружения ---
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("❌ Укажи TOKEN в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Глобальные переменные ---
OWNER_ID = None
SOUND_URLS = []  # сюда пользователь добавляет ссылки на звуки
SEEN_VIDEOS = {}  # хранение последних увиденных видео/фото

# --- FSM состояния ---
class AddSoundStates(StatesGroup):
    waiting_for_url = State()

# --- Клавиатуры ---
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("➕ Добавить звук", callback_data="add_sound"),
             InlineKeyboardButton("📃 Список звуков", callback_data="list_sounds")]
        ]
    )

def build_sounds_keyboard():
    kb = []
    for idx, sound in enumerate(SOUND_URLS):
        kb.append([InlineKeyboardButton(f"🎬 {sound}", callback_data=f"check_{idx}")])
    kb.append([InlineKeyboardButton("На главную", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def build_videos_keyboard(videos):
    kb = []
    for v in videos:
        kb.append([InlineKeyboardButton("▶️ Открыть", url=v)])
    kb.append([InlineKeyboardButton("На главную", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- Проверка новых видео/фото ---
async def check_new_videos():
    api = TikTokApi()
    while True:
        for idx, sound_url in enumerate(SOUND_URLS):
            try:
                videos = api.by_sound(sound_url, count=5)
                new_items = []
                for video in videos:
                    url = video['video']['playAddr']
                    if sound_url not in SEEN_VIDEOS:
                        SEEN_VIDEOS[sound_url] = set()
                    if url not in SEEN_VIDEOS[sound_url]:
                        SEEN_VIDEOS[sound_url].add(url)
                        new_items.append(url)
                if new_items and OWNER_ID:
                    for item in new_items:
                        await bot.send_message(
                            chat_id=OWNER_ID,
                            text=f"🆕 Новое видео/фото под звуком {sound_url}\n{item}",
                            reply_markup=build_videos_keyboard(new_items)
                        )
            except Exception as e:
                print(f"Ошибка при получении видео для {sound_url}: {e}")
        await asyncio.sleep(60)

# --- Хендлеры ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def add_sound(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_url(message: types.Message, state: FSMContext):
    SOUND_URLS.append(message.text)
    await message.answer(f"✅ Звук добавлен: {message.text}", reply_markup=get_main_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data == "list_sounds")
async def list_sounds(callback: types.CallbackQuery):
    if not SOUND_URLS:
        await callback.message.answer("❌ Список пуст")
    else:
        await callback.message.answer("📃 Список звуков:", reply_markup=build_sounds_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("check_"))
async def show_videos(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    sound_url = SOUND_URLS[idx]
    api = TikTokApi()
    try:
        videos = api.by_sound(sound_url, count=5)
        video_urls = [v['video']['playAddr'] for v in videos]
        await callback.message.answer(
            f"🎬 Последние видео/фото под звуком {sound_url}:",
            reply_markup=build_videos_keyboard(video_urls)
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при получении видео: {e}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "main")
async def go_main(callback: types.CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())
    await callback.answer()

# --- Запуск ---
async def main():
    asyncio.create_task(check_new_videos())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
