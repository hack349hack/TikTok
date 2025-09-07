from __future__ import annotations
import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


from playwright.async_api import async_playwright


SIGI_RE = re.compile(r"<script id=\"SIGI_STATE\"[^>]*>(.*?)</script>", re.S)
MUSIC_URL_RE = re.compile(r"https?://(?:www\.)?tiktok\.com/music/[^/]*-(\d+)")
VIDEO_URL_FMT = "https://www.tiktok.com/@{author}/video/{vid}"
MUSIC_URL_FMT = "https://www.tiktok.com/music/_-{mid}"


@dataclass
class VideoItem:
id: str
create_time: int
author: str
desc: str
cover: str | None


def link(self) -> str:
return VIDEO_URL_FMT.format(author=self.author, vid=self.id)




async def _new_context(p, http_proxy: str | None):
args = []
proxy = None
if http_proxy:
proxy = {"server": http_proxy}
browser = await p.chromium.launch(headless=True)
ctx = await browser.new_context(locale="en-US", proxy=proxy, user_agent=None)
return browser, ctx




async def _extract_sigi(html: str) -> dict[str, Any]:
m = SIGI_RE.search(html)
if not m:
return {}
raw = m.group(1)
try:
return json.loads(raw)
except Exception:
return {}




def _videos_from_sigi(sigi: dict[str, Any]) -> tuple[list[VideoItem], str | None]:
# try ItemModule first (most reliable)
items: list[VideoItem] = []
title = None
try:
im = sigi.get("ItemModule") or {}
for vid, data in im.items():
items.append(
VideoItem(
id=str(vid),
create_time=int(data.get("createTime") or 0),
author=str((data.get("author") or "").strip("@")),
desc=str(data.get("desc") or ""),
cover=(data.get("video") or {}).get("cover") or None,
)
)
except Exception:
pass


# title of music page if present
try:
music_module = (sigi.get("MusicModule") or sigi.get("MusicInfo") or {})
if isinstance(music_module, dict):
title = (music_module.get("music") or {}).get("title")
except Exception:
pass
return items, title




async def fetch_music_videos(music_id: str, http_proxy: str | None = None, limit: int = 30) -> tuple[list[VideoItem], str | None]:
"""Fetch recent videos for a TikTok music (sound) id.
Strategy
