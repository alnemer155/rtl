"""اختبارات استمرارية الزاحف: الحفظ وكشف التغيير والنسخ (Versioning)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from crawler.adapters.base import RawRecord
from crawler.adapters.registry import get_adapter
from crawler.core.config import load_settings
from crawler.pipeline import CrawlPipeline
from shared.db.models import Book, Issue, Section, TextVersion


def _make_pipeline(engine) -> CrawlPipeline:
    return CrawlPipeline(engine, get_adapter("sistani"), load_settings())


def _seed_book_and_section(engine) -> tuple[int, int]:
    pipeline = _make_pipeline(engine)
    with open("tests/fixtures/sistani/book-23720.html", encoding="utf-8") as f:
        outline = type(pipeline._adapter).parse_book(
            pipeline._adapter,
            f.read(),
        "https://www.sistani.org/arabic/book/23720/",
    )
    book_id = pipeline._upsert_book_and_sections("https://www.sistani.org/arabic/book/23720/", outline)
    with Session(engine) as session:
        section = session.scalar(select(Section).where(Section.book_id == book_id).limit(1))
        return book_id, section.id


def test_persist_creates_issue_with_hash_and_key(seeded_engine):
    book_id, section_id = _seed_book_and_section(seeded_engine)
    pipeline = _make_pipeline(seeded_engine)
    with Session(seeded_engine) as session:
        book = session.get(Book, book_id)
        record = RawRecord(issue_number=33, text_original="مسألة 33: نص اختبار")
        result = pipeline._persist_record(session, book, section_id, "https://www.sistani.org/arabic/book/23720/3605/", record)
        session.commit()
        assert result == "created"
        issue = session.scalar(select(Issue).where(Issue.issue_number == 33))
        assert issue is not None
        assert len(issue.content_hash) == 64
        assert len(issue.source_record_id) == 32
        assert issue.text_search  # نسخة البحث مشتقة
        assert "نص اختبار" in issue.text_original


def test_persist_unchanged_on_same_text(seeded_engine):
    book_id, section_id = _seed_book_and_section(seeded_engine)
    pipeline = _make_pipeline(seeded_engine)
    record = RawRecord(issue_number=33, text_original="مسألة 33: نص اختبار")
    with Session(seeded_engine) as session:
        book = session.get(Book, book_id)
        pipeline._persist_record(session, book, section_id, "url", record)
        session.commit()
        result = pipeline._persist_record(session, book, section_id, "url", record)
        session.commit()
    assert result == "unchanged"


def test_persist_versioning_on_text_change(seeded_engine):
    book_id, section_id = _seed_book_and_section(seeded_engine)
    pipeline = _make_pipeline(seeded_engine)
    with Session(seeded_engine) as session:
        book = session.get(Book, book_id)
        pipeline._persist_record(session, book, section_id, "url", RawRecord(issue_number=33, text_original="النسخة الأولى"))
        session.commit()
        result = pipeline._persist_record(session, book, section_id, "url", RawRecord(issue_number=33, text_original="النسخة الثانية"))
        session.commit()
    assert result == "updated"
    with Session(seeded_engine) as session:
        issue = session.scalar(select(Issue).where(Issue.issue_number == 33))
        assert issue.text_original == "النسخة الثانية"
        assert issue.source_revision == 1
        versions = session.scalars(select(TextVersion).where(TextVersion.issue_id == issue.id)).all()
        assert len(versions) == 1
        assert versions[0].text_original == "النسخة الأولى"


def test_issue_numbers_are_internal_only(seeded_engine):
    """الأرقام العربية الفارسية تتحول داخلياً دون تغيير النص المعروض (كما في تدفق الزحف)."""
    book_id, section_id = _seed_book_and_section(seeded_engine)
    pipeline = _make_pipeline(seeded_engine)
    adapter = pipeline._adapter
    with Session(seeded_engine) as session:
        book = session.get(Book, book_id)
        record = adapter.normalise_record(RawRecord(issue_number=None, text_original="مسألة ١٠٦٣: نص بالأرقام العربية"))
        assert record.issue_number == 1063  # التحويل الداخلي
        pipeline._persist_record(session, book, section_id, "url", record)
        session.commit()
        issue = session.scalar(select(Issue).where(Issue.issue_number == 1063))
        assert issue is not None
        assert "١٠٦٣" in issue.text_original  # النص الأصلي محفوظ كما هو
