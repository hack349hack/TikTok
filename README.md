# TikTok Sound Watcher Telegram Bot


Телеграм‑бот, который:
- Тречит видео по звуку (music id / ссылка вида `https://www.tiktok.com/music/<slug>-<music_id>`), сортирует по дате и присылает новые каждые 3 минуты.
- Отслеживает новые звуки из новых видео по хэштегу/поиску и уведомляет о новых sound-id.


## Быстрый старт (локально)
1. Установите Python 3.11+ и Chromium зависимости (ниже Docker все сделает сам).
2. `cp .env.sample .env` и заполните переменные.
3. `python -m venv .venv && source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Установите браузер для Playwright: `playwright install --with-deps chromium`
6. Запустите: `python -m src.bot`


## Переменные окружения
- `TELEGRAM_TOKEN` — токен бота.
- `ADMIN_CHAT_ID` — numeric chat id администратора (для логов/ошибок, опционально).
- `POLL_INTERVAL_SEC` — период джобы в секундах, по умолчанию `180` (3 минуты).
- `TZ` — например `Europe/Amsterdam`.
- `HTTP_PROXY` — при необходимости, прокси для Playwright (формат `http://user:pass@host:port`), опционально.


## Команды бота
- `/start` — помощь.
- `/track_sound <music_url|music_id>` — начать отслеживать звук.
- `/untrack_sound <music_id>` — перестать отслеживать.
- `/list` — список отслеживаемых звуков.
- `/track_hashtag <name>` — отслеживать новые звуки в новых видео по хэштегу.
- `/untrack_hashtag <name>` — удалить хэштег.
- `/set_interval <minutes>` — изменить период (по умолчанию 3).


## Хранилище
SQLite файл `tiktok_watch.db`:
- `tracked_sounds(music_id TEXT PRIMARY KEY, title TEXT, last_ts INTEGER, last_video_ids TEXT)`
- `tracked_hashtags(tag TEXT PRIMARY KEY, last_video_ids TEXT)`
- `chat_subscriptions(chat_id INTEGER, target_type TEXT, target_id TEXT, PRIMARY KEY(chat_id, target_type, target_id))`


## Отправка контента
Для каждого нового видео бот шлёт:
- кликабельную ссылку на видео;
- автора, описание, дату;
- превью (если доступно) и прямой линк на звук.


## Деплой на Amvera
Пушите репозиторий. В панели Amvera:
1) создайте приложение «Docker»,
2) подключите GitHub‑репозиторий,
3) в **Variables/Secrets** добавьте переменные окружения (см. выше),
4) деплой из ветки с `Dockerfile`.


Конфиг `amvera.yaml` описывает команду запуска; Amvera читает Dockerfile и запускает `python -m src.bot`.


## Лицензия
MIT. Используйте ответственно и в рамках правил платформ TikTok/Telegram и закона.
