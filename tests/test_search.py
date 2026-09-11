"""اختبارات محرك البحث: الفلاتر الصارمة ومنع اختلاط المذاهب."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.search.engine import SearchFilters, build_fts_query, search_issues
from crawler.adapters.base import RawRecord
from crawler.adapters.registry import get_adapter
from crawler.core.config import load_settings
from crawler.pipeline import CrawlPipeline
from crawler.storage.database import seed_reference_data
from shared.db.models import Book, Issue, School, Section


def _seed_two_madhhab_issues(engine) -> None:
    """إدراج مسألتين بنفس الموضوع لكن بانتمائين مذهبيين مختلفين."""
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        seed_reference_data(session)
    pipeline = CrawlPipeline(engine, get_adapter("sistani"), load_settings())
    with open("tests/fixtures/sistani/book-23720.html", encoding="utf-8") as f:
        outline = pipeline._adapter.parse_book(
            f.read(),
            "https://www.sistani.org/arabic/book/23720/",
        )
    book_id = pipeline._upsert_book_and_sections("https://www.sistani.org/arabic/book/23720/", outline)

    with Session(engine) as session:
        book = session.get(Book, book_id)
        section = session.scalars(select(Section).where(Section.book_id == book_id).limit(1)).first()
        shafii = session.scalar(select(School).where(School.key == "shafii"))
        book2 = Book(
            source_id=book.source_id,
            title_original="كتاب شافعي اختبار",
            title_normalised="كتاب شافعي اختبار",
            source_url="https://example-shafii.invalid/book/1/",
            madhhab_id=shafii.madhhab_id,
            school_id=shafii.id,
        )
        session.add(book2)
        session.flush()
        section2 = Section(
            book_id=book2.id,
            title_original="باب اختبار",
            title_search="باب اختبار",
            position=0,
            depth=0,
            source_url="https://example-shafii.invalid/book/1/s1/",
        )
        session.add(section2)
        session.commit()
        pipeline._persist_record(
            session, book, section.id, "https://www.sistani.org/arabic/book/23720/3605/",
            RawRecord(issue_number=33, text_original="مسألة 33: صيام يوم عرفة سنة عند السيستاني"),
        )
        pipeline._persist_record(
            session, book2, section2.id, "https://example-shafii.invalid/book/1/s1/",
            RawRecord(issue_number=33, text_original="مسألة 33: صيام يوم عرفة عند الشافعي سنة"),
        )
        session.commit()


def test_build_fts_query_quotes_and_prefixes():
    assert build_fts_query("صوم عرفة") == '"صوم"* AND "عرفه"*'
    assert build_fts_query("صوم عرفة", "OR") == '"صوم"* OR "عرفه"*'


def test_build_fts_query_empty():
    assert build_fts_query("   ") == ""


def test_search_finds_arabic_text_normalized(seeded_engine):
    """البحث مطبّع ومبادئي (بلا stemming): «صيام» تطابق «صيام» لا «صوم».

    استعلام يطبع إلى فراغ (ترقيم فقط) يعامل كتصفح بفلاتر — يعيد الكل المصفى.
    """
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        total, hits = search_issues(session, "صيام يوم عرفة", SearchFilters())
        assert total >= 2
        assert hits
        browse_all, _ = search_issues(session, "!!!!", SearchFilters())
        assert browse_all == 2


def test_madhhab_filter_is_strict(seeded_engine):
    """فلتر المذهب يفصل بصرامة: كل مذهب لا يُخرج إلا نصوصه."""
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        total_shia, hits_shia = search_issues(session, "صيام يوم عرفة", SearchFilters(madhhab="shia"))
        assert total_shia == 1
        issue = session.get(Issue, hits_shia[0].issue_id)
        assert issue.madhhab_id is not None

        total_sunni, hits_sunni = search_issues(session, "صيام يوم عرفة", SearchFilters(madhhab="sunni"))
        assert total_sunni == 1
        sunni_issue = session.get(Issue, hits_sunni[0].issue_id)
        assert "الشافعي" in sunni_issue.text_original


def test_scholar_and_book_filters(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        total, _ = search_issues(session, "صيام", SearchFilters(scholar="sistani"))
        assert total == 1
        book2 = session.scalar(select(Book).where(Book.title_original == "كتاب شافعي اختبار"))
        total2, _ = search_issues(session, "صيام", SearchFilters(book=book2.id))
        assert total2 == 1


def test_issue_number_filter(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        total, _ = search_issues(session, "صيام عرفة", SearchFilters(issue_number=33))
        assert total == 2
        total2, _ = search_issues(session, "صيام عرفة", SearchFilters(issue_number=999))
        assert total2 == 0


def test_exact_match_boosting(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    with Session(seeded_engine) as session:
        _total, hits = search_issues(session, "صيام يوم عرفة سنة عند السيستاني", SearchFilters())
        assert hits
        top = session.get(Issue, hits[0].issue_id)
        assert "السيستاني" in top.text_original
