import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from .settings import SETTINGS
from .storage import open_db, list_sounds, upsert_sound, subscribe, unsubscribe
from .tiktok import fetch_music_videos, music_id_from_input, MUSIC_URL_FMT

bot = Bot(token=SETTINGS.telegram_token)
dp = Dispatcher()

class TrackSound(StatesGroup):
    waiting_for_link = State()

class TrackHashtag(StatesGroup):
    waiting_for_tag = State()

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎵 Отслеживать звук", callback_data="track_sound")],
        [InlineKeyboardButton("📄 Список отслеживаемых", callback_data="list_sounds")],
        [InlineKeyboardButton("❌ Удалить звук", callback_data="untrack_sound")],
        [InlineKeyboardButton("#️⃣ Отслеживать хэштег", callback_data="track_hashtag")],
    ])

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await m.reply(
        "Добро пожаловать! Используйте кнопки ниже:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query()
async def cb_handler(c: CallbackQuery, state: FSMContext):
    data = c.data
    if data == "track_sound":
        await c.message.answer("Пришлите ссылку или ID звука:", parse_mode="HTML")
        await state.set_state(TrackSound.waiting_for_link)
    elif data == "track_hashtag":
        await c.message.answer("Пришлите хэштег (без #):", parse_mode="HTML")
        await state.set_state(TrackHashtag.waiting_for_tag)
    elif data == "list_sounds":
        with open_db() as conn:
            sounds = list_sounds(conn)
        if not sounds:
            await c.message.answer("Список пуст.", parse_mode="HTML")
        else:
            kb = InlineKeyboardMarkup()
            for mid, title, _ in sounds:
                kb.add(InlineKeyboardButton(text=f"{title or mid} ❌", callback_data=f"del_sound:{mid}"))
            await c.message.answer("Список отслеживаемых звуков:", reply_markup=kb, parse_mode="HTML")
    elif data.startswith("del_sound:"):
        mid = data.split(":", 1)[1]
        with open_db() as conn:
            unsubscribe(conn, c.message.chat.id, "sound", mid)
        await c.message.answer(f"Удалено: {mid}", parse_mode="HTML")

@dp.message(TrackSound.waiting_for_link)
async def fsm_track_sound(m: Message, state: FSMContext):
    mid = music_id_from_input(m.text)
    if not mid:
        await m.reply("Не удалось распознать music_id.", parse_mode="HTML")
        return
    with open_db() as conn:
        upsert_sound(conn, mid, title=f"sound {mid}", last_ts=0)
        subscribe(conn, m.chat.id, "sound", mid)
    await m.reply(
        f"✅ Звук добавлен: <code>{mid}</code>\n{MUSIC_URL_FMT.format(mid=mid)}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

@dp.message(TrackHashtag.waiting_for_tag)
async def fsm_track_hashtag(m: Message, state: FSMContext):
    tag = m.text.strip().lstrip("#")
    with open_db() as conn:
        conn.execute("INSERT OR IGNORE INTO tracked_hashtags(tag) VALUES(?)", (tag,))
        subscribe(conn, m.chat.id, "hashtag", tag)
    await m.reply(f"✅ Хэштег добавлен: <b>#{tag}</b>", reply_markup=main_menu(), parse_mode="HTML")
    await state.clear()

async def scheduler_loop():
    while True:
        try:
            with open_db() as conn:
                sound_ids = [r[0] for r in conn.execute("SELECT music_id FROM tracked_sounds").fetchall()]
            for mid in sound_ids:
                videos, last_ts = await fetch_music_videos(mid, http_proxy=SETTINGS.http_proxy, limit=10)
                with open_db() as conn:
                    subs = [r[0] for r in conn.execute(
                        "SELECT chat_id FROM subscriptions WHERE type='sound' AND identifier=?", (mid,)
                    ).fetchall()]
                for video in videos:
                    if int(video.get("ts", 0)) > last_ts:
                        for chat_id in subs:
                            await bot.send_message(chat_id, f"Новое видео под звук {mid}:\n{video['url']}", parse_mode="HTML")
                with open_db() as conn:
                    conn.execute("UPDATE tracked_sounds SET last_ts=? WHERE music_id=?", (last_ts, mid))
        except Exception as e:
            if SETTINGS.admin_chat_id:
                await bot.send_message(SETTINGS.admin_chat_id, f"Scheduler error: {e}", parse_mode="HTML")
        await asyncio.sleep(SETTINGS.poll_interval_sec)

async def main():
    if not SETTINGS.telegram_token:
        raise SystemExit("TELEGRAM_TOKEN пустой")
    asyncio.create_task(scheduler_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
