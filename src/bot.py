from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from aiogram import Dispatcher, Bot
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from .settings import SETTINGS
from .storage import open_db, list_sounds, upsert_sound, subscribe, unsubscribe, subscribers
from .tiktok import fetch_music_videos, music_id_from_input, discover_new_sounds_by_hashtag, MUSIC_URL_FMT

# === Инициализация бота ===
bot = Bot(token=SETTINGS.telegram_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === FSM состояния ===
class TrackSound(StatesGroup):
    waiting_for_link = State()

class TrackHashtag(StatesGroup):
    waiting_for_tag = State()

class SetInterval(StatesGroup):
    waiting_for_minutes = State()

# === Главное меню ===
def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎵 Отслеживать звук", callback_data="track_sound")],
        [InlineKeyboardButton("📄 Список отслеживаемых", callback_data="list_sounds")],
        [InlineKeyboardButton("❌ Удалить звук", callback_data="untrack_sound")],
        [InlineKeyboardButton("#️⃣ Отслеживать хэштег", callback_data="track_hashtag")],
        [InlineKeyboardButton("🗑 Отписаться от хэштега", callback_data="untrack_hashtag")],
        [InlineKeyboardButton("⏱ Интервал рассылки", callback_data="set_interval")],
    ])
    return kb

# === /start ===
@dp.message(Command("start"))
async def cmd_start(m: Message):
    await m.reply("Добро пожаловать! Используйте кнопки ниже для управления ботом:", reply_markup=main_menu())

# === Обработка нажатий ===
@dp.callback_query()
async def cb_handler(c: CallbackQuery, state: FSMContext):
    data = c.data
    if data == "track_sound":
        await c.message.answer("Пришлите ссылку или ID звука:")
        await state.set_state(TrackSound.waiting_for_link)
    elif data == "track_hashtag":
        await c.message.answer("Пришлите хэштег (без #):")
        await state.set_state(TrackHashtag.waiting_for_tag)
    elif data == "list_sounds":
        with open_db() as conn:
            sounds = list_sounds(conn)
        if not sounds:
            await c.message.answer("Список пуст.")
        else:
            kb = InlineKeyboardMarkup()
            for mid, title, _ in sounds:
                kb.add(InlineKeyboardButton(f"{title or mid} ❌", callback_data=f"del_sound:{mid}"))
            await c.message.answer("Список отслеживаемых звуков:", reply_markup=kb)
    elif data.startswith("del_sound:"):
        mid = data.split(":", 1)[1]
        with open_db() as conn:
            unsubscribe(conn, c.message.chat.id, "sound", mid)
        await c.message.answer(f"Удалено: {mid}")
    elif data == "set_interval":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("1 мин", callback_data="interval:60"),
             InlineKeyboardButton("3 мин", callback_data="interval:180"),
             InlineKeyboardButton("5 мин", callback_data="interval:300")],
        ])
        await c.message.answer("Выберите интервал рассылки:", reply_markup=kb)
    elif data.startswith("interval:"):
        sec = int(data.split(":", 1)[1])
        import os
        os.environ["POLL_INTERVAL_SEC"] = str(sec)
        await c.message.answer(f"Интервал обновлён на {sec // 60} мин.")

# === FSM хендлеры ===
@dp.message(TrackSound.waiting_for_link)
async def fsm_track_sound(m: Message, state: FSMContext):
    mid = music_id_from_input(m.text)
    if not mid:
        await m.reply("Не удалось распознать music_id.")
        return
    with open_db() as conn:
        upsert_sound(conn, mid, title=f"sound {mid}", last_ts=0)
        subscribe(conn, m.chat.id, "sound", mid)
    await m.reply(f"✅ Звук добавлен: <code>{mid}</code>\n{MUSIC_URL_FMT.format(mid=mid)}", reply_markup=main_menu())
    await state.clear()

@dp.message(TrackHashtag.waiting_for_tag)
async def fsm_track_hashtag(m: Message, state: FSMContext):
    tag = m.text.strip().lstrip("#")
    with open_db() as conn:
        conn.execute("INSERT OR IGNORE INTO tracked_hashtags(tag) VALUES(?)", (tag,))
        subscribe(conn, m.chat.id, "hashtag", tag)
    await m.reply(f"✅ Хэштег добавлен: <b>#{tag}</b>", reply_markup=main_menu())
    await state.clear()

# === Scheduler для видео/хэштегов ===
async def notify_new_videos(music_id: str):
    items, title = await fetch_music_videos(music_id, http_proxy=SETTINGS.http_proxy, limit=50)
    with open_db() as conn:
        last_ts, last_ids = conn.cursor().execute(
            "SELECT last_ts, last_ids FROM tracked_sounds WHERE music_id=?", (music_id,)
        ).fetchone() or (0, "[]")
    # Здесь можно добавить полноценный update состояния и рассылку пользователям
    # Для простоты оставлено минимально

async def scheduler_loop():
    while True:
        try:
            with open_db() as conn:
                sound_ids = [r[0] for r in conn.execute("SELECT music_id FROM tracked_sounds").fetchall()]
            for mid in sound_ids:
                await notify_new_videos(mid)
            # Тут добавить хэштеги аналогично
        except Exception as e:
            if SETTINGS.admin_chat_id:
                await bot.send_message(SETTINGS.admin_chat_id, f"Scheduler error: {e}")
        await asyncio.sleep(SETTINGS.poll_interval_sec)

# === Main ===
async def main():
    if not SETTINGS.telegram_token:
        raise SystemExit("TELEGRAM_TOKEN пустой")
    asyncio.create_task(scheduler_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
