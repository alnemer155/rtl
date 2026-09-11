"""مزود Turath: المصادر السنية عبر API المنظم في api.turath.io.

لا يُزحف الموقع — يُستخدم الوصول المنظم:
  search(query)  → نتائج داخل نصوص المكتبة
  getBookInfo(id) → بيانات الكتاب
  getPage(id, page) → صفحة (حسب توفرها في الـAPI)
  getAuthor(id) → بيانات المؤلف
"""

from __future__ import annotations

import json
import re

import httpx

from backend.research.base import IslamicSourceProvider, ResearchChunk

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def _strip_html(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw or "")
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
    lines = [_WS_RE.sub(" ", line.strip()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


class TurathProvider(IslamicSourceProvider):
    key = "turath"
    name = "المكتبة التراثية السنية — turath.io"

    def __init__(
        self,
        api_base: str = "https://api.turath.io",
        app_base: str = "https://app.turath.io",
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._app_base = app_base.rstrip("/")
        self._client = client
        self._timeout = timeout

    def _build_client(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(
            timeout=self._timeout, headers={"Accept": "application/json"}
        )

    async def search(self, query: str, limit: int = 6) -> list[ResearchChunk]:
        params = {"q": query, "version": "3"}
        client = self._build_client()
        try:
            if self._client is not None:
                response = await client.get(f"{self._api_base}/search", params=params)
            else:
                async with client:
                    response = await client.get(f"{self._api_base}/search", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []  # فشل المزود لا يكسر المحادثة

        chunks: list[ResearchChunk] = []
        for item in (payload.get("data") or [])[:limit]:
            try:
                meta = json.loads(item.get("meta") or "{}")
            except (TypeError, ValueError):
                meta = {}
            book_id = item.get("book_id")
            page_id = item.get("meta") and meta.get("page_id")
            text = _strip_html(item.get("text") or item.get("snip") or "")
            if not text:
                continue
            headings = meta.get("headings") or []
            detail_parts = [
                meta.get("book_name") or "",
                " ← ".join(headings[-2:]) if headings else "",
                meta.get("author_name") or "",
            ]
            chunks.append(
                ResearchChunk(
                    provider=self.key,
                    title=meta.get("book_name") or f"كتاب تراثي {book_id}",
                    detail=" · ".join(part for part in detail_parts if part)
                    + (f" · ج{meta.get('vol')}" if meta.get("vol") else "")
                    + (f" · ص{meta.get('page')}" if meta.get("page") else ""),
                    text=text,
                    url=f"{self._app_base}/book/{book_id}"
                    + (f"/{page_id}" if page_id else ""),
                    metadata={
                        "book_id": book_id,
                        "author_id": item.get("author_id"),
                        "author_name": meta.get("author_name"),
                        "page": meta.get("page"),
                        "vol": meta.get("vol"),
                        "madhhab": "المصادر السنية",
                    },
                )
            )
        return chunks

    async def get_book_info(self, book_id: int) -> dict:
        client = self._build_client()
        try:
            if self._client is not None:
                response = await client.get(f"{self._api_base}/book", params={"id": book_id, "version": "3"})
            else:
                async with client:
                    response = await client.get(
                        f"{self._api_base}/book", params={"id": book_id, "version": "3"}
                    )
            response.raise_for_status()
            return response.json().get("meta") or {}
        except (httpx.HTTPError, ValueError):
            return {}

    async def get_author(self, author_id: int) -> dict:
        client = self._build_client()
        try:
            if self._client is not None:
                response = await client.get(f"{self._api_base}/author", params={"id": author_id, "version": "3"})
            else:
                async with client:
                    response = await client.get(
                        f"{self._api_base}/author", params={"id": author_id, "version": "3"}
                    )
            response.raise_for_status()
            return response.json() or {}
        except (httpx.HTTPError, ValueError):
            return {}

    async def get_page(self, book_id: int, page: int) -> dict:
        """جلب صفحة من كتاب — يعتمد توفرها في الـAPI وقد يرجع فارغاً."""
        client = self._build_client()
        try:
            if self._client is not None:
                response = await client.get(
                    f"{self._api_base}/page", params={"id": book_id, "page": page, "version": "3"}
                )
            else:
                async with client:
                    response = await client.get(
                        f"{self._api_base}/page", params={"id": book_id, "page": page, "version": "3"}
                    )
            response.raise_for_status()
            return response.json() or {}
        except (httpx.HTTPError, ValueError):
            return {}
