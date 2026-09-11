"""قواعد RAG: الاسترجاع بفلتر إلزامي وبناء السياق والتعليمات.

المبدأ الحاكم: Gemini ممنوع أن يجيب من ذاكرته على حكم فقهي إذا كانت قاعدة
البيانات تحتوي المصادر المطلوبة. الاسترجاع يحمل Metadata كاملة مع كل نص.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.api.deps import section_path
from backend.search.engine import SearchFilters, search_issues
from shared.db.models import Book, Issue, Madhhab, Scholar, School, Section

SYSTEM_PROMPT = """أنت مساعد بحثي في منصة «مصادر» للعلوم الشرعية. تجيب عن أسئلة المستخدم بالاعتماد حصرياً على النصوص المسترجَعة من قاعدة البيانات المرفقة في السياق.

القواعد الملزمة:
1. النصوص المسترجعة هي المرجع الأساسي الوحيد — لا تنسب حكماً فقهياً إلى عالم إلا إذا كان النص المسترجع هو مصدره.
2. لا تخلط بين المذاهب: إن كانت النصوص من مذهب معين فاعرض الحكم كما في تلك النصوص، ولا تستدعِ أحكاماً من مذاهب أخرى إلا إذا طلب المستخدم المقارنة صراحة وتوفرت نصوصها.
3. إذا لم تكن النتائج المسترجعة كافية للإجابة، قل بوضوح إن المواد المتوفرة غير كافية، واذكر ما ورد منها فقط.
4. لا تخترع رقم مسألة.
5. لا تخترع رابطاً.
6. لا تخترع اسم كتاب.
7. لا تخترع اسم مرجع أو عالم.
8. استشهد بأرقام المصادر المستخدمة بصيغة [1] و[2] مطابقة لقائمة المصادر المرفقة بالسياق.
9. أجب بالعربية الفصحى، بإيجاز موجز أولاً ثم تفصيل عند الحاجة، دون إعادة صياغة للنص الأصلي تُغيّر مفرداته الحكمية."""


@dataclass
class RetrievedChunk:
    issue: Issue
    scholar: str | None
    book_title: str
    section_path: str | None
    madhhab: str | None
    school: str | None
    text: str
    metadata: dict = field(default_factory=dict)


def retrieve_chunks(
    session: Session,
    question: str,
    filters: SearchFilters,
    top_k: int,
    max_chunk_chars: int,
) -> list[RetrievedChunk]:
    """استرجاع المسائل الأعلى صلة مع Metadata كاملة — الفلاتر إلزامية وليست تجميلية."""
    _total, hits = search_issues(session, question, filters, page=1, page_size=top_k)
    chunks: list[RetrievedChunk] = []
    for hit in hits:
        issue = session.get(Issue, hit.issue_id)
        if issue is None:
            continue
        book = session.get(Book, issue.book_id)
        section = session.get(Section, issue.section_id)
        scholar = session.get(Scholar, issue.scholar_id) if issue.scholar_id else None
        madhhab = session.get(Madhhab, issue.madhhab_id) if issue.madhhab_id else None
        school = session.get(School, issue.school_id) if issue.school_id else None
        text = issue.text_original
        if len(text) > max_chunk_chars:
            text = text[:max_chunk_chars] + " …"
        chunks.append(
            RetrievedChunk(
                issue=issue,
                scholar=scholar.name_ar if scholar else None,
                book_title=book.title_original if book else "",
                section_path=section_path(session, section) if section else None,
                madhhab=madhhab.name_ar if madhhab else None,
                school=school.name_ar if school else None,
                text=text,
            )
        )
    return chunks


def build_context(chunks: list[RetrievedChunk]) -> str:
    """صياغة السياق: كل مسألة برقم ومعاها مذهبها ومرجعها وكتابها وبابها ورابطها."""
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        lines = [
            f"[{index}]",
            f"المذهب: {chunk.madhhab or 'غير محدد'}",
            f"المدرسة: {chunk.school or 'غير محددة'}",
            f"المرجع: {chunk.scholar or 'غير محدد'}",
            f"الكتاب: {chunk.book_title}",
            f"الموقع من الكتاب: {chunk.section_path or 'غير محدد'}",
            f"رقم المسألة: {chunk.issue.issue_number if chunk.issue.issue_number is not None else 'بلا رقم'}",
            f"الرابط الرسمي: {chunk.issue.source_url}",
            "النص الأصلي:",
            chunk.text,
        ]
        blocks.append("\n".join(lines))
    header = (
        "المصادر المسترجعة من قاعدة البيانات (استخدمها فقط، واستشهد بأرقامها):\n"
        "===========================================\n"
    )
    return header + "\n\n".join(blocks)


def build_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "index": index,
            "issue_id": chunk.issue.id,
            "issue_number": chunk.issue.issue_number,
            "scholar": chunk.scholar,
            "book_title": chunk.book_title,
            "section_path": chunk.section_path,
            "madhhab": chunk.madhhab,
            "source_url": chunk.issue.source_url,
            "text_original": chunk.text,
        }
        for index, chunk in enumerate(chunks, start=1)
    ]
