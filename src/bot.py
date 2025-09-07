import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from settings import SETTINGS
from tiktok import music_id_from_input, fetch_music_videos

bot = Bot(token=SETTINGS.bot_token)
dp = Dispatcher()

# Хранилище активных трекеров
trackers = {}  # user_id -> {music_id, last_ts}


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎵 Отслеживать звук", callback_data="track_sound")],
    ])


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу тебе отслеживать новые видео по звуку TikTok.\n"
        "Нажми кнопку ниже, чтобы выбрать звук.",
        reply_markup=main_menu()
    )


@dp.callback_query(lambda c: c.data == "track_sound")
async def process_track_sound(callback: types.CallbackQuery):
    await callback.message.answer("🎵 Отправь ссылку или ID звука TikTok:")
    await callback.answer()


@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    music_id = music_id_from_input(message.text)

    if not music_id:
        await message.answer("❌ Не удалось распознать sound ID. Пришли корректную ссылку или число.")
        return

    await message.answer(f"🔎 Ищу видео по звуку `{music_id}`...")

    videos, last_ts = await fetch_music_videos(music_id)
    if not videos:
        await message.answer("❌ Не удалось найти видео с этим звуком.")
        return

    # Сохраняем трекер
    trackers[user_id] = {"music_id": music_id, "last_ts": last_ts}

    # Отправляем первые найденные видео
    text = "\n".join(f"▶️ {v['url']}" for v in videos)
    await message.answer(f"Нашёл {len(videos)} видео:\n\n{text}\n\n✅ Теперь я буду следить за новыми!")


async def tracker_loop():
    while True:
        for user_id, data in list(trackers.items()):
            music_id = data["music_id"]
            last_ts = data["last_ts"]

            try:
                videos, new_last_ts = await fetch_music_videos(music_id)
            except Exception as e:
                print(f"Ошибка парсинга для {music_id}: {e}")
                continue

            new_videos = [v for v in videos if v["ts"] > last_ts]
            if new_videos:
                trackers[user_id]["last_ts"] = max(v["ts"] for v in new_videos)
                text = "\n".join(f"🆕 {v['url']}" for v in new_videos)
                await bot.send_message(user_id, f"🎬 Новые видео по звуку {music_id}:\n\n{text}")

        await asyncio.sleep(60)  # проверка раз в минуту


async def main():
    asyncio.create_task(tracker_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
