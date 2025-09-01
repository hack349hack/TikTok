import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from TikTokApi import TikTokApi

# --- Переменные ---
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

OWNER_ID = None
sound_list = []  # Сюда добавляем словари {'url':..., 'name':...}
rename_state = {}

# --- FSM ---
class AddSoundStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_name = State()

# --- Клавиатуры ---
def main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить звук", callback_data="add_sound")],
        [InlineKeyboardButton(text="📃 Список звуков", callback_data="list_sounds")]
    ])
    return kb

def sounds_keyboard():
    kb = InlineKeyboardMarkup()
    for i, sound in enumerate(sound_list):
        kb.add(InlineKeyboardButton(text=f"{i+1}. {sound.get('name') or 'Без имени'}", callback_data=f"show_{i}"))
    kb.add(InlineKeyboardButton(text="🏠 На главную", callback_data="back_main"))
    return kb

def back_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 На главную", callback_data="back_main")]
    ])

# --- Старт ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен!", reply_markup=main_keyboard())

# --- Добавление звука ---
@dp.callback_query(lambda c: c.data == "add_sound")
async def add_sound_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 Пришлите ссылку на звук TikTok:")
    await state.set_state(AddSoundStates.waiting_for_url)
    await callback.answer()

@dp.message(AddSoundStates.waiting_for_url)
async def add_sound_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("✏️ Теперь пришлите название звука (или напишите 'нет' для пропуска):")
    await state.set_state(AddSoundStates.waiting_for_name)

@dp.message(AddSoundStates.waiting_for_name)
async def add_sound_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    url = data['url']
    name = message.text if message.text.lower() != 'нет' else None
    sound_list.append({'url': url, 'name': name})
    await message.answer(f"✅ Звук добавлен: {name or url}", reply_markup=main_keyboard())
    await state.clear()

# --- Список звуков ---
@dp.callback_query(lambda c: c.data == "list_sounds")
async def list_sounds_cb(callback: CallbackQuery):
    if not sound_list:
        await callback.message.answer("❌ Список пуст")
    else:
        await callback.message.edit_text("📃 Список звуков:", reply_markup=sounds_keyboard())
    await callback.answer()

# --- Просмотр последних видео ---
@dp.callback_query(lambda c: c.data.startswith("show_"))
async def show_sound_cb(callback: CallbackQuery):
    idx = int(callback.data.split("_")[1])
    sound = sound_list[idx]
    url = sound['url']

    try:
        async with TikTokApi() as api:
            posts = api.by_sound(url, count=5)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при получении видео: {e}", reply_markup=back_main_keyboard())
        await callback.answer()
        return

    if not posts:
        await callback.message.answer("❌ Видео пока нет", reply_markup=back_main_keyboard())
        await callback.answer()
        return

    text = f"🎬 5 последних видео под звуком {sound.get('name') or 'Без имени'}:\n"
    for i, p in enumerate(posts, start=1):
        text += f"{i}. https://www.tiktok.com/@{p.author.username}/video/{p.id}\n"

    await callback.message.answer(text, reply_markup=back_main_keyboard())
    await callback.answer()

# --- Назад на главную ---
@dp.callback_query(lambda c: c.data == "back_main")
async def back_main_cb(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_keyboard())
    await callback.answer()

# --- Запуск ---
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
