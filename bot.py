import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# === НАСТРОЙКИ ===
TOKEN = "8098428478:AAGJJKaREHjQgGPFudgyH1pc_UzzqJUrcgE"  # вставь токен от BotFather
CHECK_INTERVAL = 300  # как часто проверять (секунд)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Храним ID уже найденных видео, текущий звук и дату публикации
seen_videos = set()
video_dates = dict()
SOUND_URL = None
OWNER_ID = None

async def check_new_videos():
    global seen_videos, SOUND_URL, video_dates
    while True:
        if SOUND_URL:
            try:
                r = requests.get(SOUND_URL, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")

                # Ищем все ссылки на видео и дату публикации
                video_elements = soup.find_all("a", href=True)
                for a in video_elements:
                    if "/video/" in a["href"]:
                        video_url = a["href"]
                        # Здесь попробуем получить дату из data-time или текстового блока, если есть
                        time_tag = a.find_next("span")
                        try:
                            video_time = datetime.strptime(time_tag.text.strip(), '%Y-%m-%d %H:%M')
                        except:
                            video_time = datetime.now()  # если нет данных, ставим текущее время

                        if video_url not in seen_videos and video_time > datetime.now() - timedelta(days=1):
                            seen_videos.add(video_url)
                            await bot.send_message(chat_id=OWNER_ID, text=f"🆕 Новый ролик под твой звук: {video_url}")

            except Exception as e:
                print("Ошибка:", e)

        await asyncio.sleep(CHECK_INTERVAL)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    global OWNER_ID
    OWNER_ID = message.chat.id
    await message.answer("✅ Бот запущен! Используй команду /set_sound <ссылка> чтобы задать звук.")

@dp.message(Command("set_sound"))
async def set_sound_cmd(message: Message):
    global SOUND_URL, seen_videos
    parts = message.text.split()
    if len(parts) == 2:
        SOUND_URL = parts[1]
        seen_videos = set()  # сброс предыдущих видео
        await message.answer(f"✅ Звук установлен: {SOUND_URL}")
    else:
        await message.answer("❌ Использование: /set_sound <ссылка на звук>")

async def main():
    asyncio.create_task(check_new_videos())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
