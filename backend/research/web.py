"""مزود بحث الويب — FreeSERP حالياً بقابلية الاستبدال دون تعديل الـChat API.

FreeSERP أداة اكتشاف وليست مصدراً شرعياً: لا يُعامل ai_summary أو عنوان
محرك بحث على أنه فتوى أو حديث. عند الحاجة تُجلب الصفحة الأصلية للتحقق.
"""

from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import urlsplit

import httpx

from backend.research.base import ResearchChunk, WebSearchProvider

_TAG_RE = re.compile(r"<[^>]+>")

# جودة النطاق: تُستخدم للترتيب فقط وليست حكماً على شرعية المحتوى
_TRUSTED_DOMAIN_BONUS = {
    "sistani.org": 40,
    "app.turath.io": 40,
    "turath.io": 35,
    "shamela.ws": 30,
    "islamweb.net": 15,
    "dorar.net": 25,
    "islamqa.info": 15,
    "wikipedia.org": 10,
}

_MAX_CONTENT_CHARS = 1600


class FreeSerpProvider(WebSearchProvider):
    key = "web"
    name = "بحث الويب — FreeSERP"

    def __init__(
        self,
        api_base: str = "https://freeserp.ai/api.php",
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
        cache_ttl: float = 600.0,
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._client = client
        self._timeout = timeout
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, list[ResearchChunk]]] = {}

    def _build_client(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(
            timeout=self._timeout, headers={"Accept": "application/json"}
        )

    def _rank(self, results: list[dict]) -> list[dict]:
        def score(item: dict) -> float:
            domain_bonus = 0.0
            url = item.get("url") or ""
            host = urlsplit(url).netloc.removeprefix("www.")
            for trusted, bonus in _TRUSTED_DOMAIN_BONUS.items():
                if host == trusted or host.endswith("." + trusted):
                    domain_bonus = float(bonus)
                    break
            try:
                dr = float(item.get("dr") or 0)
            except (TypeError, ValueError):
                dr = 0
            return domain_bonus + min(dr, 50.0)

        return sorted(results, key=score, reverse=True)

    def _to_chunks(self, payload: dict, limit: int) -> list[ResearchChunk]:
        seen_urls: set[str] = set()
        chunks: list[ResearchChunk] = []
        for item in self._rank(payload.get("results") or []):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url or not title or url in seen_urls:
                continue
            if not url.startswith(("http://", "https://")):
                continue
            seen_urls.add(url)
            summary = (item.get("ai_summary") or "").strip()
            domain = item.get("domain") or urlsplit(url).netloc
            text = summary if summary else title
            chunks.append(
                ResearchChunk(
                    provider=self.key,
                    title=title[:180],
                    detail=f"بحث الويب · {domain}",
                    text=text[:_MAX_CONTENT_CHARS],
                    url=url,
                    metadata={"domain": domain, "dr": item.get("dr")},
                )
            )
            if len(chunks) >= limit:
                break
        return chunks

    async def search(self, query: str, limit: int = 5) -> list[ResearchChunk]:
        cache_key = query.strip().lower()
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self._cache_ttl:
            return cached[1]

        params: dict[str, str | int] = {"q": query, "size": max(limit, 5)}
        client = self._build_client()
        payload: dict | None = None
        for attempt in range(2):  # إعادة محاولة واحدة على الأخطاء العابرة
            try:
                if self._client is not None:
                    response = await client.get(self._api_base, params=params)
                else:
                    async with client:
                        response = await client.get(self._api_base, params=params)
                response.raise_for_status()
                payload = response.json()
                break
            except (httpx.HTTPError, ValueError):
                if attempt == 0:
                    await asyncio.sleep(0.8)
                continue
        if not payload:
            return []

        chunks = self._to_chunks(payload, limit)
        self._cache[cache_key] = (time.monotonic(), chunks)
        return chunks


async def fetch_page_text(url: str, client: httpx.AsyncClient | None = None) -> str:
    """جلب صفحة أصلية للتحقق من محتواها — بحماية SSRF وحدود حجم صارمة."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return ""
    host = (parts.hostname or "").lower()
    if not host or host in ("localhost", "0.0.0.0") or host.endswith(".local"):
        return ""
    if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", host):
        octets = [int(part) for part in host.split(".")]
        if octets[0] in (10, 127) or (octets[0] == 192 and octets[1] == 168) or (
            octets[0] == 172 and 16 <= octets[1] <= 31
        ):
            return ""
    own_client = client is None
    http = client or httpx.AsyncClient(
        timeout=10.0, follow_redirects=True, headers={"User-Agent": "MasadirBot/0.1"}
    )
    try:
        response = await http.get(url)
        if response.status_code >= 400:
            return ""
        body = response.text[:200_000]
        body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", body)
        text = _TAG_RE.sub(" ", body)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:_MAX_CONTENT_CHARS]
    except httpx.HTTPError:
        return ""
    finally:
        if own_client:
            await http.aclose()
