"""نقطة المحادثة الأساسية: رسالة → توجيه → استرجاع متعدد المصادر → Gemini مبثوثاً.

التصميم الحساس للزمن:
- معرّف المحادثة UUID يُولّد فوراً ويُرسل في حدث meta قبل أي كتابة — البث يبدأ لحظياً
  حتى مع قواعد سحابية بعيدة (مثل Neon).
- الحفظ (المحادثة + رسالة المستخدم + الجواب) يتم دفعة واحدة بعد انتهاء البث.
- المصادر تُدمج في قائمة استشهادات مرقمة واحدة مع الحفاظ على هوية كل مزود،
  ولا يُسمح للنموذج باختراع استشهاد لا يقابل سجلاً مسترجعاً.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.base import ChatMessage, ProviderError, public_provider_error
from backend.ai.gemini import GeminiProvider
from backend.ai.prompts import CHAT_SYSTEM_PROMPT
from backend.api.deps import get_app_settings, get_db
from backend.research.base import ResearchChunk
from backend.research.router import route_message
from backend.research.sistani import SistaniProvider
from backend.research.turath import TurathProvider
from backend.research.web import FreeSerpProvider, fetch_page_text
from backend.search.engine import SearchFilters
from shared.db.models import ChatMessage as ChatMessageRow
from shared.db.models import Conversation

logger = logging.getLogger("[chat]")

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_HISTORY_MESSAGES = 6
MAX_CHUNK_CHARS = 1500
PROVIDER_LABELS = {
    "sistani": "المصادر الجعفرية — sistani.org",
    "turath": "المكتبة التراثية السنية — turath.io",
    "web": "بحث الويب",
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    # وضع البحث: تلقائي (الراوتر يقرر) / مصادر إسلامية / ويب / بحث موسع
    research_mode: str | None = Field(default=None, pattern="^(auto|islamic|web|expanded)$")
    # إعدادات المصادر المتقدمة
    madhhab: str | None = None
    scholar: str | None = None
    book: int | None = None


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_to_citation(index: int, chunk: ResearchChunk) -> dict:
    return {
        "index": index,
        "provider": chunk.provider,
        "provider_label": PROVIDER_LABELS.get(chunk.provider, chunk.provider),
        "title": chunk.title,
        "detail": chunk.detail,
        "url": chunk.url,
        "text": chunk.text,
    }


def _apply_research_mode(decision, research_mode: str | None) -> None:
    """وضع البحث يتجاوز قرار الراوتر عندما يختاره المستخدم صراحة."""
    if research_mode in (None, "", "auto"):
        return
    if research_mode == "islamic":
        decision.islamic = True
        decision.web = False
        decision.providers = ["sistani", "turath"]
    elif research_mode == "web":
        decision.islamic = False
        decision.web = True
        decision.providers = []
    elif research_mode == "expanded":
        decision.islamic = True
        decision.web = True
        decision.providers = ["sistani", "turath"]
    decision.reason = f"manual:{research_mode}"


def _build_context(chunks: list[ResearchChunk]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        lines = [
            f"[{index}] ({PROVIDER_LABELS.get(chunk.provider, chunk.provider)})",
            f"العنوان: {chunk.title}",
        ]
        if chunk.detail:
            lines.append(f"التفاصيل: {chunk.detail}")
        if chunk.url:
            lines.append(f"الرابط: {chunk.url}")
        lines.append("النص:")
        lines.append(chunk.text)
        blocks.append("\n".join(lines))
    header = "المصادر المسترجعة من محرك البحث الإسلامي (استخدمها فقط للاستشهاد):\n"
    return header + "\n\n".join(blocks)


async def _gather_chunks(
    session: Session,
    message: str,
    decision,  # RouteDecision
    settings,  # Settings
    filters: SearchFilters | None,
) -> list[ResearchChunk]:
    sistani = SistaniProvider(session)
    top_k = settings.rag_top_k
    tasks = []
    if decision.islamic:
        if "sistani" in decision.providers:
            # Neon بعيد: أي عمل متزامن على حلقة الأحداث يجمد الخادم كله
            tasks.append(asyncio.to_thread(sistani.search_sync, message, top_k, filters))
        if "turath" in decision.providers:
            tasks.append(TurathProvider().search(message, limit=top_k))
    web_task = FreeSerpProvider().search(message, limit=4) if decision.web else None

    chunks: list[ResearchChunk] = []
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("provider failed: %r", result)
                continue
            chunks.extend(result)
    if web_task is not None:
        try:
            web_chunks = await web_task
        except Exception as error:  # noqa: BLE001 — بحث الويب لا يكسر المحادثة
            logger.warning("web search failed: %r", error)
            web_chunks = []
        # جلب الصفحة الأصلية لأول نتيجة للتحقق منها — بأفضل جهد
        if web_chunks:
            try:
                page_text = await fetch_page_text(web_chunks[0].url)
                if page_text and len(page_text) > 200:
                    web_chunks[0].text = page_text
            except Exception as error:  # noqa: BLE001
                logger.warning("page fetch failed: %r", error)
        chunks.extend(web_chunks)
    return [chunk.trim(MAX_CHUNK_CHARS) for chunk in chunks]


def _persist_exchange(
    session: Session,
    conversation_id: str,
    message: str,
    collected: list[str],
    citations_payload: list[dict],
    decision,
    research_mode: str | None,
    finish_status: str,
) -> None:
    """حفظ دفعة واحدة بعد انتهاء البث: المحادثة + رسالة المستخدم + الجواب."""
    try:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            conversation = Conversation(
                id=conversation_id, title=message.strip()[:80] or "محادثة جديدة"
            )
            session.add(conversation)
        session.add(
            ChatMessageRow(
                conversation_id=conversation_id,
                role="user",
                content=message,
                route_json={
                    "islamic": decision.islamic,
                    "web": decision.web,
                    "providers": decision.providers,
                    "madhhab_filter": decision.madhhab_filter,
                    "reason": decision.reason,
                    "research_mode": research_mode,
                },
            )
        )
        session.add(
            ChatMessageRow(
                conversation_id=conversation_id,
                role="assistant",
                content="".join(collected),
                citations_json=citations_payload,
                route_json={
                    "islamic": decision.islamic,
                    "web": decision.web,
                    "providers": decision.providers,
                    "reason": decision.reason,
                    "research_mode": research_mode,
                    "finish": finish_status,
                },
            )
        )
        session.commit()
    except Exception:  # noqa: BLE001 — فشل الأرشفة لا يكسر الرد
        logger.exception("failed to persist chat exchange")


@router.post("")
async def chat(
    request: Request,
    body: ChatRequest,
    session: Session = Depends(get_db),
) -> StreamingResponse:
    settings = get_app_settings()
    client_ip = request.client.host if request.client else "unknown"
    from backend.api.ai import _rate_limited

    if _rate_limited(client_ip, settings.api_rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="rate_limited")

    decision = route_message(body.message)
    _apply_research_mode(decision, body.research_mode)

    filters: SearchFilters | None = None
    if body.madhhab or body.scholar or body.book is not None:
        filters = SearchFilters(
            madhhab=body.madhhab,
            scholar=body.scholar,
            book=body.book,
        )
        # فلترة صريحة من المستخدم تعني نيته البحث في المصادر
        if not decision.islamic:
            decision.islamic = True
            if "sistani" not in decision.providers:
                decision.providers.append("sistani")

    provider = GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
    conversation_id = body.conversation_id or str(uuid.uuid4())

    async def event_stream():
        collected: list[str] = []
        finish_status = "stop"
        citations_payload: list[dict] = []
        # أول حدث يخرج فوراً — لا كتابة في قاعدة البيانات قبل البث
        yield _sse("meta", {"conversation_id": conversation_id, "route": decision.reason})

        needs_search = decision.islamic or decision.web
        chunks: list[ResearchChunk] = []
        if needs_search:
            yield _sse("status", {"line": "يبحث في المصادر…"})
            if decision.islamic and "sistani" in decision.providers:
                yield _sse("status", {"line": "يبحث في مصادر sistani.org…"})
            if decision.islamic and "turath" in decision.providers:
                yield _sse("status", {"line": "يبحث في المكتبة التراثية turath.io…"})
            if decision.web:
                yield _sse("status", {"line": "يبحث في الويب…"})
            try:
                chunks = await _gather_chunks(session, body.message, decision, settings, filters)
            except Exception as error:  # noqa: BLE001 — فشل الاسترجاع لا يوقف المحادثة
                logger.warning("retrieval failed: %r", error)
                chunks = []
            citations_payload = [
                _chunk_to_citation(index, chunk) for index, chunk in enumerate(chunks, start=1)
            ]
            yield _sse("sources", {"citations": citations_payload})
            yield _sse("status", {"line": "يصيغ الإجابة…"})

        context = _build_context(chunks) if chunks else ""
        user_content = body.message
        if context:
            user_content = (
                f"{body.message}\n\n{context}\n\n"
                "بما أن النصوص أعلاه هي المصدر الوحيد للاستشهاد، أجب اعتماداً عليها "
                "وادمج أرقامها [n] في مواضع الاعتماد. إن لم تكفِ قل ذلك بوضوح."
            )

        gemini_messages = [ChatMessage(role="user", content=user_content)]
        try:
            async for text in provider.stream_generate(CHAT_SYSTEM_PROMPT, gemini_messages):
                collected.append(text)
                yield _sse("delta", {"text": text})
        except ProviderError as error:
            finish_status = error.code
            yield _sse("error", {"message": public_provider_error(error)})
        except asyncio.CancelledError:
            finish_status = "cancelled"
            await asyncio.to_thread(
                _persist_exchange,
                session, conversation_id, body.message, collected, citations_payload,
                decision, body.research_mode, finish_status,
            )
            raise
        yield _sse("done", {"finish": finish_status, "conversation_id": conversation_id})
        # الكتابة بعد done وفي Thread حتى لا تجمد حلقة الأحداث
        await asyncio.to_thread(
            _persist_exchange,
            session, conversation_id, body.message, collected, citations_payload,
            decision, body.research_mode, finish_status,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
def list_conversations(session: Session = Depends(get_db)) -> list[dict]:
    conversations = session.scalars(
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(50)
    ).all()
    return [
        {
            "id": conversation.id,
            "title": conversation.title,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        }
        for conversation in conversations
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, session: Session = Depends(get_db)) -> dict:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    messages = session.scalars(
        select(ChatMessageRow)
        .where(ChatMessageRow.conversation_id == conversation_id)
        .order_by(ChatMessageRow.id)
    ).all()
    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "citations": message.citations_json or [],
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, session: Session = Depends(get_db)) -> dict:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    for message in session.scalars(
        select(ChatMessageRow).where(ChatMessageRow.conversation_id == conversation_id)
    ).all():
        session.delete(message)
    session.delete(conversation)
    session.commit()
    return {"deleted": conversation_id}
