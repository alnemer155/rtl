"""اختبارات مزود Turath وFreeSERP بـhttpx.MockTransport — بلا شبكة."""

import asyncio

import httpx

from backend.research.turath import TurathProvider
from backend.research.web import FreeSerpProvider, fetch_page_text

TURATH_SEARCH_PAYLOAD = {
    "count": 2,
    "data": [
        {
            "book_id": 13251,
            "cat_id": 6,
            "author_id": 2445,
            "meta": '{"headings":["كتاب الجهاد"],"page_id":900,"page":120,"vol":"3","book_name":"كتاب تجريبي","author_name":"مؤلف تجريبي"}',
            "snip": "<em>نص</em> مع &amp; علامات",
            "text": "النص الأصلي الكامل هنا",
        }
    ],
}


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_turath_search_parses_results():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "api.turath.io/search" in str(request.url)
        assert request.url.params["version"] == "3"
        return httpx.Response(200, json=TURATH_SEARCH_PAYLOAD)

    async def run() -> list:
        provider = TurathProvider(client=_mock_client(handler))
        return await provider.search("بر الوالدين", limit=3)

    chunks = asyncio.run(run())
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.provider == "turath"
    assert chunk.title == "كتاب تجريبي"
    assert "<em>" not in chunk.text  # إزالة وسوم HTML
    assert "&amp;" not in chunk.text
    assert chunk.url == "https://app.turath.io/book/13251/900"
    assert chunk.metadata["page"] == 120


def test_turath_search_graceful_on_http_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async def run() -> list:
        provider = TurathProvider(client=_mock_client(handler))
        return await provider.search("أي شيء")

    assert asyncio.run(run()) == []


def _serp_payload():
    return {
        "ok": "True",
        "results": [
            {
                "url": "https://example.org/page",
                "title": "نتيجة موثوقة",
                "domain": "example.org",
                "dr": 30,
                "ai_summary": "ملخص الصفحة",
            },
            {
                "url": "https://example.org/page",
                "title": "مكرر",
                "domain": "example.org",
                "dr": 10,
            },
            {
                "url": "https://lowdr.example.net/x",
                "title": "نتيجة أقل جودة",
                "domain": "lowdr.example.net",
                "dr": 2,
                "ai_summary": "ملخص ثانٍ",
            },
        ],
    }


def test_freeserp_dedup_and_ranking():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_serp_payload())

    async def run() -> list:
        provider = FreeSerpProvider(client=_mock_client(handler))
        return await provider.search("islamic history", limit=5)

    chunks = asyncio.run(run())
    urls = [chunk.url for chunk in chunks]
    assert len(urls) == len(set(urls))  # إزالة التكرار
    assert chunks[0].url == "https://example.org/page"  # الترتيب بجودة النطاق
    assert chunks[0].metadata["domain"] == "example.org"


def test_freeserp_cache_hits_same_object():
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_serp_payload())

    async def run() -> tuple[list, list]:
        provider = FreeSerpProvider(client=_mock_client(handler))
        first = await provider.search("same query")
        second = await provider.search("same query")
        return first, second

    first, second = asyncio.run(run())
    assert calls["count"] == 1
    assert first is second


def test_fetch_page_text_blocks_private_targets():
    async def run() -> tuple[str, str, str, str]:
        return (
            await fetch_page_text("http://localhost/admin"),
            await fetch_page_text("http://127.0.0.1/secret"),
            await fetch_page_text("http://192.168.1.5/router"),
            await fetch_page_text("ftp://example.org/file"),
        )

    results = asyncio.run(run())
    assert all(text == "" for text in results)


def test_fetch_page_text_strips_html():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text="<html><script>evil()</script><body><p>محتوى صفحي الأصلي</p></body></html>"
        )

    async def run() -> str:
        client = _mock_client(handler)
        try:
            return await fetch_page_text("https://example.org/article", client)
        finally:
            await client.aclose()

    text = asyncio.run(run())
    assert "محتوى صفحي الأصلي" in text
    assert "evil" not in text
