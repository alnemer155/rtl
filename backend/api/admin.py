"""مسارات الإدارة: إحصاءات قاعدة البيانات والزحف والذكاء الاصطناعي."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from shared.db.models import AiAnswer, Book, CrawlRun, Issue, Madhhab, Scholar, Section, Source

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def stats(session: Session = Depends(get_db)) -> dict:
    def count(model) -> int:
        return int(session.scalar(select(func.count(model.id))) or 0)

    last_run = session.scalar(select(CrawlRun).order_by(desc(CrawlRun.id)).limit(1))
    return {
        "madhhabs": count(Madhhab),
        "sources": count(Source),
        "scholars": count(Scholar),
        "books": count(Book),
        "sections": count(Section),
        "issues": count(Issue),
        "crawl_runs_total": count(CrawlRun),
        "crawl_runs_failed": int(
            session.scalar(
                select(func.count(CrawlRun.id)).where(CrawlRun.status.in_(("failed", "partial")))
            )
            or 0
        ),
        "ai_answers": count(AiAnswer),
        "last_crawl": (
            {
                "id": last_run.id,
                "status": last_run.status,
                "book_id": last_run.book_id,
                "pages_processed": last_run.pages_processed,
                "records_created": last_run.records_created,
                "records_updated": last_run.records_updated,
                "records_unchanged": last_run.records_unchanged,
                "records_failed": last_run.records_failed,
                "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
                "finished_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            }
            if last_run
            else None
        ),
    }


@router.get("/crawl-runs")
def crawl_runs(limit: int = 20, session: Session = Depends(get_db)) -> list[dict]:
    runs = session.scalars(select(CrawlRun).order_by(desc(CrawlRun.id)).limit(limit)).all()
    return [
        {
            "id": run.id,
            "source_id": run.source_id,
            "book_id": run.book_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "pages_discovered": run.pages_discovered,
            "pages_processed": run.pages_processed,
            "records_created": run.records_created,
            "records_updated": run.records_updated,
            "records_unchanged": run.records_unchanged,
            "records_failed": run.records_failed,
            "errors": (run.error_log or [])[:10],
        }
        for run in runs
    ]


@router.get("/sources")
def admin_sources(session: Session = Depends(get_db)) -> list[dict]:
    sources = session.scalars(select(Source)).all()
    return [
        {
            "id": source.id,
            "key": source.key,
            "name": source.name,
            "domain": source.domain,
            "active": source.active,
            "official": source.official,
            "books": int(
                session.scalar(select(func.count(Book.id)).where(Book.source_id == source.id)) or 0
            ),
        }
        for source in sources
    ]
