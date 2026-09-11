"""مخطط قاعدة البيانات الموحد — يستخدمه الزاحف وواجهة API معاً.

يدعم SQLite وPostgreSQL عبر DATABASE_URL. لا علاقة لهذا الملف بنسخ النصوص
بين المذاهب: كل سجل يحمل مصدره وانتماءه صراحة.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Madhhab(Base):
    """مذهب فقهي كبير (سني / شيعي)."""

    __tablename__ = "madhhabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    schools: Mapped[list[School]] = relationship(back_populates="madhhab")


class School(Base):
    """مدرسة فقهية تفصيلية (الجعفري، الحنفي، المالكي…)."""

    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    madhhab_id: Mapped[int] = mapped_column(ForeignKey("madhhabs.id"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)

    madhhab: Mapped[Madhhab] = relationship(back_populates="schools")


class Source(Base):
    """مصدر رسمي يُزحف منه المحتوى (موقع مرجعية، دار فتوى…)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="website", nullable=False)
    official: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ar", nullable=False)
    madhhab_id: Mapped[int | None] = mapped_column(ForeignKey("madhhabs.id"), index=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    adapters: Mapped[list[SourceAdapter]] = relationship(back_populates="source")


class SourceAdapter(Base):
    """سجل ربط المصدر بمحوله البرمجي — إضافة مصادر جديدة تتم هنا دون تعديل المحرك."""

    __tablename__ = "source_adapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True, nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped[Source] = relationship(back_populates="adapters")


class Scholar(Base):
    """عالم / مرجع ديني."""

    __tablename__ = "scholars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    madhhab_id: Mapped[int | None] = mapped_column(ForeignKey("madhhabs.id"), index=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Book(Base):
    """كتاب فقهي أو حديثي مرتبط بمصدر."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True, nullable=False)
    scholar_id: Mapped[int | None] = mapped_column(ForeignKey("scholars.id"), index=True)
    madhhab_id: Mapped[int | None] = mapped_column(ForeignKey("madhhabs.id"), index=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), index=True)
    slug: Mapped[str | None] = mapped_column(String(200))
    title_original: Mapped[str] = mapped_column(String(500), nullable=False)
    title_normalised: Mapped[str] = mapped_column(String(500), nullable=False)
    edition: Mapped[str | None] = mapped_column(String(200))
    volume: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="ar", nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sections: Mapped[list[Section]] = relationship(back_populates="book", foreign_keys="Section.book_id")


class Section(Base):
    """عقدة في شجرة فهرس الكتاب: كتاب ← باب ← فصل ← فرع (parent_id)."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"), index=True)
    title_original: Mapped[str] = mapped_column(String(500), nullable=False)
    title_search: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    book: Mapped[Book] = relationship(back_populates="sections", foreign_keys=[book_id])

    __table_args__ = (UniqueConstraint("book_id", "source_url", name="uq_section_book_url"),)


class Issue(Base):
    """المسألة الفقهية — الوحدة الأصلية للتخزين والبحث وRAG (Issue = Chunk)."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True, nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), index=True, nullable=False)
    scholar_id: Mapped[int | None] = mapped_column(ForeignKey("scholars.id"), index=True)
    madhhab_id: Mapped[int | None] = mapped_column(ForeignKey("madhhabs.id"), index=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), index=True)
    issue_number: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    text_search: Mapped[str] = mapped_column(Text, nullable=False)
    text_embedding: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    book: Mapped[Book] = relationship()
    section: Mapped[Section] = relationship()


class Hadith(Base):
    """بنية الأحاديث — جاهزة للإدخال لاحقاً؛ لا تُحوَّل النصوص الفقهية إليها."""

    __tablename__ = "hadiths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True, nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"), index=True)
    hadith_number: Mapped[str | None] = mapped_column(String(50), index=True)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    text_search: Mapped[str] = mapped_column(Text, nullable=False)
    text_embedding: Mapped[str | None] = mapped_column(Text)
    narrator: Mapped[str | None] = mapped_column(String(300))
    isnad: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TextVersion(Base):
    """سجل تاريخ النصوص: كل تغيير حقيقي في النص الأصلي يُحفظ هنا دون استبدال صامت."""

    __tablename__ = "text_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrawlRun(Base):
    """سجل تشغيلة زحف واحدة لكتاب/مصدر مع عدّاداتها وأخطائها."""

    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True, nullable=False)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[list] = mapped_column(JSON, default=list)

    book: Mapped[Book | None] = relationship()


class CrawlPageState(Base):
    """حالة كل صفحة داخل كتاب — أساس الاستكمال (Resume) دون البدء من الصفر."""

    __tablename__ = "crawl_page_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    records_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("book_id", "url", name="uq_page_book_url"),)


class AiAnswer(Base):
    """محتوى مشتق: أجوبة Gemini لا تُخزّن أبداً كسجلات مصدرية."""

    __tablename__ = "ai_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    madhhab_filter: Mapped[str | None] = mapped_column(String(50))
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    citations_json: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(50), default="gemini")
    model: Mapped[str | None] = mapped_column(String(100))
    finish_status: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# فهارس مركبة شائعة الاستعلام
Index("ix_issues_book_number", Issue.book_id, Issue.issue_number)
Index("ix_issues_madhhab_book", Issue.madhhab_id, Issue.book_id)
Index("ix_sections_book_position", Section.book_id, Section.position)
Index("ix_books_source", Book.source_id, Book.id)
