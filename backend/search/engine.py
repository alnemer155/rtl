"""محرك البحث العربي: FTS5 لـ SQLite وtsvector لـ PostgreSQL مع فلاتر صارمة.

قواعد حاكمة:
- الفلاتر جزء من الاستعلام نفسه — اختيار المستخدم مذهباً معيناً لا يُخرج أي
  نتائج من مذهب آخر مهما كانت نقاط التطابق.
- منطق AND أولاً للصلة العالية، وإن لم يُطابق شيء نوسّع إلى OR تلقائياً
  (صيغ مثل «صيام/صوم» لا تحمل جذراً مشتركاً نصياً).
- المطابقة الحرفية للعبارة تتصدر النتائج.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.arabic import tokenize_for_query
from shared.db.models import Issue


@dataclass
class SearchFilters:
    madhhab: str | None = None
    school: str | None = None
    scholar: str | None = None
    book: int | None = None
    section: int | None = None
    issue_number: int | None = None
    source: str | None = None


@dataclass
class SearchHit:
    issue_id: int
    rank: float
    snippet: str
    sort_key: tuple = field(default_factory=tuple)


def build_fts_query(query: str, operator: str = "AND") -> str:
    """بناء استعلام FTS: كل حدّ مُقتبس مع بحث بادئة، مربوطة بعامل AND أو OR."""
    tokens = tokenize_for_query(query)
    if not tokens:
        return ""
    return f" {operator} ".join(f'"{token.replace(chr(34), "")}"*' for token in tokens)


def build_pg_query(query: str, operator: str = "&") -> str:
    """بناء استعلام tsquery مع بادئات لمسار PostgreSQL."""
    tokens = tokenize_for_query(query)
    return f" {operator} ".join(f"{token}:*" for token in tokens)


_JOIN = """
FROM issues_fts f
JOIN issues i ON i.id = f.rowid
JOIN books b ON b.id = i.book_id
JOIN sources src ON src.id = b.source_id
JOIN sections s ON s.id = i.section_id
LEFT JOIN scholars sc ON sc.id = i.scholar_id
LEFT JOIN madhhabs m ON m.id = i.madhhab_id
LEFT JOIN schools sch ON sch.id = i.school_id
"""

# مسار PostgreSQL لا يحتوي جدول FTS5 — يبدأ من issues مباشرة
_JOIN_PG = """
FROM issues i
JOIN books b ON b.id = i.book_id
JOIN sources src ON src.id = b.source_id
JOIN sections s ON s.id = i.section_id
LEFT JOIN scholars sc ON sc.id = i.scholar_id
LEFT JOIN madhhabs m ON m.id = i.madhhab_id
LEFT JOIN schools sch ON sch.id = i.school_id
"""


def _filter_clauses(filters: SearchFilters, params: dict) -> list[str]:
    clauses: list[str] = []
    if filters.madhhab:
        clauses.append("m.key = :madhhab")
        params["madhhab"] = filters.madhhab
    if filters.school:
        clauses.append("sch.key = :school")
        params["school"] = filters.school
    if filters.scholar:
        clauses.append("sc.key = :scholar")
        params["scholar"] = filters.scholar
    if filters.book is not None:
        clauses.append("b.id = :book")
        params["book"] = filters.book
    if filters.section is not None:
        clauses.append("s.id = :section")
        params["section"] = filters.section
    if filters.issue_number is not None:
        clauses.append("i.issue_number = :issue_number")
        params["issue_number"] = filters.issue_number
    if filters.source:
        clauses.append("src.key = :source")
        params["source"] = filters.source
    return clauses


def _sql(statement: str):
    from sqlalchemy import text as sql_text

    return sql_text(statement)


def _sqlite_run(
    session: Session,
    params: dict,
    filters: SearchFilters,
    offset: int,
    limit: int,
    has_match: bool,
) -> tuple[int, list[SearchHit]]:
    """تنفيذ استعلام SQLite FTS بمعاملات جاهزة، أو تصفح بلا نص عند has_match=False."""
    filter_params: dict = dict(params)
    clauses = _filter_clauses(filters, filter_params)
    where_sql = ("WHERE issues_fts MATCH :fts_query " if has_match else "WHERE 1=1 ") + (
        ("AND " + " AND ".join(clauses)) if clauses else ""
    )
    rows = session.execute(
        _sql(
            f"""
            SELECT i.id AS issue_id,
                   bm25(issues_fts, 8.0, 3.0) AS rank,
                   snippet(issues_fts, 0, '<mark>', '</mark>', '…', 18) AS snip
            {_JOIN}
            {where_sql}
            ORDER BY rank
            LIMIT :fetch OFFSET 0
            """
        ),
        {**filter_params, "fetch": limit},
    ).all()
    total = session.execute(_sql(f"SELECT COUNT(*) {_JOIN} {where_sql}"), filter_params).scalar_one()
    hits = [SearchHit(issue_id=row.issue_id, rank=float(row.rank), snippet=row.snip or "") for row in rows]
    return total, hits[offset : offset + limit]


def search_issues(
    session: Session,
    query: str,
    filters: SearchFilters,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, list[SearchHit]]:
    """بحث نصي مع فلاتر؛ يعيد (الإجمالي، النتائج) مرتبة بالصلة مع دفعة المطابقة الحرفية."""
    offset = max(0, (page - 1) * page_size)
    tokens = tokenize_for_query(query) if query.strip() else []
    fetch = page_size * 5 + 50

    if session.get_bind().dialect.name == "postgresql":
        return _search_postgres(session, query, filters, tokens, offset, page_size)

    if tokens:
        params = {"fts_query": build_fts_query(query, "AND")}
        total, hits = _sqlite_run(session, params, filters, offset, fetch, has_match=True)
        if total == 0 and len(tokens) > 1:
            params = {"fts_query": build_fts_query(query, "OR")}
            total, hits = _sqlite_run(session, params, filters, offset, fetch, has_match=True)
    else:
        total, hits = _sqlite_run(session, {}, filters, offset, fetch, has_match=False)

    if tokens:
        _boost_exact_matches(session, hits, " ".join(tokens))
        hits.sort(key=lambda item: item.sort_key)
    return total, hits[offset : offset + page_size]


def _boost_exact_matches(session: Session, hits: list[SearchHit], normalised_query: str) -> None:
    """المطابقة الحرفية للعبارة المطبّعة تأخذ الأولوية على درجة الصلة."""
    if not hits or not normalised_query:
        for hit in hits:
            hit.sort_key = (1, hit.rank)
        return
    ids = [hit.issue_id for hit in hits]
    rows = session.execute(select(Issue.id, Issue.text_search).where(Issue.id.in_(ids))).all()
    texts: dict[int, str] = {row[0]: row[1] for row in rows}
    for hit in hits:
        exact = 0 if normalised_query in (texts.get(hit.issue_id) or "") else 1
        hit.sort_key = (exact, hit.rank)


def _search_postgres(
    session: Session,
    query: str,
    filters: SearchFilters,
    tokens: list[str],
    offset: int,
    limit: int,
) -> tuple[int, list[SearchHit]]:
    """مسار PostgreSQL: tsvector بإعداد simple مع بادئات وts_headline للمقتطفات."""
    filter_params: dict = {}
    clauses = _filter_clauses(filters, filter_params)
    filter_where = ("AND " + " AND ".join(clauses)) if clauses else ""

    def run(operator: str) -> tuple[int, list[SearchHit]]:
        """نافذة مرشحين ثابتة (كما في مسار SQLite) — ترقيم صفحات متسق مع إعادة الترتيب."""
        if not tokens:
            where_sql = "WHERE 1=1 " + filter_where
            params: dict = dict(filter_params)
            rank_expr = "0.0"
            headline = "''"
        else:
            where_sql = "WHERE to_tsvector('simple', i.text_search) @@ to_tsquery('simple', :ts_query) " + filter_where
            params = {**filter_params, "ts_query": build_pg_query(query, operator)}
            rank_expr = "ts_rank(to_tsvector('simple', i.text_search), to_tsquery('simple', :ts_query))"
            headline = (
                "ts_headline('simple', i.text_search, to_tsquery('simple', :ts_query), "
                "'StartSel=<mark>,StopSel=</mark>,MaxFragments=1')"
            )
        rows = session.execute(
            _sql(
                f"""
                SELECT i.id AS issue_id, {rank_expr} AS rank, {headline} AS snip
                {_JOIN_PG}
                {where_sql}
                ORDER BY rank DESC
                LIMIT :fetch OFFSET 0
                """
            ),
            {**params, "fetch": max(limit * 5 + 50, offset + limit)},
        ).all()
        total = session.execute(_sql(f"SELECT COUNT(*) {_JOIN_PG} {where_sql}"), params).scalar_one()
        hits = [SearchHit(issue_id=row.issue_id, rank=float(row.rank), snippet=row.snip or "") for row in rows]
        return total, hits

    if tokens:
        total, hits = run("&")
        if total == 0 and len(tokens) > 1:
            total, hits = run("|")
        # توحيد السلوك مع مسار SQLite: المطابقة الحرفية تتصدر النتائج
        _boost_exact_matches(session, hits, " ".join(tokens))
        hits.sort(key=lambda item: item.sort_key)
        return total, hits[offset : offset + limit]
    return run("&")
