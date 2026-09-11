"""نقل المحتوى المزحوف من SQLite المحلية إلى قاعدة PostgreSQL (مثل Neon).

ينسخ كل الجداول مع الحفاظ على المعرفات، ويثبت المناطق الزمنية (SQLite يخزن
UTC بلا منطقة)، ويعيد ضبط عدّادات الـidentity بعد الإدخال الصريح.
لا يعيد الزحف من الموقع — احتراماً للمصدر وسرعةً في التنفيذ.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import MetaData, Table, insert, select, text
from sqlalchemy.orm import Session

from shared.db.session import create_db_engine

# ترتيب يحترم الأعمدة الأجنبية
TABLES = [
    "madhhabs",
    "schools",
    "sources",
    "source_adapters",
    "scholars",
    "books",
    "sections",
    "issues",
    "hadiths",
    "text_versions",
    "crawl_runs",
    "crawl_page_state",
    "ai_answers",
]

DATETIME_COLUMNS = {
    "sources": ["created_at", "updated_at"],
    "source_adapters": ["created_at"],
    "scholars": ["created_at"],
    "books": ["created_at", "updated_at"],
    "sections": ["created_at"],
    "issues": ["scraped_at", "verified_at", "created_at", "updated_at"],
    "hadiths": ["created_at"],
    "text_versions": ["created_at"],
    "crawl_runs": ["started_at", "finished_at"],
    "crawl_page_state": ["updated_at"],
    "ai_answers": ["created_at"],
}


def _fix_datetimes(table: str, row: dict) -> dict:
    for column in DATETIME_COLUMNS.get(table, []):
        value = row.get(column)
        if isinstance(value, datetime) and value.tzinfo is None:
            row[column] = value.replace(tzinfo=UTC)
    return row


def transfer(source_url: str, target_url: str | None) -> dict:
    sqlite_engine = create_db_engine(source_url)
    pg_engine = create_db_engine(target_url)
    metadata = MetaData()

    report: dict[str, int] = {}
    with Session(pg_engine) as pg_session, Session(sqlite_engine) as lite_session:
        pg_session.execute(text("SET TIME ZONE 'UTC'"))
        # الهدف يبدأ نظيفاً (المرجعيات المزروعة سابقاً تُستبدل بنسخ المصدر)
        pg_session.execute(
            text(f"TRUNCATE {', '.join(reversed(TABLES))} RESTART IDENTITY CASCADE")
        )
        for table_name in TABLES:
            table = Table(table_name, metadata, autoload_with=sqlite_engine)
            rows = [dict(row) for row in lite_session.execute(select(table)).mappings().all()]
            if not rows:
                report[table_name] = 0
                continue
            target_table = Table(table_name, metadata, autoload_with=pg_engine)
            fixed = [_fix_datetimes(table_name, row) for row in rows]
            pg_session.execute(insert(target_table), fixed)
            report[table_name] = len(fixed)
        pg_session.commit()

        # إعادة ضبط عدادات الـidentity بعد الإدخال بمعرفات صريحة
        for table_name in TABLES:
            pg_session.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false)"
                )
            )
        pg_session.commit()
    return report


if __name__ == "__main__":
    import sys

    source = sys.argv[1] if len(sys.argv) > 1 else "sqlite:///./data/masadir.db"
    result = transfer(source, None)
    for table, count in result.items():
        print(f"{table}: {count}")
