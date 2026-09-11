"""إعدادات الزاحف من متغيرات البيئة بقيم محافظة."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, "") or default)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "") or default)
    except ValueError:
        return default


@dataclass
class CrawlSettings:
    min_interval: float = field(default_factory=lambda: _env_float("CRAWL_MIN_INTERVAL", 2.0))
    concurrency: int = field(default_factory=lambda: _env_int("CRAWL_CONCURRENCY", 2))
    max_attempts: int = field(default_factory=lambda: _env_int("CRAWL_MAX_ATTEMPTS", 4))
    connect_timeout: float = 15.0
    read_timeout: float = 60.0
    user_agent: str = field(
        default_factory=lambda: os.environ.get(
            "CRAWL_USER_AGENT",
            "MasadirScholarlyBot/0.1 (respectful academic archive crawler)",
        )
    )
    max_pages: int | None = None  # حد اختياري للتجارب


def load_settings() -> CrawlSettings:
    return CrawlSettings()
