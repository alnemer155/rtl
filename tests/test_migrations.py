"""اختبارات الترحيلات: ترقية قاعدة فارغة عبر Alembic ثم تهيئة فهارس البحث."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from shared.db import fts
from shared.db.session import create_db_engine


def test_alembic_upgrade_head_creates_schema(tmp_path):
    db_path = tmp_path / "migration-test.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    expected = {
        "madhhabs", "schools", "sources", "source_adapters", "scholars", "books",
        "sections", "issues", "hadiths", "text_versions", "crawl_runs",
        "crawl_page_state", "ai_answers",
    }
    tables = set(inspector.get_table_names())
    assert expected <= tables


def test_ensure_fts_is_idempotent(tmp_path):
    db_path = tmp_path / "fts-test.db"
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    from shared.db.models import Base

    Base.metadata.create_all(engine)
    fts.ensure_fts(engine)
    fts.ensure_fts(engine)  # استدعاء ثانٍ لا يفشل
    inspector = inspect(engine)
    assert "issues_fts" in inspector.get_table_names()


def test_fts_triggers_keep_index_in_sync(tmp_path):
    db_path = tmp_path / "fts-sync.db"
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    from shared.db.models import Base

    Base.metadata.create_all(engine)
    fts.ensure_fts(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO issues (book_id, section_id, text_original, text_search, source_url,"
                " source_record_id, content_hash, issue_number, source_revision, scraped_at, created_at, updated_at)"
                " VALUES (1, 1, 'مسألة 33: نص', 'مساله 33 نص', 'https://x/1/', 'key1', 'h1', 33, 0,"
                " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        matches = conn.execute(
            text("SELECT rowid FROM issues_fts WHERE issues_fts MATCH '\"نص\"*'")
        ).all()
        assert matches
        # تحديث النص يجب أن ينعكس في الفهرس (كلمة جديدة ليست بادئة للقديمة)
        conn.execute(text("UPDATE issues SET text_search = 'كلام آخر' WHERE rowid = 1"))
        stale = conn.execute(text("SELECT rowid FROM issues_fts WHERE issues_fts MATCH '\"مساله\"*'")).all()
        assert not stale
        fresh = conn.execute(text("SELECT rowid FROM issues_fts WHERE issues_fts MATCH '\"كلام\"*'")).all()
        assert fresh
