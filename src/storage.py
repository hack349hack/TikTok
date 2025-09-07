from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Iterable


DB_PATH = Path("tiktok_watch.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS tracked_sounds (
music_id TEXT PRIMARY KEY,
title TEXT,
last_ts INTEGER DEFAULT 0,
last_video_ids TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS tracked_hashtags (
tag TEXT PRIMARY KEY,
last_video_ids TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS chat_subscriptions (
chat_id INTEGER NOT NULL,
target_type TEXT NOT NULL, -- 'sound' | 'hashtag'
target_id TEXT NOT NULL,
PRIMARY KEY(chat_id, target_type, target_id)
);
"""




def open_db() -> sqlite3.Connection:
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL;")
conn.executescript(SCHEMA)
return conn




def list_sounds(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
cur = conn.execute("SELECT music_id, title, last_ts FROM tracked_sounds ORDER BY title")
return list(cur.fetchall())




def upsert_sound(conn: sqlite3.Connection, music_id: str, title: str, last_ts: int) -> None:
conn.execute(
"INSERT INTO tracked_sounds(music_id, title, last_ts) VALUES(?,?,?) "
"ON CONFLICT(music_id) DO UPDATE SET title=excluded.title, last_ts=max(tracked_sounds.last_ts, excluded.last_ts)",
(music_id, title, last_ts),
)
conn.commit()




def get_sound_state(conn: sqlite3.Connection, music_id: str) -> tuple[int, set[str]]:
cur = conn.execute("SELECT last_ts, last_video_ids FROM tracked_sounds WHERE music_id=?", (music_id,))
row = cur.fetchone()
if not row:
return 0, set()
last_ts, ids_json = row
try:
return int(last_ts or 0), set(json.loads(ids_json or "[]"))
except Exception:
return int(last_ts or 0), set()




def update_sound_state(conn: sqlite3.Connection, music_id: str, last_ts: int, last_ids: Iterable[str]) -> None:
conn.execute(
"UPDATE tracked_sounds SET last_ts=?, last_video_ids=? WHERE music_id=?",
(int(last_ts), json.dumps(list(set(last_ids))), music_id),
)
conn.commit()




def subscribe(conn: sqlite3.Connection, chat_id: int, target_type: str, target_id: str) -> None:
conn.execute(
"INSERT OR IGNORE INTO chat_subscriptions(chat_id, target_type, target_id) VALUES(?,?,?)",
(chat_id, target_type, target_id),
)
conn.commit()




def unsubscribe(conn: sqlite3.Connection, chat_id: int, target_type: str, target_id: str) -> None:
conn.execute(
"DELETE FROM chat_subscriptions WHERE chat_id=? AND target_type=? AND target_id=?",
(chat_id, target_type, target_id),
)
conn.commit()




def subscribers(conn: sqlite3.Connection, target_type: str, target_id: str) -> list[int]:
cur = conn.execute(
"SELECT chat_id FROM chat_subscriptions WHERE target_type=? AND target_id=?",
(target_type, target_id),
)
return [r[0] for r in cur.fetchall()]
