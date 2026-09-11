"""تهيئة البيانات المرجعية الحقيقية: المذاهب والمدارس ومصدر السيستاني ومرجعيته.

لا محتوى منسوخ ولا مسائل مصطنعة — بيانات تصنيفية عامة ومعلومات نشر موثقة فقط.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from crawler.storage.database import seed_reference_data, upsert_scholar, upsert_source
from shared.db.models import Book, Issue, Scholar, Source


def _propagate_lineage(session: Session) -> None:
    """وراثة الانتماءات من المصدر إلى كتبه ومسائله (للكتب التي زُحفت قبل الـseed)."""
    source = session.scalar(select(Source).where(Source.key == "sistani"))
    scholar = session.scalar(select(Scholar).where(Scholar.key == "sistani"))
    if source is None or scholar is None:
        return
    books = session.scalars(select(Book).where(Book.source_id == source.id)).all()
    for book in books:
        book.madhhab_id = source.madhhab_id
        book.school_id = source.school_id
        book.scholar_id = scholar.id
    issues = session.scalars(
        select(Issue).join(Book, Issue.book_id == Book.id).where(Book.source_id == source.id)
    ).all()
    for issue in issues:
        issue.madhhab_id = source.madhhab_id
        issue.school_id = source.school_id
        issue.scholar_id = scholar.id
    session.commit()


def seed_all(session: Session) -> None:
    seed_reference_data(session)

    upsert_source(
        session,
        key="sistani",
        name="موقع مكتب سماحة المرجع الديني الأعلى السيد علي الحسيني السيستاني",
        domain="sistani.org",
        base_url="https://www.sistani.org/",
        source_type="official_website",
        language="ar",
        madhhab_key="shia",
        school_key="jaafari",
        adapter_name="SistaniAdapter",
        adapter_config={"book_url_pattern": "/arabic/book/{id}/"},
    )

    upsert_scholar(
        session,
        key="sistani",
        name_ar="السيد علي الحسيني السيستاني",
        name_en="Ali al-Husayni al-Sistani",
        madhhab_key="shia",
        school_key="jaafari",
        source_key="sistani",
        metadata_json={"role": "marja", "website": "https://www.sistani.org/"},
    )

    _propagate_lineage(session)
