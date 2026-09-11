"""قراءة robots.txt مع تخزين مؤقت واحترام صارم لقرارات المنع.

السياسات:
- robots.txt غير موجود (404) → يُسمح بالزحف وفق العرف.
- robots.txt يُعيد 429/5xx أو يفشل → يُمنع الزحف (فشل مُغلق احتراماً).
- لا تجاوز لحظر المسارات ولا لجدران الدخول ولا CAPTCHA، إطلاقاً.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger("[crawler.robots]")

_ROBOTS_TTL_SECONDS = 3600.0


class RobotsDenied(Exception):
    def __init__(self, url: str) -> None:
        super().__init__(f"robots.txt disallows: {url}")
        self.url = url


@dataclass
class _RobotsEntry:
    parser: RobotFileParser | None  # None = ممنوع بالكامل (فشل مُغلق)
    fetched_at: float


class RobotsGuard:
    def __init__(self, user_agent: str, client: httpx.AsyncClient) -> None:
        self._user_agent = user_agent
        self._client = client
        self._cache: dict[str, _RobotsEntry] = {}

    async def _fetch_entry(self, origin: str) -> _RobotsEntry:
        robots_url = f"{origin}/robots.txt"
        base_parser = RobotFileParser()
        parser: RobotFileParser | None
        try:
            response = await self._client.get(robots_url)
            if response.status_code == 404:
                parser = base_parser
                parser.parse([])  # لا قواعد → مسموح
            elif response.status_code >= 400:
                logger.warning("%s unreachable (%d) — failing closed", robots_url, response.status_code)
                parser = None  # فشل مُغلق
            else:
                parser = base_parser
                parser.parse(response.text.splitlines())
        except httpx.HTTPError:
            logger.warning("%s fetch failed — failing closed", robots_url)
            parser = None
        return _RobotsEntry(parser=parser, fetched_at=time.monotonic())

    async def _entry(self, url: str) -> _RobotsEntry:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        entry = self._cache.get(origin)
        if entry is None or time.monotonic() - entry.fetched_at > _ROBOTS_TTL_SECONDS:
            entry = await self._fetch_entry(origin)
            self._cache[origin] = entry
        return entry

    async def ensure_allowed(self, url: str) -> None:
        entry = await self._entry(url)
        if entry.parser is None:
            raise RobotsDenied(url)
        if not entry.parser.can_fetch(self._user_agent, url):
            raise RobotsDenied(url)
