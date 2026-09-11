"""مسارات الـAPI: الكتب والمسائل والبحث والبيانات المرجعية والصحة."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import book_summary, build_toc, get_db, issue_to_out
from backend.search.engine import SearchFilters, search_issues
from shared.db.models import Book, Issue, Madhhab, Scholar, School, Source

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------- health
@router.get("/health")
def health(session: Session = Depends(get_db)) -> dict:
    from sqlalchemy import func

    issues_count = session.scalar(select(func.count(Issue.id))) or 0
    from backend.config import get_settings

    return {
        "status": "ok",
        "database": "connected",
        "issues_count": issues_count,
        "ai_configured": bool(get_settings().gemini_api_key),
    }


# --------------------------------------------------------------------- meta
@router.get("/madhhabs")
def list_madhhabs(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.scalars(select(Madhhab)).all()
    return [
        {
            "id": row.id,
            "key": row.key,
            "name_ar": row.name_ar,
            "name_en": row.name_en,
            "schools": [
                {"id": school.id, "key": school.key, "name_ar": school.name_ar, "name_en": school.name_en}
                for school in session.scalars(select(School).where(School.madhhab_id == row.id)).all()
            ],
        }
        for row in rows
    ]


@router.get("/sources")
def list_sources(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.scalars(select(Source).where(Source.active.is_(True))).all()
    return [
        {
            "id": row.id,
            "key": row.key,
            "name": row.name,
            "domain": row.domain,
            "base_url": row.base_url,
            "source_type": row.source_type,
            "official": row.official,
            "language": row.language,
            "madhhab_id": row.madhhab_id,
        }
        for row in rows
    ]


@router.get("/scholars")
def list_scholars(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.scalars(select(Scholar)).all()
    return [
        {
            "id": row.id,
            "key": row.key,
            "name_ar": row.name_ar,
            "name_en": row.name_en,
            "madhhab_id": row.madhhab_id,
            "school_id": row.school_id,
            "source_id": row.source_id,
        }
        for row in rows
    ]


# --------------------------------------------------------------------- books
@router.get("/books")
def list_books(session: Session = Depends(get_db)) -> list[dict]:
    books = session.scalars(select(Book).order_by(Book.id)).all()
    return [book_summary(session, book) for book in books]


@router.get("/books/{book_id}")
def get_book(book_id: int, session: Session = Depends(get_db)) -> dict:
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="book_not_found")
    detail = book_summary(session, book)
    detail["edition"] = book.edition
    detail["volume"] = book.volume
    detail["toc"] = build_toc(session, book_id)
    return detail


@router.get("/books/{book_id}/sections")
def get_book_sections(book_id: int, session: Session = Depends(get_db)) -> list[dict]:
    if session.get(Book, book_id) is None:
        raise HTTPException(status_code=404, detail="book_not_found")
    return build_toc(session, book_id)


# -------------------------------------------------------------------- issues
@router.get("/issues/by-number/{number}")
def issues_by_number(number: int, session: Session = Depends(get_db)) -> list[dict]:
    """كل المسائل ذات الرقم نفسه عبر الكتب والمذاهب — المقارنة تبدأ من هنا."""
    issues = session.scalars(select(Issue).where(Issue.issue_number == number)).all()
    return [issue_to_out(session, issue) for issue in issues]


@router.get("/issues/{issue_id}")
def get_issue(issue_id: int, session: Session = Depends(get_db)) -> dict:
    issue = session.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="issue_not_found")
    return issue_to_out(session, issue)


# -------------------------------------------------------------------- search
@router.get("/search")
def search(
    q: str = Query(default="", max_length=500),
    madhhab: str | None = None,
    school: str | None = None,
    scholar: str | None = None,
    book: int | None = None,
    section: int | None = None,
    issue_number: int | None = None,
    source: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_db),
) -> dict:
    filters = SearchFilters(
        madhhab=madhhab,
        school=school,
        scholar=scholar,
        book=book,
        section=section,
        issue_number=issue_number,
        source=source,
    )
    total, hits = search_issues(session, q, filters, page=page, page_size=page_size)
    results = []
    for hit in hits:
        issue = session.get(Issue, hit.issue_id)
        if issue is None:
            continue
        results.append({"issue": issue_to_out(session, issue), "score": hit.rank, "snippet": hit.snippet})
    return {
        "query": q,
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": results,
    }
