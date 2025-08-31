import asyncio
from aiogram import Bot
import os

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)

async def delete_webhook():
    await bot.delete_webhook()
    print("Webhook удалён")
    await bot.session.close()

asyncio.run(delete_webhook())
