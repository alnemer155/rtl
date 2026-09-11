"""اختبارات RAG: الاسترجاع المصفى وبناء السياق والاستشهادات."""

from sqlalchemy.orm import Session

from backend.rag.context import (
    SYSTEM_PROMPT,
    build_citations,
    build_context,
    retrieve_chunks,
)
from backend.search.engine import SearchFilters
from tests.test_search import _seed_two_madhhab_issues


def test_retrieve_chunks_include_full_metadata(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        chunks = retrieve_chunks(session, "صيام يوم عرفة", SearchFilters(), top_k=5, max_chunk_chars=3000)
        assert chunks
        chunk = chunks[0]
        assert chunk.book_title
        assert chunk.madhhab
        assert chunk.issue.source_url.startswith("http")
        assert chunk.issue.content_hash


def test_retrieval_enforces_madhhab_filter(seeded_engine):
    """فلتر المذهب في RAG إلزامي: لا نصوص من مذهب آخر تدخل سياق Gemini."""
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        chunks = retrieve_chunks(session, "صيام يوم عرفة", SearchFilters(madhhab="shia"), top_k=5, max_chunk_chars=3000)
        assert len(chunks) == 1
        assert chunks[0].madhhab == "الشيعة"
        assert "الشافعي" not in chunks[0].text


def test_build_context_numbers_and_metadata():
    from types import SimpleNamespace

    chunk = SimpleNamespace(
        issue=SimpleNamespace(id=1, issue_number=1065, source_url="https://x/1/", text_original="نص"),
        scholar="السيد علي السيستاني",
        book_title="منهاج الصالحين",
        section_path="كتاب الصوم ← فصل",
        madhhab="الشيعة",
        school="الجعفري",
        text="نص المسألة كامل",
    )
    context = build_context([chunk])
    assert "[1]" in context
    assert "السيد علي السيستاني" in context
    assert "منهاج الصالحين" in context
    assert "كتاب الصوم ← فصل" in context
    assert "1065" in context
    assert "https://x/1/" in context
    assert "نص المسألة كامل" in context


def test_build_citations_map_to_records():
    from types import SimpleNamespace

    chunk = SimpleNamespace(
        issue=SimpleNamespace(id=7, issue_number=33, source_url="https://x/7/"),
        scholar="مرجع",
        book_title="كتاب",
        section_path="باب",
        madhhab="مذهب",
        school="مدرسة",
        text="نص",
    )
    citations = build_citations([chunk])
    assert citations[0]["index"] == 1
    assert citations[0]["issue_id"] == 7
    assert citations[0]["issue_number"] == 33
    assert citations[0]["source_url"] == "https://x/7/"


def test_system_prompt_grounding_rules():
    """تعليمات النظام تفرض الاستناد للمصادر وتمنع الاختراع."""
    assert "حصرياً" in SYSTEM_PROMPT or "المرجع الأساسي" in SYSTEM_PROMPT
    assert "لا تخترع رقم مسألة" in SYSTEM_PROMPT
    assert "لا تخترع رابطاً" in SYSTEM_PROMPT
    assert "لا تخترع اسم كتاب" in SYSTEM_PROMPT
    assert "لا تخلط بين المذاهب" in SYSTEM_PROMPT
    assert "غير كافية" in SYSTEM_PROMPT
