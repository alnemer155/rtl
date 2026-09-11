"""نقطة «اسأل المصادر»: استرجاع محكم ← Gemini ← جواب مبثوث مع Citations."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.ai.base import ChatMessage, ProviderError, public_provider_error
from backend.ai.gemini import GeminiProvider
from backend.api.deps import get_app_settings, get_db
from backend.rag.context import (
    SYSTEM_PROMPT,
    build_citations,
    build_context,
    retrieve_chunks,
)
from backend.schemas.models import AskRequest
from backend.search.engine import SearchFilters
from shared.db.models import AiAnswer

logger = logging.getLogger("[rag]")

router = APIRouter(prefix="/api/ai", tags=["ai"])

# حدود طلبات بسيطة في الذاكرة (لكل عملية) — كافية للتطوير والحماية الأولية
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=200))


def _rate_limited(client_ip: str, limit_per_minute: int) -> bool:
    bucket = _RATE_BUCKETS[client_ip]
    now = time.monotonic()
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= limit_per_minute:
        return True
    bucket.append(now)
    return False


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/ask")
async def ask(
    request: Request,
    body: AskRequest,
    session: Session = Depends(get_db),
) -> StreamingResponse:
    settings = get_app_settings()
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip, settings.api_rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="rate_limited")

    provider = GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
    filters = SearchFilters(
        madhhab=body.madhhab,
        school=body.school,
        scholar=body.scholar,
        book=body.book,
        source=body.source,
    )
    chunks = retrieve_chunks(session, body.question, filters, settings.rag_top_k, settings.rag_max_chunk_chars)
    citations = build_citations(chunks)
    context = build_context(chunks)

    # انتماء الفلتر يُدخل في بيانات الجواب المشتقة للفصل بينها وبين المصادر
    record = AiAnswer(
        question=body.question,
        madhhab_filter=body.madhhab,
        filters_json={
            "madhhab": body.madhhab,
            "school": body.school,
            "scholar": body.scholar,
            "book": body.book,
            "source": body.source,
        },
        citations_json=citations,
        provider=provider.name,
        model=settings.gemini_model,
    )

    def build_user_message() -> str:
        return (
            f"سؤال المستخدم: {body.question}\n\n"
            f"{context}\n\n"
            "بما أن النصوص أعلاه هي المرجع الوحيد، أجب اعتماداً عليها فقط واذكر أرقامها بين معقوفتين مثل [1]. "
            "إذا كانت غير كافية للإجابة فقل ذلك صراحة."
        )

    async def event_stream():
        collected: list[str] = []
        finish_status = "stop"
        yield _sse("sources", {"citations": citations})
        if not chunks:
            yield _sse(
                "error",
                {"message": "لا توجد مواد متوفرة في قاعدة البيانات للإجابة على هذا السؤال بعد."},
            )
            yield _sse("done", {"finish": "no_sources"})
            return
        try:
            messages = [ChatMessage(role="user", content=build_user_message())]
            async for text in provider.stream_generate(SYSTEM_PROMPT, messages):
                collected.append(text)
                yield _sse("delta", {"text": text})
        except ProviderError as error:
            finish_status = error.code
            yield _sse("error", {"message": public_provider_error(error)})
        except asyncio.CancelledError:
            finish_status = "cancelled"
            _save_answer(record, "".join(collected), finish_status)
            raise
        yield _sse("done", {"finish": finish_status})
        _save_answer(record, "".join(collected), finish_status)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _save_answer(record: AiAnswer, answer: str, finish_status: str) -> None:
    """حفظ الجواب المشترك كمحتوى مشتق — لا يدخل سجلات المصادر أبداً."""
    try:
        from sqlalchemy.orm import Session as DBSession

        from shared.db.session import create_db_engine

        settings = get_app_settings()
        engine = create_db_engine(settings.database_url)
        with DBSession(engine) as session:
            record.answer = answer
            record.finish_status = finish_status
            session.add(record)
            session.commit()
    except Exception:  # noqa: BLE001 — فشل الأرشفة لا يكسر الجواب
        logger.exception("[rag] failed to archive ai answer")
