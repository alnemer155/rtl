"""اختبارات مزوّد Gemini: تحليل بث SSE والأخطاء العامة — بلا اتصال شبكة."""

import json

import pytest

from backend.ai.base import ChatMessage, ProviderError, public_provider_error
from backend.ai.gemini import GeminiProvider, _parse_sse_event


def test_parse_sse_event_extracts_text():
    payload = json.dumps({"candidates": [{"content": {"parts": [{"text": "مرحبا"}]}}]})
    assert _parse_sse_event(payload) == "مرحبا"


def test_parse_sse_event_multiple_parts():
    payload = json.dumps({"candidates": [{"content": {"parts": [{"text": "أ"}, {"text": "ب"}]}}]})
    assert _parse_sse_event(payload) == "أب"


def test_parse_sse_event_ignores_thought_parts():
    payload = json.dumps({"candidates": [{"content": {"parts": [{"text": "خ", "thought": True}, {"text": "جواب"}]}}]})
    assert _parse_sse_event(payload) == "جواب"


def test_parse_sse_event_blocked_raises():
    payload = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(ProviderError) as error:
        _parse_sse_event(payload)
    assert error.value.code == "blocked"


def test_parse_sse_event_error_payload_raises():
    payload = json.dumps({"error": {"code": 400, "message": "raw google error"}})
    with pytest.raises(ProviderError):
        _parse_sse_event(payload)


def test_parse_sse_event_invalid_json_raises():
    with pytest.raises(ProviderError):
        _parse_sse_event("not-json{")


def test_provider_requires_api_key():
    provider = GeminiProvider(api_key="", model="gemini-2.5-flash")

    async def consume():
        async for _ in provider.stream_generate("system", [ChatMessage(role="user", content="س")]):
            pass

    import asyncio

    with pytest.raises(ProviderError) as error:
        asyncio.run(consume())
    assert error.value.code == "not_configured"


def test_public_error_messages_are_arabic_and_generic():
    message_429 = public_provider_error(ProviderError("http_error", status=429))
    assert "مشغولة" in message_429
    message_blocked = public_provider_error(ProviderError("blocked"))
    assert "تعذر" in message_blocked
    message_generic = public_provider_error(ProviderError("http_error", status=500))
    assert "تعذر إكمال الرد" in message_generic
    # رسالة 403/401 لا تكشف تفاصيل Google
    assert "google" not in message_generic.lower()


def test_public_error_for_unconfigured():
    assert "غير مهيأة" in public_provider_error(ProviderError("not_configured"))
