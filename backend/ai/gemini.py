"""مزوّد Gemini — Server-side فقط عبر بث SSE (منهج مستوحى من provider.ts في Sal AI).

الضوابط:
- GEMINI_API_KEY من متغيرات البيئة فقط؛ لا يصل إلى المتصفح أو السجلات أو الردود.
- GEMINI_MODEL متغير مستقل بقيمة افتراضية.
- مهلة زمنية حقيقية + إلغاء المستخدم (Abort) يفوز دائماً.
- التعامل مع 429 وBlocked وأخطاء البث برسائل عامة لا تكشف تفاصيل Google.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from backend.ai.base import AIProvider, ChatMessage, ProviderError

logger = logging.getLogger("[gemini]")

_STREAM_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
_TIMEOUT_SECONDS = 180.0


def _parse_sse_event(payload: str) -> str | None:
    """استخراج نص جزء واحد من حدث SSE بصيغة Gemini، أو None إذا لم يوجد نص."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise ProviderError("invalid_stream") from None
    if "error" in data:
        logger.warning("[gemini] stream error payload received")
        raise ProviderError("stream_error")
    prompt_feedback = data.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        raise ProviderError("blocked")
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    candidate = candidates[0]
    finish = candidate.get("finishReason")
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict) and not part.get("thought")
    )
    if finish and finish not in ("STOP", "MAX_TOKENS"):
        raise ProviderError("blocked")
    return text


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @classmethod
    def from_settings(cls) -> GeminiProvider:
        from backend.config import get_settings

        settings = get_settings()
        if not settings.gemini_api_key:
            raise ProviderError("not_configured")
        return cls(api_key=settings.gemini_api_key, model=settings.gemini_model)

    async def stream_generate(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        if not self._api_key:
            raise ProviderError("not_configured")
        url = _STREAM_ENDPOINT.format(model=self._model)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._api_key}
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": "model" if message.role == "assistant" else "user", "parts": [{"text": message.content}]}
                for message in messages
            ],
            "generationConfig": {"maxOutputTokens": 4096},
        }
        timeout = httpx.Timeout(connect=15.0, read=_TIMEOUT_SECONDS, write=30.0, pool=30.0)
        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream("POST", url, headers=headers, json=body) as response,
            ):
                    if response.status_code == 429:
                        raise ProviderError("http_error", status=429)
                    if response.status_code in (401, 403):
                        raise ProviderError("auth_error", status=response.status_code)
                    if response.status_code >= 400:
                        logger.warning("[gemini] http status %d", response.status_code)
                        raise ProviderError("http_error", status=response.status_code)
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line.startswith("data:"):
                                text = _parse_sse_event(line[len("data:") :].strip())
                                if text:
                                    yield text
        except httpx.TimeoutException as error:
            raise ProviderError("timeout") from error
        except httpx.HTTPError as error:
            raise ProviderError("network_error") from error
        except asyncio.CancelledError:
            raise


def _self_test() -> None:  # pragma: no cover
    assert _parse_sse_event(
        json.dumps({"candidates": [{"content": {"parts": [{"text": "مرحبا"}]}}]})
    ) == "مرحبا"
