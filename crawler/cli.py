"""واجهة سطر الأوامر للزاحف: crawl / resume / validate / export / stats / reindex / seed."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crawler.adapters.registry import get_adapter
from crawler.core.config import load_settings
from crawler.pipeline import CrawlPipeline
from crawler.storage.database import ensure_schema, seed_reference_data
from crawler.storage.json_export import export_book
from crawler.validation import validate_database, write_report
from shared.db import fts
from shared.db.models import Book, CrawlRun, Issue, Madhhab, Scholar, Section, Source
from shared.db.session import create_db_engine


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def cmd_crawl(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    ensure_schema(engine)
    with Session(engine) as session:
        seed_reference_data(session)
    adapter = get_adapter(args.source)
    settings = load_settings()
    if args.min_interval is not None:
        settings.min_interval = args.min_interval
    if args.concurrency is not None:
        settings.concurrency = args.concurrency
    pipeline = CrawlPipeline(engine, adapter, settings)
    stats = asyncio.run(pipeline.run(args.book, refresh=args.refresh, max_pages=args.max_pages))
    print(
        f"run={stats.run_id} discovered={stats.pages_discovered} processed={stats.pages_processed} "
        f"skipped={stats.pages_skipped} created={stats.records_created} updated={stats.records_updated} "
        f"unchanged={stats.records_unchanged} failed={stats.records_failed} errors={len(stats.errors)}"
    )
    return 0 if not stats.errors or args.allow_partial else 1


def cmd_validate(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    report = validate_database(engine, book_id=args.book_id)
    path = write_report(report, args.out)
    print(f"books={report.books_checked} issues={report.issues_checked} errors={len(report.errors)} "
          f"warnings={len(report.warnings)} report={path}")
    for error in report.errors[:20]:
        print(f"  ERROR {error}")
    return 0 if report.ok else 1


def cmd_export(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    if args.book_id:
        book_ids = [args.book_id]
    else:
        with Session(engine) as session:
            book_ids = list(session.scalars(select(Book.id)).all())
    for book_id in book_ids:
        path = export_book(engine, book_id, args.out)
        print(f"exported book={book_id} -> {path}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    with Session(engine) as session:
        print(f"madhhabs:  {session.scalar(select(func.count(Madhhab.id)))}")
        print(f"sources:   {session.scalar(select(func.count(Source.id)))}")
        print(f"scholars:  {session.scalar(select(func.count(Scholar.id)))}")
        print(f"books:     {session.scalar(select(func.count(Book.id)))}")
        print(f"sections:  {session.scalar(select(func.count(Section.id)))}")
        print(f"issues:    {session.scalar(select(func.count(Issue.id)))}")
        runs = session.scalars(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(5)).all()
        for run in runs:
            print(
                f"crawl_run {run.id}: {run.status} book={run.book_id} processed={run.pages_processed} "
                f"created={run.records_created} failed={run.records_failed}"
            )
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    fts.rebuild_sqlite_fts(engine)
    print("fts rebuilt")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    engine = create_db_engine(args.database_url)
    ensure_schema(engine)
    from scripts.seed_reference import seed_all

    with Session(engine) as session:
        seed_all(session)
    print("reference data seeded")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crawler", description="محرك زحف منصة المصادر")
    parser.add_argument("--database-url", default=None, help="DATABASE_URL (افتراضياً من البيئة)")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    crawl = sub.add_parser("crawl", help="زحف كتاب من مصدر")
    crawl.add_argument("--source", required=True, help="مفتاح المصدر (مثل sistani)")
    crawl.add_argument("--book", required=True, help="رابط صفحة الكتاب")
    crawl.add_argument("--refresh", action="store_true", help="إعادة جلب الصفحات المكتملة")
    crawl.add_argument("--max-pages", type=int, default=None)
    crawl.add_argument("--min-interval", type=float, default=None)
    crawl.add_argument("--concurrency", type=int, default=None)
    crawl.add_argument("--allow-partial", action="store_true", help="إبقاء الخروج 0 مع أخطاء جزئية")
    crawl.set_defaults(func=cmd_crawl)

    resume = sub.add_parser("resume", help="استكمال زحف كتاب متوقف (يتخطى الصفحات المكتملة)")
    resume.add_argument("--source", required=True)
    resume.add_argument("--book", required=True)
    resume.add_argument("--max-pages", type=int, default=None)
    resume.add_argument("--min-interval", type=float, default=None)
    resume.add_argument("--concurrency", type=int, default=None)
    resume.add_argument("--allow-partial", action="store_true")
    resume.set_defaults(func=cmd_crawl, refresh=False)

    validate = sub.add_parser("validate", help="تحقق آلي من صحة البيانات")
    validate.add_argument("--book-id", type=int, default=None)
    validate.add_argument("--out", default="exports/validation-report.json")
    validate.set_defaults(func=cmd_validate)

    export = sub.add_parser("export", help="تصدير كتاب إلى JSON")
    export.add_argument("--book-id", type=int, default=None)
    export.add_argument("--out", default="exports")
    export.set_defaults(func=cmd_export)

    sub.add_parser("stats", help="إحصاءات قاعدة البيانات").set_defaults(func=cmd_stats)
    sub.add_parser("reindex", help="إعادة بناء فهرس البحث (SQLite FTS)").set_defaults(func=cmd_reindex)
    sub.add_parser("seed", help="تهيئة البيانات المرجعية").set_defaults(func=cmd_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
