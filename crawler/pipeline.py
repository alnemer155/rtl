"""منسّق الزحف: صفحة الكتاب ← الفهرس ← الصفحات ← السجلات ← قاعدة البيانات.

يطبق: robots.txt، معدل طلبات محافظ، استكمال (Resume) عبر crawl_page_state،
نسخَ نصية (text_original/search/embedding)، تجزئة، وكشف التغيير مع Versioning.
خطأ صفحة واحدة لا يوقف الكتاب — يُسجل ويُكمل.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from crawler.adapters.base import BookOutline, RawRecord, SourceAdapter
from crawler.core.config import CrawlSettings
from crawler.core.http import AsyncHttpClient, HttpError
from crawler.core.robots import RobotsDenied, RobotsGuard
from crawler.storage.database import upsert_source
from shared.arabic import to_embedding_text, to_search_text
from shared.db.models import (
    Book,
    CrawlPageState,
    CrawlRun,
    Issue,
    Section,
    TextVersion,
)
from shared.hashing import sha256_hex, stable_record_key

logger = logging.getLogger("[crawler.pipeline]")


@dataclass
class CrawlStats:
    run_id: int = 0
    pages_discovered: int = 0
    pages_processed: int = 0
    pages_skipped: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_failed: int = 0
    errors: list[dict] = field(default_factory=list)


class CrawlPipeline:
    def __init__(self, engine: Engine, adapter: SourceAdapter, settings: CrawlSettings) -> None:
        self._engine = engine
        self._adapter = adapter
        self._settings = settings

    # ------------------------------------------------------------------ عام
    async def run(self, book_url: str, refresh: bool = False, max_pages: int | None = None) -> CrawlStats:
        source_id = self._ensure_source_row()
        self._mark_stale_runs(source_id)
        stats = CrawlStats()
        run = CrawlRun(source_id=source_id, status="running")
        with Session(self._engine) as session:
            session.add(run)
            session.commit()
            stats.run_id = run.id
        async with AsyncHttpClient(
            allowed_domains=self._adapter.allowed_domains,
            user_agent=self._settings.user_agent,
            min_interval=self._settings.min_interval,
            concurrency=self._settings.concurrency,
            max_attempts=self._settings.max_attempts,
        ) as client:
            guard = RobotsGuard(self._settings.user_agent, client.raw_client)
            try:
                await guard.ensure_allowed(book_url)
                fetched = await client.get_html(book_url)
            except (RobotsDenied, HttpError) as error:
                self._fail_run(run.id, f"book_page: {error}")
                raise
            outline = self._adapter.parse_book(fetched.content, book_url)
            book_id = self._upsert_book_and_sections(book_url, outline)
            self._set_run_book(run.id, book_id)
            section_urls = [entry.url for entry in outline.toc]
            if not section_urls:
                # كتاب بصفحة واحدة: صفحة الكتاب نفسها هي المحتوى
                section_urls = [book_url]
            limit = max_pages if max_pages is not None else self._settings.max_pages
            if limit is not None:
                section_urls = section_urls[:limit]
            stats.pages_discovered = len(section_urls)
            self._update_run(run.id, pages_discovered=stats.pages_discovered)

            await self._crawl_sections(client, book_id, book_url, section_urls, refresh, stats)
            status = "completed" if not stats.errors else "partial"
            self._finish_run(run.id, status, stats)
            logger.info(
                "[book] done run=%d book=%d discovered=%d processed=%d skipped=%d created=%d updated=%d unchanged=%d failed=%d",
                stats.run_id,
                book_id,
                stats.pages_discovered,
                stats.pages_processed,
                stats.pages_skipped,
                stats.records_created,
                stats.records_updated,
                stats.records_unchanged,
                stats.records_failed,
            )
            return stats

    # ------------------------------------------------------------ قاعدة البيانات
    def _mark_stale_runs(self, source_id: int) -> None:
        """تشغيلات توقفت دون اكتمال (انقطاع عملية) تُعلَّم بدل بقائها running."""
        from sqlalchemy import update

        with Session(self._engine) as session:
            session.execute(
                update(CrawlRun)
                .where(CrawlRun.source_id == source_id, CrawlRun.status == "running")
                .values(status="interrupted")
            )
            session.commit()

    def _ensure_source_row(self) -> int:
        with Session(self._engine) as session:
            source = upsert_source(
                session,
                key=self._adapter.source_key,
                domain=self._primary_domain(),
                base_url=f"https://{self._primary_domain()}/",
                adapter_name=self._adapter.adapter_name,
            )
            return source.id

    def _primary_domain(self) -> str:
        return sorted(self._adapter.allowed_domains)[0].removeprefix("www.")

    def _upsert_book_and_sections(self, book_url: str, outline: BookOutline) -> int:
        with Session(self._engine) as session:
            source_id = self._source_id(session)
            book = session.scalar(select(Book).where(Book.source_url == book_url))
            if book is None:
                book = Book(source_id=source_id, source_url=book_url)
                session.add(book)
            book.title_original = outline.title
            book.title_normalised = to_search_text(outline.title)
            book.metadata_json = outline.metadata
            # انتماء الكتاب يورَّث من المصدر إن لم يُحدد
            if book.madhhab_id is None:
                book.madhhab_id = self._source_field(session, "madhhab_id")
            if book.school_id is None:
                book.school_id = self._source_field(session, "school_id")
            if book.scholar_id is None:
                book.scholar_id = self._source_scholar_id(session)
            session.flush()

            sections = session.scalars(select(Section).where(Section.book_id == book.id)).all()
            sections_by_url = {section.source_url: section for section in sections}

            path_map: dict[tuple[str, ...], int] = {}
            for position, entry in enumerate(outline.toc):
                parts = tuple(part.strip() for part in entry.title_full.split("»") if part.strip())
                if not parts:
                    continue
                parent_id: int | None = None
                depth = 0
                for cut in range(len(parts) - 1, 0, -1):
                    prefix = parts[:cut]
                    if prefix in path_map:
                        parent_id = path_map[prefix]
                        depth = cut
                        break
                section = sections_by_url.get(entry.url)
                if section is None:
                    section = Section(
                        book_id=book.id,
                        source_url=entry.url,
                        parent_id=parent_id,
                        title_original=entry.title_full,
                        title_search=to_search_text(entry.title_full),
                        position=position,
                        depth=depth,
                    )
                    session.add(section)
                    session.flush()
                    sections_by_url[entry.url] = section
                else:
                    section.parent_id = parent_id
                    section.title_original = entry.title_full
                    section.title_search = to_search_text(entry.title_full)
                    section.position = position
                    section.depth = depth
                path_map[parts] = section.id
            session.commit()
            return book.id

    def _source_id(self, session: Session) -> int:
        from shared.db.models import Source

        source_id = session.scalar(select(Source.id).where(Source.key == self._adapter.source_key))
        if source_id is None:
            raise ValueError(f"source '{self._adapter.source_key}' is not registered")
        return source_id

    def _source_field(self, session: Session, field_name: str):
        from shared.db.models import Source

        source = session.scalar(select(Source).where(Source.key == self._adapter.source_key))
        return getattr(source, field_name) if source else None

    def _source_scholar_id(self, session: Session) -> int | None:
        from shared.db.models import Scholar

        return session.scalar(select(Scholar.id).where(Scholar.source_id == self._source_id(session)))

    # ------------------------------------------------------------- الصفحات
    async def _crawl_sections(
        self,
        client: AsyncHttpClient,
        book_id: int,
        book_url: str,
        section_urls: list[str],
        refresh: bool,
        stats: CrawlStats,
    ) -> None:
        state_map = self._load_page_states(book_id)
        queue: asyncio.Queue[tuple[str, CrawlPageState | None]] = asyncio.Queue()
        for url in section_urls:
            queue.put_nowait((url, state_map.get(url)))

        async def worker() -> None:
            while True:
                try:
                    url, state = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                if state is not None and state.status == "done" and not refresh:
                    # العنصر مكتمل سابقاً — يجب إنهاء عدّه في الطابور قبل التخطي
                    queue.task_done()
                    stats.pages_skipped += 1
                    logger.info("[page] skip (done) %s", url)
                    continue
                try:
                    await self._process_page(client, book_id, book_url, url, stats)
                except (RobotsDenied, HttpError) as error:
                    self._record_page_failure(book_id, url, str(error))
                    stats.errors.append({"url": url, "error": str(error)})
                    logger.warning("[page] failed %s — %s", url, error)
                except Exception as error:  # noqa: BLE001 — صفحة واحدة لا توقف الكتاب
                    self._record_page_failure(book_id, url, repr(error))
                    stats.errors.append({"url": url, "error": repr(error)})
                    logger.exception("[page] unexpected failure %s", url)
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(max(1, self._settings.concurrency))]
        await queue.join()
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    def _load_page_states(self, book_id: int) -> dict[str, CrawlPageState]:
        with Session(self._engine) as session:
            states = session.scalars(select(CrawlPageState).where(CrawlPageState.book_id == book_id)).all()
            return {state.url: state for state in states}

    async def _process_page(
        self,
        client: AsyncHttpClient,
        book_id: int,
        book_url: str,
        url: str,
        stats: CrawlStats,
    ) -> None:
        fetched = await client.get_html(url)
        page = self._adapter.parse_page(fetched.content, url)
        raw_records = self._adapter.extract_records(page)
        raw_records = [self._adapter.normalise_record(record) for record in raw_records]
        section_id = self._resolve_section_id(book_id, url, book_url)
        created = updated = unchanged = failed = 0
        with Session(self._engine) as session:
            book = session.get(Book, book_id)
            if book is None:
                raise ValueError(f"book {book_id} disappeared during crawl")
            for record in raw_records:
                errors = self._adapter.validate_record(record)
                if errors:
                    failed += 1
                    stats.errors.append({"url": url, "error": f"validation: {','.join(errors)}"})
                    continue
                result = self._persist_record(session, book, section_id, url, record)
                created += result == "created"
                updated += result == "updated"
                unchanged += result == "unchanged"
            session.commit()
        stats.records_created += created
        stats.records_updated += updated
        stats.records_unchanged += unchanged
        stats.records_failed += failed
        stats.pages_processed += 1
        self._upsert_page_state(book_id, url, status="done", content_hash=None, records_count=len(raw_records))
        self._update_run(
            stats.run_id,
            pages_processed=stats.pages_processed,
            records_created=stats.records_created,
            records_updated=stats.records_updated,
            records_unchanged=stats.records_unchanged,
            records_failed=stats.records_failed,
        )
        logger.info(
            "[page] ok records=%d created=%d updated=%d unchanged=%d %s",
            len(raw_records),
            created,
            updated,
            unchanged,
            url,
        )

    def _resolve_section_id(self, book_id: int, page_url: str, book_url: str) -> int:
        with Session(self._engine) as session:
            section = session.scalar(
                select(Section).where(Section.book_id == book_id, Section.source_url == page_url)
            )
            if section is not None:
                return section.id
            # صفحة الكتاب نفسها: أنشئ قسم جذرياً باسم الكتاب
            book = session.get(Book, book_id)
            if book is None:
                raise ValueError(f"book {book_id} disappeared during crawl")
            section = Section(
                book_id=book_id,
                parent_id=None,
                title_original=book.title_original,
                title_search=book.title_normalised,
                position=-1,
                depth=0,
                source_url=book_url,
            )
            existing = session.scalar(
                select(Section).where(Section.book_id == book_id, Section.source_url == book_url)
            )
            if existing is not None:
                return existing.id
            session.add(section)
            session.commit()
            return section.id

    # --------------------------------------------------------------- السجلات
    def _persist_record(
        self,
        session: Session,
        book: Book,
        section_id: int,
        page_url: str,
        record: RawRecord,
    ) -> str:
        text_original = record.text_original.strip()
        text_search = to_search_text(text_original)
        text_embedding = to_embedding_text(text_original)
        content_hash = sha256_hex(text_original)
        domain = urlsplit(page_url).netloc
        source_record_id = stable_record_key(domain, book.source_url, page_url, record.issue_number)

        issue = session.scalar(select(Issue).where(Issue.source_record_id == source_record_id))
        if issue is None:
            issue = Issue(
                book_id=book.id,
                section_id=section_id,
                scholar_id=book.scholar_id,
                madhhab_id=book.madhhab_id,
                school_id=book.school_id,
                source_record_id=source_record_id,
            )
            session.add(issue)
            result = "created"
        elif issue.content_hash == content_hash:
            return "unchanged"
        else:
            session.add(
                TextVersion(
                    issue_id=issue.id,
                    content_hash=issue.content_hash,
                    text_original=issue.text_original,
                    source_revision=issue.source_revision,
                )
            )
            issue.source_revision += 1
            result = "updated"

        issue.issue_number = record.issue_number
        issue.text_original = text_original
        issue.text_search = text_search
        issue.text_embedding = text_embedding
        issue.source_url = page_url
        issue.content_hash = content_hash
        issue.verified_at = None
        return result

    # ------------------------------------------------------------ حالة التشغيلة
    def _upsert_page_state(
        self, book_id: int, url: str, *, status: str, content_hash: str | None, records_count: int
    ) -> None:
        with Session(self._engine) as session:
            state = session.scalar(
                select(CrawlPageState).where(CrawlPageState.book_id == book_id, CrawlPageState.url == url)
            )
            if state is None:
                state = CrawlPageState(book_id=book_id, url=url)
                session.add(state)
            state.status = status
            state.content_hash = content_hash
            state.records_count = records_count
            state.attempts = (state.attempts or 0) + 1
            state.last_error = None
            session.commit()

    def _record_page_failure(self, book_id: int, url: str, error: str) -> None:
        with Session(self._engine) as session:
            state = session.scalar(
                select(CrawlPageState).where(CrawlPageState.book_id == book_id, CrawlPageState.url == url)
            )
            if state is None:
                state = CrawlPageState(book_id=book_id, url=url)
                session.add(state)
            state.status = "failed"
            state.last_error = error[:2000]
            state.attempts = (state.attempts or 0) + 1
            session.commit()

    def _set_run_book(self, run_id: int, book_id: int) -> None:
        self._update_run(run_id, book_id=book_id)

    def _update_run(self, run_id: int, **fields: object) -> None:
        with Session(self._engine) as session:
            run = session.get(CrawlRun, run_id)
            if run is None:
                return
            for key, value in fields.items():
                setattr(run, key, value)
            session.commit()

    def _fail_run(self, run_id: int, error: str) -> None:
        with Session(self._engine) as session:
            run = session.get(CrawlRun, run_id)
            if run is None:
                return
            run.status = "failed"
            run.error_log = list(run.error_log or []) + [{"error": error[:2000]}]
            session.commit()

    def _finish_run(self, run_id: int, status: str, stats: CrawlStats) -> None:
        with Session(self._engine) as session:
            run = session.get(CrawlRun, run_id)
            if run is None:
                return
            run.status = status
            from shared.db.models import utcnow

            run.finished_at = utcnow()
            run.pages_discovered = stats.pages_discovered
            run.pages_processed = stats.pages_processed
            run.records_created = stats.records_created
            run.records_updated = stats.records_updated
            run.records_unchanged = stats.records_unchanged
            run.records_failed = stats.records_failed
            run.error_log = stats.errors
            session.commit()
