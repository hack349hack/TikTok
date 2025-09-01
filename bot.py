import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from TikTokApi import TikTokApi

TOKEN = os.getenv("TOKEN")  # Токен бота
OWNER_ID = None

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# --- FSM ---
class AddSoundStates(StatesGroup):
    waiting_for_url = State()

# --- Хранилища ---
sound_list = []  # [{'id': sound_id, 'name': name}]
seen_videos = {}  # sound_id: set(video_urls)

# --- Клавиатуры ---
def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound")],
        ]
    )

def back_to_main():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 На главную", callback_data="back_main")]]
    )

# --- Обработчики ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=main_keyboard())

@dp.callback_query(lambda c: c.data == "add_sound")
async def add_sound_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришли ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    # Получаем ID звука из ссылки
    if "music/" in url:
        sound_id = url.split("music/")[1].split("?")[0]
    elif "tiktok.com/t/" in url:
        sound_id = url.split("t/")[1].split("/")[0]
    else:
        await message.answer("❌ Не удалось распознать ссылку на звук.")
        return

    sound_list.append({"id": sound_id, "name": f"Звук {len(sound_list)+1}"})
    seen_videos[sound_id] = set()
    await message.answer(f"✅ Звук добавлен: {sound_id}", reply_markup=main_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data == "back_main")
async def back_main_cb(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_keyboard())
    await callback.answer()

# --- Проверка новых видео ---
async def check_videos_loop():
    async with TikTokApi() as api:
        while True:
            for sound in sound_list:
                sound_id = sound['id']
                try:
                    videos = await api.video.by_sound(sound_id=sound_id, count=5)
                    new_videos = []
                    for v in videos:
                        url = v['video']['playAddr']
                        if url not in seen_videos[sound_id]:
                            seen_videos[sound_id].add(url)
                            new_videos.append(url)

                    if new_videos and OWNER_ID:
                        text = f"🆕 Новые видео под звуком {sound.get('name')}:\n"
                        for u in new_videos:
                            text += f"{u}\n"
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text="🏠 На главную", callback_data="back_main")]]
                        )
                        await bot.send_message(OWNER_ID, text=text, reply_markup=keyboard)
                except Exception as e:
                    print("Ошибка TikTokApi:", e)
            await asyncio.sleep(60)  # Проверка каждые 60 секунд

# --- Запуск ---
async def main():
    asyncio.create_task(check_videos_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
