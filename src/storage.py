import sqlite3
from pathlib import Path
import json
from typing import Iterable, Set, Tuple, Optional

DB_PATH = Path(__file__).parent / "data.db"

def open_db() -> sqlite3.Connection:
    """Открыть соединение с базой и создать таблицы, если их нет."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tracked_sounds (
        music_id TEXT PRIMARY KEY,
        title TEXT,
        last_ts INTEGER DEFAULT 0,
        last_ids TEXT DEFAULT '[]'
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        chat_id INTEGER,
        type TEXT,
        target TEXT,
        PRIMARY KEY(chat_id, type, target)
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tracked_hashtags (
        tag TEXT PRIMARY KEY,
        last_video_ids TEXT DEFAULT '[]'
    )
    """)
    conn.commit()
    return conn

def list_sounds(conn: sqlite3.Connection) -> list[Tuple[str, str, Optional[int]]]:
    cur = conn.execute("SELECT music_id, title, last_ts FROM tracked_sounds")
    return cur.fetchall()

def upsert_sound(conn: sqlite3.Connection, music_id: str, title: str, last_ts: int):
    conn.execute(
        "INSERT INTO tracked_sounds(music_id, title, last_ts) VALUES(?, ?, ?) "
        "ON CONFLICT(music_id) DO UPDATE SET title=excluded.title, last_ts=excluded.last_ts",
        (music_id, title, last_ts)
    )
    conn.commit()

def get_sound_state(conn: sqlite3.Connection, music_id: str) -> Tuple[Optional[int], Set[str]]:
    cur = conn.execute("SELECT last_ts, last_ids FROM tracked_sounds WHERE music_id=?", (music_id,))
    row = cur.fetchone()
    if not row:
        return 0, set()
    last_ts, last_ids_json = row
    try:
        last_ids = set(json.loads(last_ids_json))
    except Exception:
        last_ids = set()
    return last_ts or 0, last_ids

def update_sound_state(conn: sqlite3.Connection, music_id: str, last_ts: int, last_ids: Set[str]):
    conn.execute(
        "UPDATE tracked_sounds SET last_ts=?, last_ids=? WHERE music_id=?",
        (last_ts, json.dumps(list(last_ids)), music_id)
    )
    conn.commit()

def subscribe(conn: sqlite3.Connection, chat_id: int, type_: str, target: str):
    conn.execute(
        "INSERT OR IGNORE INTO subscriptions(chat_id, type, target) VALUES(?, ?, ?)",
        (chat_id, type_, target)
    )
    conn.commit()

def unsubscribe(conn: sqlite3.Connection, chat_id: int, type_: str, target: str):
    conn.execute(
        "DELETE FROM subscriptions WHERE chat_id=? AND type=? AND target=?",
        (chat_id, type_, target)
    )
    conn.commit()

def subscribers(conn: sqlite3.Connection, type_: str, target: str) -> Iterable[int]:
    cur = conn.execute(
        "SELECT chat_id FROM subscriptions WHERE type=? AND target=?",
        (type_, target)
    )
    return [r[0] for r in cur.fetchall()]
  
