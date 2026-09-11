"""عميل HTTP غير متزامن: تجميع اتصالات، مهل، تحقق من الحالة ونوع المحتوى، إعادة محاولة.

التصميم محافظ: لا يتبع ريدايركت خارج النطاقات المسموحة (حماية من SSRF)،
ولا يتجاوز robots.txt ولا جدران الدخول ولا CAPTCHA.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger("[crawler.http]")


if TYPE_CHECKING:
    from aiolimiter import AsyncLimiter


class HttpError(Exception):
    """خطأ HTTP مع كود للتصنيف في سجل التشغيلة."""

    def __init__(self, code: str, status: int = 0, url: str = "") -> None:
        super().__init__(f"{code} {status} {url}".strip())
        self.code = code
        self.status = status
        self.url = url


@dataclass
class FetchedPage:
    url: str
    status: int
    content: str


class AsyncHttpClient:
    """عميل واحد لكل تشغيلة: Rate limiting داخلي وإعادة محاولة بتراجع أسي مترنح."""

    def __init__(
        self,
        allowed_domains: set[str],
        user_agent: str,
        min_interval: float = 2.0,
        concurrency: int = 2,
        max_attempts: int = 4,
        connect_timeout: float = 15.0,
        read_timeout: float = 60.0,
        rate_limiter: AsyncLimiter | None = None,
    ) -> None:
        from aiolimiter import AsyncLimiter

        self._allowed_domains = {d.lower() for d in allowed_domains}
        self._max_attempts = max(max_attempts, 1)
        self._limiter = rate_limiter or AsyncLimiter(1.0, max(0.1, min_interval))
        self._interval = min_interval
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=30.0, pool=30.0),
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ar,en;q=0.6",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def raw_client(self) -> httpx.AsyncClient:
        """عميل httpx الأساسي (يُستخدم لفحص robots.txt عبر RobotsGuard)."""
        return self._client

    async def __aenter__(self) -> AsyncHttpClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def validate_url(self, url: str) -> None:
        """التحقق من أن الرابط ضمن النطاقات المسموحة (Allowlist) — حماية SSRF."""
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise HttpError("scheme_not_allowed", 0, url)
        host = (parts.hostname or "").lower()
        if not host or not any(host == d or host.endswith("." + d) for d in self._allowed_domains):
            raise HttpError("domain_not_allowed", 0, url)
        # منع الاستهداف الداخلي
        if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
            raise HttpError("domain_not_allowed", 0, url)

    def _is_retryable(self, page: FetchedPage) -> bool:
        return page.status in (429, 500, 502, 503, 504)

    async def _attempt(self, url: str) -> FetchedPage:
        self.validate_url(url)
        # المحدّد نفسه يفرض المسافة الزمنية بين الطلبات (طلب واحد كل min_interval)
        async with self._limiter:
            pass
        response = await self._client.get(url)
        content_type = response.headers.get("content-type", "")
        if response.status_code in (401, 403):
            raise HttpError("forbidden", response.status_code, url)
        if response.status_code == 404:
            raise HttpError("not_found", 404, url)
        if response.status_code >= 400:
            raise HttpError("http_error", response.status_code, url)
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            raise HttpError("content_type_unexpected", response.status_code, url)
        page = FetchedPage(url=str(response.url), status=response.status_code, content=response.text)
        if self._is_retryable(page):
            return page
        return page

    async def get_html(self, url: str) -> FetchedPage:
        """جلب HTML مع إعادة المحاولة على الأخطاء العابرة والتراجع الأسي المترنح."""
        last_error: Exception | None = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential_jitter(initial=1.5, max=30),
                retry=(
                    retry_if_result(lambda page: self._is_retryable(page))
                    | retry_if_exception_type((httpx.TimeoutException, httpx.TransportError))
                ),
                reraise=True,
            ):
                with attempt:
                    async with self._semaphore:
                        return await self._attempt(url)
        except HttpError:
            raise
        except RetryError as error:  # pragma: no cover — reraise=True يمنعها نظرياً
            last_error = error
        except (httpx.TimeoutException, httpx.TransportError) as error:
            last_error = error
            raise HttpError("network_error", 0, url) from error
        raise HttpError("network_error", 0, url) from last_error
