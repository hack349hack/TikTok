from aiogram import Bot, Dispatcher
from settings import SETTINGS
from tiktok import monitor_music
import asyncio

bot = Bot(token=SETTINGS.telegram_token)
dp = Dispatcher()

@dp.message(commands=["start"])
async def cmd_start(message):
    await message.answer("Бот запущен!")

# Запуск фонового мониторинга
async def on_startup():
    music_id = "7344858713896913666"  # пример
    chat_id = 123456789  # ваш chat_id
    asyncio.create_task(monitor_music(bot, music_id, chat_id))

if __name__ == "__main__":
    import asyncio
    from aiogram import F

    asyncio.run(on_startup())
    
