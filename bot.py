import asyncio import requests from bs4 import BeautifulSoup from datetime import datetime, timedelta from aiogram import Bot, Dispatcher, types from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery from aiogram.filters import Command import os, json

=== НАСТРОЙКИ ===

TOKEN = os.getenv("TOKEN", "8098428478:AAGJJKaREHjQgGPFudgyH1pc_UzzqJUrcgE")  # можно оставить токен напрямую CHECK_INTERVAL = 300  # как часто проверять (секунд) HISTORY_FILE = 'seen_videos.json'

bot = Bot(token=TOKEN) dp = Dispatcher()

Храним данные

seen_videos = set() SOUND_URL = None OWNER_ID = None

Загрузка истории

if os.path.exists(HISTORY_FILE): with open(HISTORY_FILE, 'r') as f: try: seen_videos = set(json.load(f)) except: seen_videos = set()

Клавиатура

keyboard = ReplyKeyboardMarkup( keyboard=[ [KeyboardButton('Установить звук'), KeyboardButton('Удалить звук')], [KeyboardButton('Проверить звук')] ], resize_keyboard=True )

async def check_new_videos(): global seen_videos, SOUND_URL while True: if SOUND_URL: try: r = requests.get(SOUND_URL, headers={"User-Agent": "Mozilla/5.0"}) soup = BeautifulSoup(r.text, "html.parser")

video_elements = soup.find_all("a", href=True)
            for a in video_elements:
                if "/video/" in a["href"]:
                    video_url = a["href"]
                    time_tag = a.find_next("span")
                    try:
                        video_time = datetime.strptime(time_tag.text.strip(), '%Y-%m-%d %H:%M')
                    except:
                        video_time = datetime.now()

                    if video_url not in seen_videos and video_time > datetime.now() - timedelta(days=1):
                        seen_videos.add(video_url)
                        with open(HISTORY_FILE, 'w') as f:
                            json.dump(list(seen_videos), f)

                        # Получаем миниатюру видео
                        try:
                            r_video = requests.get(video_url, headers={"User-Agent": "Mozilla/5.0"})
                            soup_video = BeautifulSoup(r_video.text, "html.parser")
                            meta_thumb = soup_video.find("meta", property="og:image")
                            thumbnail_url = meta_thumb["content"] if meta_thumb else None
                        except:
                            thumbnail_url = None

                        # Кнопки: открыть видео и удалить звук
                        keyboard_inline = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="▶️ Открыть в TikTok", url=video_url)],
                                [InlineKeyboardButton(text="🗑 Удалить звук", callback_data="remove_sound")]
                            ]
                        )

                        if thumbnail_url:
                            await bot.send_photo(
                                chat_id=OWNER_ID,
                                photo=thumbnail_url,
                                caption="🆕 Новый ролик под твой звук!",
                                reply_markup=keyboard_inline
                            )
                        else:
                            await bot.send_message(
                                chat_id=OWNER_ID,
                                text="🆕 Новый ролик под твой звук!",
                                reply_markup=keyboard_inline
                            )

        except Exception as e:
            print("Ошибка:", e)

    await asyncio.sleep(CHECK_INTERVAL)

@dp.message(Command("start")) async def start_cmd(message: Message): global OWNER_ID OWNER_ID = message.chat.id await message.answer("✅ Бот запущен!", reply_markup=keyboard)

@dp.message(Command("set_sound")) async def set_sound_cmd(message: Message): global SOUND_URL, seen_videos parts = message.text.split() if len(parts) == 2: SOUND_URL = parts[1] seen_videos = set()  # сброс предыдущих видео with open(HISTORY_FILE, 'w') as f: json.dump(list(seen_videos), f) await message.answer(f"✅ Звук установлен: {SOUND_URL}") else: await message.answer("❌ Использование: /set_sound <ссылка на звук>")

@dp.message(Command("remove_sound")) async def remove_sound_cmd(message: Message): global SOUND_URL SOUND_URL = None await message.answer("🗑 Звук удалён")

@dp.callback_query(lambda c: c.data == "remove_sound") async def callback_remove_sound(callback: CallbackQuery): global SOUND_URL SOUND_URL = None await callback.message.edit_caption( caption="❌ Звук удалён", reply_markup=None ) if callback.message.photo else await callback.message.edit_text( text="❌ Звук удалён", reply_markup=None ) await callback.answer("Звук удалён")

@dp.message() async def handle_buttons(message: Message): if message.text == 'Установить звук': await message.answer('Используй команду /set_sound <ссылка на звук>') elif message.text == 'Удалить звук': await remove_sound_cmd(message) elif message.text == 'Проверить звук': if SOUND_URL: await message.answer(f"Текущий звук: {SOUND_URL}") else: await message.answer("Звук не установлен")

async def main(): asyncio.create_task(check_new_videos()) await dp.start_polling(bot)

if name == "main": asyncio.run(main())

