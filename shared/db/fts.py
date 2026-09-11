"""فهارس البحث النصي الكاملة: FTS5 لـ SQLite وtsvector لـ PostgreSQL.

تُنشأ دائماً بصورة idempotent — تستدعى من الترحيلات ومن بدء تشغيل API ومن
الزاحف حتى يبقى الفهرس متزامناً مع جدول issues عبر Triggers.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

_SQLITE_FTS_STATEMENTS = [
    # جدول FTS خارجي مرتبط بصفوف issues (rowid = issues.id)
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
        text_search, title, content='issues', content_rowid='id',
        tokenize='unicode61'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS issues_fts_insert AFTER INSERT ON issues BEGIN
        INSERT INTO issues_fts(rowid, text_search, title)
        VALUES (new.id, new.text_search, COALESCE(new.title, ''));
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS issues_fts_delete AFTER DELETE ON issues BEGIN
        INSERT INTO issues_fts(issues_fts, rowid, text_search, title)
        VALUES ('delete', old.id, old.text_search, COALESCE(old.title, ''));
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS issues_fts_update AFTER UPDATE ON issues BEGIN
        INSERT INTO issues_fts(issues_fts, rowid, text_search, title)
        VALUES ('delete', old.id, old.text_search, COALESCE(old.title, ''));
        INSERT INTO issues_fts(rowid, text_search, title)
        VALUES (new.id, new.text_search, COALESCE(new.title, ''));
    END
    """,
]

_POSTGRES_INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS ix_issues_text_search_trgm ON issues USING gin (text_search gin_trgm_ops)",
]


def ensure_fts(engine: Engine) -> None:
    """تهيئة فهارس البحث حسب المحرك — آمنة للاستدعاء المتكرر."""
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            for statement in _SQLITE_FTS_STATEMENTS:
                conn.execute(text(statement))
    elif engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            # pg_trgm اختياري؛ إن لم يتوفر نكمل بلا فهرس ثلاثي
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                for statement in _POSTGRES_INDEX_STATEMENTS:
                    conn.execute(text(statement))
            except Exception:  # noqa: BLE001 — الامتداد اختياري وليس شرطاً للتشغيل
                pass


def rebuild_sqlite_fts(engine: Engine) -> None:
    """إعادة بناء كاملة لفهرس FTS5 من جدول issues (أمر صيانة يدوي)."""
    ensure_fts(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO issues_fts(issues_fts) VALUES ('rebuild')"))
