"""مخططات Pydantic لاستجابات الـAPI — تحقق صارم من المدخلات والمخرجات."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MadhhabOut(BaseModel):
    id: int
    key: str
    name_ar: str
    name_en: str


class SchoolOut(BaseModel):
    id: int
    key: str
    name_ar: str
    name_en: str
    madhhab_id: int


class SourceOut(BaseModel):
    id: int
    key: str
    name: str
    domain: str
    base_url: str
    source_type: str
    official: bool
    language: str
    madhhab_id: int | None = None


class ScholarOut(BaseModel):
    id: int
    key: str
    name_ar: str
    name_en: str | None = None
    madhhab_id: int | None = None
    school_id: int | None = None
    source_id: int | None = None


class SectionNode(BaseModel):
    id: int
    title: str
    depth: int
    position: int
    source_url: str
    issue_count: int = 0
    children: list[SectionNode] = Field(default_factory=list)


class BookSummary(BaseModel):
    id: int
    title: str
    scholar: str | None = None
    madhhab: str | None = None
    school: str | None = None
    language: str
    source_url: str
    cover_url: str | None = None
    sections_count: int = 0
    issues_count: int = 0


class BookDetail(BookSummary):
    edition: str | None = None
    volume: str | None = None
    toc: list[SectionNode] = Field(default_factory=list)


class IssueOut(BaseModel):
    id: int
    issue_number: int | None
    title: str | None
    text_original: str
    book_id: int
    book_title: str
    scholar: str | None = None
    madhhab: str | None = None
    school: str | None = None
    section_path: str | None = None
    section_id: int
    source_url: str
    content_hash: str
    source_revision: int
    scraped_at: datetime | None = None
    verified_at: datetime | None = None


class SearchResult(BaseModel):
    issue: IssueOut
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    results: list[SearchResult]


class Citation(BaseModel):
    index: int
    issue_id: int
    issue_number: int | None
    scholar: str | None
    book_title: str
    section_path: str | None
    madhhab: str | None
    source_url: str
    text_original: str


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    madhhab: str | None = None
    school: str | None = None
    scholar: str | None = None
    book: int | None = None
    source: str | None = None


class HealthOut(BaseModel):
    status: str
    database: str
    issues_count: int
    ai_configured: bool


class StatsOut(BaseModel):
    madhhabs: int
    sources: int
    scholars: int
    books: int
    sections: int
    issues: int
    hadiths: int
    crawl_runs_total: int
    crawl_runs_failed: int
    ai_answers: int
    last_crawl: dict | None = None
