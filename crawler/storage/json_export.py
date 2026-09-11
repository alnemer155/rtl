"""تصدير الكتب إلى JSON مع Metadata كاملة لكل سجل."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from shared.db.models import Book, Issue, Madhhab, Scholar, School, Section, Source


def _section_path(session: Session, section: Section) -> str:
    parts: list[str] = []
    current: Section | None = section
    while current is not None:
        leaf = current.title_original.split("»")[-1].strip()
        parts.append(leaf)
        current = session.get(Section, current.parent_id) if current.parent_id else None
    return " ← ".join(reversed(parts))


def build_book_export(engine: Engine, book_id: int) -> dict:
    with Session(engine) as session:
        book = session.get(Book, book_id)
        if book is None:
            raise ValueError(f"book {book_id} not found")
        source = session.get(Source, book.source_id)
        scholar = session.get(Scholar, book.scholar_id) if book.scholar_id else None
        madhhab = session.get(Madhhab, book.madhhab_id) if book.madhhab_id else None
        school = session.get(School, book.school_id) if book.school_id else None

        sections = session.scalars(select(Section).where(Section.book_id == book.id)).all()
        sections_by_id = {section.id: section for section in sections}

        issues = session.scalars(select(Issue).where(Issue.book_id == book.id)).all()
        issues_payload = []
        for issue in sorted(issues, key=lambda item: (item.issue_number is None, item.issue_number or 0)):
            section = sections_by_id.get(issue.section_id)
            issues_payload.append(
                {
                    "madhhab": madhhab.name_ar if madhhab else None,
                    "school": school.name_ar if school else None,
                    "scholar": scholar.name_ar if scholar else None,
                    "book": book.title_original,
                    "section": _section_path(session, section) if section else None,
                    "issue_number": issue.issue_number,
                    "text_original": issue.text_original,
                    "source_url": issue.source_url,
                    "content_hash": issue.content_hash,
                    "source_record_id": issue.source_record_id,
                    "source_revision": issue.source_revision,
                    "scraped_at": issue.scraped_at.isoformat() if issue.scraped_at else None,
                }
            )

        def build_tree(parent_id: int | None) -> list[dict]:
            nodes = []
            for section in sorted(
                (s for s in sections if s.parent_id == parent_id), key=lambda s: s.position
            ):
                nodes.append(
                    {
                        "title": section.title_original,
                        "depth": section.depth,
                        "position": section.position,
                        "source_url": section.source_url,
                        "children": build_tree(section.id),
                    }
                )
            return nodes

        return {
            "source": {"key": source.key, "name": source.name, "domain": source.domain} if source else None,
            "madhhab": madhhab.name_ar if madhhab else None,
            "school": school.name_ar if school else None,
            "scholar": scholar.name_ar if scholar else None,
            "book": {
                "id": book.id,
                "title": book.title_original,
                "edition": book.edition,
                "volume": book.volume,
                "language": book.language,
                "source_url": book.source_url,
                "metadata": book.metadata_json,
            },
            "toc": build_tree(None),
            "issues_count": len(issues_payload),
            "issues": issues_payload,
        }


def export_book(engine: Engine, book_id: int, out_dir: str | Path = "exports") -> Path:
    payload = build_book_export(engine, book_id)
    source_key = (payload.get("source") or {}).get("key") or "unknown"
    title = payload["book"]["title"]
    slug = re.sub(r"[\s«»]+", "-", title).strip("-")[:80] or f"book-{book_id}"
    path = Path(out_dir) / source_key / f"{slug}-{book_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
