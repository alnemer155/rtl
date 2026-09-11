"""واجهة SourceAdapter العامة — كل مصدر جديد يحصل على Adapter منفصل.

محرك الزحف لا يعرف شيئاً عن تفاصيل المواقع: يستدعي هذه الواجهة فقط.
الإضافة للمصادر تتم بالتسجيل في ADAPTERS دون أي شرط on domain في المحرك.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TocEntry:
    """مدخل في فهرس كتاب: المسار الكامل كما يعرضه المصدر + الرابط."""

    title_full: str  # النص الكامل كما ورد (قد يحتوي فاصل تسلسل مثل «»)
    url: str


@dataclass
class BookOutline:
    """بيانات صفحة الكتاب وفهرسه الكامل."""

    title: str
    toc: list[TocEntry] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PageContent:
    """محتوى صفحة داخلية واحدة بعد استخراجه من HTML الموقع."""

    title: str | None
    text: str
    footnote: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RawRecord:
    """سجل خام قبل التطبيع: مقطع نصي من المصدر مع رقم المسألة إن وُجد."""

    issue_number: int | None
    text_original: str
    metadata: dict = field(default_factory=dict)


class SourceAdapter(ABC):
    """العقد الذي يفي به كل محول موقع."""

    #: مفتاح المصدر في قاعدة البيانات (sources.key)
    source_key: str = ""
    #: اسم المحول المسجل في source_adapters.adapter_name
    adapter_name: str = ""
    #: النطاقات المسموح الزحفها — Allowlist صارم لمنع SSRF
    allowed_domains: set[str] = set()
    #: النمط الذي يحدد روابط صفحات الكتب المقبولة
    book_url_pattern: str = ""

    @abstractmethod
    def parse_book(self, html: str, book_url: str) -> BookOutline:
        """استخراج اسم الكتاب والفهرس الكامل وترتيب الفصول."""

    @abstractmethod
    def parse_page(self, html: str, page_url: str) -> PageContent:
        """استخراج منطقة النص الرئيسية من صفحة داخلية بعد إزالة الهياكل غير المحتوائية."""

    @abstractmethod
    def extract_records(self, page: PageContent) -> list[RawRecord]:
        """تقسيم نص الصفحة إلى سجلات مستقلة (مسألة = سجل)."""

    def normalise_record(self, record: RawRecord) -> RawRecord:
        """تطبيع موحد عام — المحولات تحتاج نادراً تجاوزه."""
        from shared.arabic import extract_issue_number, split_issues

        if record.issue_number is None:
            record.issue_number = extract_issue_number(record.text_original[:120])
        # التطبيع التفصيلي (text_search/embedding) يجري في الـPipeline المشترك
        del split_issues
        return record

    def validate_record(self, record: RawRecord) -> list[str]:
        """تحقق صحة السجل قبل الحفظ."""
        errors: list[str] = []
        if not record.text_original.strip():
            errors.append("empty_text")
        if record.issue_number is not None and record.issue_number < 0:
            errors.append("negative_issue_number")
        if len(record.text_original) > 200_000:
            errors.append("text_too_long")
        return errors
