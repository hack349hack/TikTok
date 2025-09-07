import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tiktok.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS music_videos (
        music_id TEXT,
        video_id TEXT,
        PRIMARY KEY (music_id, video_id)
    )
    """)
    conn.commit()
    conn.close()

def get_known_video_ids(music_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT video_id FROM music_videos WHERE music_id=?", (music_id,))
    rows = cursor.fetchall()
    conn.close()
    return set(r[0] for r in rows)

def save_new_video(music_id: str, video_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO music_videos (music_id, video_id) VALUES (?, ?)", (music_id, video_id))
    conn.commit()
    conn.close()

# Инициализация БД при импорте
init_db()
