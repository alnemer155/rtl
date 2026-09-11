"""مزود السيستاني: بحث في قاعدة البيانات المحلية المزحوفة من sistani.org.

المصادر الجعفرية الرسمية — النصوص الأصلية مع روابطها الرسمية.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.research.base import IslamicSourceProvider, ResearchChunk
from backend.search.engine import SearchFilters, search_issues
from shared.db.models import Book, Issue, Scholar


class SistaniProvider(IslamicSourceProvider):
    key = "sistani"
    name = "المصادر الجعفرية — sistani.org"

    def __init__(self, session: Session) -> None:
        self._session = session

    async def search(
        self, query: str, limit: int = 6, filters: SearchFilters | None = None
    ) -> list[ResearchChunk]:
        return self.search_sync(query, limit=limit, filters=filters)

    def search_sync(
        self, query: str, limit: int = 6, filters: SearchFilters | None = None
    ) -> list[ResearchChunk]:
        _total, hits = search_issues(
            self._session, query, filters or SearchFilters(), page=1, page_size=limit
        )
        chunks: list[ResearchChunk] = []
        for hit in hits:
            issue = self._session.get(Issue, hit.issue_id)
            if issue is None:
                continue
            book = self._session.get(Book, issue.book_id)
            scholar = self._session.get(Scholar, issue.scholar_id) if issue.scholar_id else None
            section_label = ""
            if issue.section_id:
                from shared.db.models import Section

                section = self._session.get(Section, issue.section_id)
                if section is not None:
                    section_label = section.title_original.split("»")[-1].strip()
            detail_parts = [
                book.title_original if book else "",
                section_label,
                scholar.name_ar if scholar else "",
            ]
            chunks.append(
                ResearchChunk(
                    provider=self.key,
                    title=book.title_original if book else "مصدر السيستاني",
                    detail=" · ".join(part for part in detail_parts if part)
                    + (f" · المسألة {issue.issue_number}" if issue.issue_number is not None else ""),
                    text=issue.text_original,
                    url=issue.source_url,
                    metadata={
                        "issue_id": issue.id,
                        "issue_number": issue.issue_number,
                        "book": book.title_original if book else None,
                        "scholar": scholar.name_ar if scholar else None,
                        "madhhab": "الجعفري",
                    },
                )
            )
        return chunks
