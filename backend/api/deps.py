"""أدوات مشتركة لمسارات الـAPI: جلسة قاعدة البيانات وتحويل السجلات وشجرة الفهرس."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as SessionT

from backend.config import Settings, get_settings
from shared.db.models import Book, Issue, Madhhab, Scholar, School, Section


def get_db() -> Iterator[Session]:
    from shared.db.session import create_db_engine

    engine = create_db_engine(get_settings().database_url)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def get_app_settings() -> Settings:
    return get_settings()


def section_path(session: SessionT, section: Section) -> str:
    """بناء مسار القسم من الجذر: «كتاب الصوم ← الفصل الثاني…»."""
    parts: list[str] = []
    current: Section | None = section
    guard = 0
    while current is not None and guard < 20:
        leaf = current.title_original.split("»")[-1].strip()
        parts.append(leaf)
        current = session.get(Section, current.parent_id) if current.parent_id else None
        guard += 1
    return " ← ".join(reversed(parts))


def issue_to_out(session: SessionT, issue: Issue) -> dict:
    book = session.get(Book, issue.book_id)
    section = session.get(Section, issue.section_id)
    scholar = session.get(Scholar, issue.scholar_id) if issue.scholar_id else None
    madhhab = session.get(Madhhab, issue.madhhab_id) if issue.madhhab_id else None
    school = session.get(School, issue.school_id) if issue.school_id else None
    return {
        "id": issue.id,
        "issue_number": issue.issue_number,
        "title": issue.title,
        "text_original": issue.text_original,
        "book_id": issue.book_id,
        "book_title": book.title_original if book else "",
        "scholar": scholar.name_ar if scholar else None,
        "madhhab": madhhab.name_ar if madhhab else None,
        "school": school.name_ar if school else None,
        "section_path": section_path(session, section) if section else None,
        "section_id": issue.section_id,
        "source_url": issue.source_url,
        "content_hash": issue.content_hash,
        "source_revision": issue.source_revision,
        "scraped_at": issue.scraped_at,
        "verified_at": issue.verified_at,
    }


def build_toc(session: SessionT, book_id: int) -> list[dict]:
    """بناء شجرة الفهرس الكاملة مع عدد المسائل في كل عقدة."""

    from sqlalchemy import func

    sections = session.scalars(select(Section).where(Section.book_id == book_id)).all()
    count_rows = session.execute(
        select(Issue.section_id, func.count(Issue.id))
        .where(Issue.book_id == book_id)
        .group_by(Issue.section_id)
    ).all()
    counts: dict[int, int] = {row[0]: row[1] for row in count_rows}
    nodes: dict[int, dict] = {}
    for section in sections:
        nodes[section.id] = {
            "id": section.id,
            "title": section.title_original,
            "depth": section.depth,
            "position": section.position,
            "source_url": section.source_url,
            "issue_count": int(counts.get(section.id, 0)),
            "children": [],
        }
    roots: list[dict] = []
    for section in sorted(sections, key=lambda item: item.position):
        node = nodes[section.id]
        if section.parent_id and section.parent_id in nodes:
            nodes[section.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def book_summary(session: SessionT, book: Book) -> dict:
    from sqlalchemy import func

    scholar = session.get(Scholar, book.scholar_id) if book.scholar_id else None
    madhhab = session.get(Madhhab, book.madhhab_id) if book.madhhab_id else None
    school = session.get(School, book.school_id) if book.school_id else None
    sections_count = session.scalar(
        select(func.count(Section.id)).where(Section.book_id == book.id)
    )
    issues_count = session.scalar(select(func.count(Issue.id)).where(Issue.book_id == book.id))
    metadata = book.metadata_json or {}
    return {
        "id": book.id,
        "title": book.title_original,
        "scholar": scholar.name_ar if scholar else None,
        "madhhab": madhhab.name_ar if madhhab else None,
        "school": school.name_ar if school else None,
        "language": book.language,
        "source_url": book.source_url,
        "cover_url": metadata.get("cover_url"),
        "sections_count": int(sections_count or 0),
        "issues_count": int(issues_count or 0),
    }
