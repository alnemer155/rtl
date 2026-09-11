"""التحقق الآلي من صحة البيانات بعد الزحف مع تقرير."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from shared.arabic import to_search_text
from shared.db.models import Book, Issue, Section
from shared.hashing import sha256_hex


@dataclass
class ValidationReport:
    books_checked: int = 0
    issues_checked: int = 0
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_database(engine: Engine, book_id: int | None = None) -> ValidationReport:
    report = ValidationReport()
    with Session(engine) as session:
        book_ids: list[int]
        if book_id is not None:
            book_ids = [book_id]
        else:
            book_ids = list(session.scalars(select(Book.id)).all())

        for checked_book_id in book_ids:
            book = session.get(Book, checked_book_id)
            if book is None:
                report.errors.append({"scope": "book", "book_id": checked_book_id, "error": "book_missing"})
                continue
            report.books_checked += 1
            section_ids = set(
                session.scalars(select(Section.id).where(Section.book_id == checked_book_id)).all()
            )
            issues = session.scalars(select(Issue).where(Issue.book_id == checked_book_id)).all()
            report.issues_checked += len(issues)
            seen_keys: set[str] = set()
            for issue in issues:
                where = {"book_id": checked_book_id, "issue_id": issue.id}
                if issue.source_record_id in seen_keys:
                    report.errors.append({**where, "error": "duplicate_source_record_id"})
                seen_keys.add(issue.source_record_id)
                if not issue.text_original or not issue.text_original.strip():
                    report.errors.append({**where, "error": "empty_text_original"})
                if issue.issue_number is not None and issue.issue_number < 0:
                    report.errors.append({**where, "error": "invalid_issue_number"})
                if not issue.content_hash or issue.content_hash != sha256_hex(issue.text_original):
                    report.errors.append({**where, "error": "content_hash_mismatch"})
                if issue.section_id not in section_ids:
                    report.errors.append({**where, "error": "section_not_in_book"})
                parts = urlsplit(issue.source_url or "")
                if parts.scheme not in ("http", "https") or not parts.netloc:
                    report.errors.append({**where, "error": "invalid_source_url"})
                if not to_search_text(issue.text_original).strip():
                    report.warnings.append({**where, "error": "empty_text_search"})

            orphan_sections = session.scalar(
                select(func.count(Section.id)).where(
                    Section.book_id == checked_book_id,
                    Section.parent_id.isnot(None),
                    Section.parent_id.not_in(select(Section.id).where(Section.book_id == checked_book_id)),
                )
            )
            if orphan_sections:
                report.errors.append(
                    {"scope": "book", "book_id": checked_book_id, "error": "orphan_sections", "count": orphan_sections}
                )
    return report


def write_report(report: ValidationReport, path: str | Path = "exports/validation-report.json") -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path
