from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Iterable

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram import Bot

from .settings import SETTINGS
from .storage import (
    open_db, list_sounds, upsert_sound, get_sound_state, update_sound_state,
    subscribe, unsubscribe, subscribers,
)
from .tiktok import fetch_music_videos, music_id_from_input, discover_new_sounds_by_hashtag, MUSIC_URL_FMT


# === Инициализация бота ===
bot = Bot(
    token=SETTINGS.telegram_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


HELP = (
    "<b>TikTok Sound Watcher</b>\n\n"
    "/track_sound &lt;music_url|music_id&gt; — отслеживать звук\n"
    "/untrack_sound &lt;music_id&gt; — перестать\n"
    "/list — список звуков\n"
    "/track_hashtag &lt;tag&gt; — искать новые звуки по хэштегу\n"
    "/untrack_hashtag &lt;tag&gt; — перестать отслеживать хэштег\n"
    "/set_interval &lt;минуты&gt; — период рассылки (по умолчанию 3)\n"
)


# === Команды ===
@dp.message(Command("start"))
async def cmd_start(m: Message):
    await m.reply(HELP)


@dp.message(Command("list"))
async def cmd_list(m: Message):
    with open_db() as conn:
        sounds = list_sounds(conn)
    if not sounds:
        await m.reply("Список пуст. Добавьте через /track_sound <music_id|url>")
        return
    lines = ["<b>Звуки:</b>"]
    for mid, title, last_ts in sounds:
        dt = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if last_ts else "—"
        lines.append(f"• <code>{mid}</code> — {title or '—'} (последний: {dt})")
    await m.reply("\n".join(lines))


@dp.message(Command("track_sound"))
async def cmd_track_sound(m: Message):
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2:
        await m.reply("Укажите music_id или ссылку на страницу звука.")
        return
    mid = music_id_from_input(args[1])
    if not mid:
        await m.reply("Не удалось распознать music_id.")
        return
    with open_db() as conn:
        upsert_sound(conn, mid, title=f"sound {mid}", last_ts=0)
        subscribe(conn, m.chat.id, "sound", mid)
    await m.reply(f"Добавлено. Подписал чат на звук <code>{mid}</code> — {MUSIC_URL_FMT.format(mid=mid)}")


@dp.message(Command("untrack_sound"))
async def cmd_untrack_sound(m: Message):
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2:
        await m.reply("Укажите music_id")
        return
    mid = music_id_from_input(args[1]) or args[1]
    with open_db() as conn:
        unsubscribe(conn, m.chat.id, "sound", mid)
    await m.reply(f"Ок, чат отписан от <code>{mid}</code>.")


@dp.message(Command("track_hashtag"))
async def cmd_track_hashtag(m: Message):
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2:
        await m.reply("Укажите хэштег без #")
        return
    tag = args[1].strip().lstrip("#")
    with open_db() as conn:
        conn.execute("INSERT OR IGNORE INTO tracked_hashtags(tag) VALUES(?)", (tag,))
        subscribe(conn, m.chat.id, "hashtag", tag)
    await m.reply(f"Добавлено. Подписал чат на хэштег <b>#{tag}</b>.")


@dp.message(Command("untrack_hashtag"))
async def cmd_untrack_hashtag(m: Message):
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2:
        await m.reply("Укажите хэштег")
        return
    tag = args[1].strip().lstrip("#")
    with open_db() as conn:
        unsubscribe(conn, m.chat.id, "hashtag", tag)
    await m.reply(f"Ок, чат отписан от хэштега <b>#{tag}</b>.")


@dp.message(Command("set_interval"))
async def cmd_set_interval(m: Message):
    args = (m.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await m.reply("Укажите число минут, например: /set_interval 3")
        return
    minutes = int(args[1].strip())
    import os
    os.environ["POLL_INTERVAL_SEC"] = str(minutes * 60)
    await m.reply(f"Интервал поставлен на {minutes} мин.")


# === Асинхронный шедулер ===
async def notify_new_videos(music_id: str):
    from .settings import SETTINGS
    items, title = await fetch_music_videos(music_id, http_proxy=SETTINGS.http_proxy, limit=50)

    with open_db() as conn:
        last_ts, last_ids = get_sound_state(conn, music_id)
        new_items = [it for it in items if it.create_time > (last_ts or 0) and it.id not in last_ids]
        if last_ts == 0:
            new_items = new_items[:3]
        if items:
            upsert_sound(conn, music_id, title or f"sound {music_id}", last_ts=max(last_ts, items[0].create_time))
        if new_items:
            update_sound_state(conn, music_id, max(x.create_time for x in items) if items else last_ts,
                               last_ids | {x.id for x in new_items})
            chats = subscribers(conn, "sound", music_id)
        else:
            chats = []

    if not new_items:
        return

    for it in sorted(new_items, key=lambda x: x.create_time):
        text = (
            f"<b>Новый ролик под звук</b> <code>{music_id}</code>\n"
            f"<a href='{it.link()}'>Видео</a> | {datetime.fromtimestamp(it.create_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Автор: @{it.author}\n"
            f"Описание: {it.desc[:500]}\n"
            f"Звук: {MUSIC_URL_FMT.format(mid=music_id)}"
        )
        await asyncio.gather(*[bot.send_message(chat_id, text) for chat_id in chats])


async def sweep_hashtags():
    from .settings import SETTINGS
    import json
    with open_db() as conn:
        cur = conn.execute("SELECT tag, last_video_ids FROM tracked_hashtags")
        rows = cur.fetchall()
    for tag, last_ids_json in rows:
        try:
            pairs = await discover_new_sounds_by_hashtag(tag, http_proxy=SETTINGS.http_proxy, limit=50)
        except Exception as e:
            if SETTINGS.admin_chat_id:
                await bot.send_message(SETTINGS.admin_chat_id, f"Ошибка hashtag {tag}: {e}")
            continue
        new_pairs = []
        seen_ids = set()
        try:
            seen_ids = set(json.loads(last_ids_json or "[]"))
        except Exception:
            seen_ids = set()
        for mid, title in pairs:
            if mid not in seen_ids:
                new_pairs.append((mid, title))
        if new_pairs:
            with open_db() as conn:
                conn.execute(
                    "UPDATE tracked_hashtags SET last_video_ids=? WHERE tag=?",
                    (json.dumps(list({*seen_ids, *[mid for mid, _ in pairs]})), tag),
                )
                chats = subscribers(conn, "hashtag", tag)
            for mid, title in new_pairs[:10]:
                text = (
                    f"<b>Новый звук по хэштегу</b> #{tag}\n"
                    f"<code>{mid}</code> — {title or '—'}\n{MUSIC_URL_FMT.format(mid=mid)}"
                )
                await asyncio.gather(*[bot.send_message(c, text) for c in chats])


async def scheduler_loop():
    while True:
        try:
            with open_db() as conn:
                cur = conn.execute("SELECT music_id FROM tracked_sounds")
                sound_ids = [r[0] for r in cur.fetchall()]
            for mid in sound_ids:
                try:
                    await notify_new_videos(mid)
                except Exception as e:
                    if SETTINGS.admin_chat_id:
                        await bot.send_message(SETTINGS.admin_chat_id, f"Ошибка sound {mid}: {e}")
            await sweep_hashtags()
        except Exception as e:
            if SETTINGS.admin_chat_id:
                await bot.send_message(SETTINGS.admin_chat_id, f"Scheduler error: {e}")
        await asyncio.sleep(SETTINGS.poll_interval_sec)


async def main():
    if not SETTINGS.telegram_token:
        raise SystemExit("TELEGRAM_TOKEN is empty")
    asyncio.create_task(scheduler_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
