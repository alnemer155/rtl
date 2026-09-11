"""محول موقع مكتب السيد السيستاني (sistani.org).

بنية الموقع المرصودة:
- صفحة الكتاب: <title> يحمل الاسم، والفهرس في <ul class="baz"> وكل مدخل
  رابط /arabic/book/{book}/{section}/ ويشير التسلسل الهرمي بعلامة «» في العنوان.
- صفحة المحتوى: النص في <div class="baz book-text"> والحواشي في
  <div class="baz book-footnote"> والعنوان في <h1 class="c">.
- المسائل تبدأ أسطراً بصيغة «مسألة N:».
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import NavigableString, Tag

from crawler.adapters.base import BookOutline, PageContent, RawRecord, SourceAdapter, TocEntry
from shared.arabic import split_issues

SKIP_TAGS = {"script", "style", "form", "nav", "header", "footer", "button", "select", "input", "noscript"}
BLOCK_TAGS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "blockquote"}

_TOC_LINK_RE = re.compile(r"^/arabic/book/\d+/\d+/?$")
_TITLE_SITE_SUFFIX_RE = re.compile(r"\s+-\s+موقع مكتب.*$")


def html_to_text(node: Tag) -> str:
    """تحويل HTML إلى نص: فواصل الأسطر والكتل تُحفظ، والهياكل غير المحتوائية تُزال.

    لا يُعدَّل النص نفسه: لا حذف تشكيل ولا تغيير حروف — فقط تنظيف الفراغات.
    """
    parts: list[str] = []
    for element in node.descendants:
        if isinstance(element, NavigableString):
            parents = {parent.name for parent in element.parents if isinstance(parent, Tag)}
            if parents & SKIP_TAGS:
                continue
            parts.append(str(element))
        elif isinstance(element, Tag):
            if element.name == "br" or element.name in BLOCK_TAGS:
                parts.append("\n")
    raw = "".join(parts)
    lines = [re.sub(r"[ \t\u00a0\u200e\u200f]+", " ", line.strip()) for line in raw.split("\n")]
    return "\n".join(line for line in lines if line)


def _first_tag(html: str, selector: str) -> Tag | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    found = soup.select_one(selector)
    return found if isinstance(found, Tag) else None


class SistaniAdapter(SourceAdapter):
    source_key = "sistani"
    adapter_name = "SistaniAdapter"
    allowed_domains = {"sistani.org", "www.sistani.org"}
    book_url_pattern = r"^https?://(?:www\.)?sistani\.org/(?:arabic|persian|urdu|english)/book/\d+/?$"

    # ------------------------------------------------------------ صفحة الكتاب
    def parse_book(self, html: str, book_url: str) -> BookOutline:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        title = self._extract_book_title(soup, book_url)
        metadata = self._extract_book_metadata(soup)

        toc: list[TocEntry] = []
        toc_root = soup.select_one("ul.baz")
        if toc_root is not None:
            for anchor in toc_root.select("a[href]"):
                href = anchor.get("href", "")
                if not _TOC_LINK_RE.match(str(href)):
                    continue
                text = anchor.get_text(" ", strip=True)
                if not text:
                    continue
                toc.append(TocEntry(title_full=text, url=urljoin(book_url, str(href))))
        return BookOutline(title=title, toc=toc, metadata=metadata)

    def _extract_book_title(self, soup: Tag, book_url: str) -> str:
        # <title> في صفحات الكتب = «اسم الكتاب - موقع مكتب…»؛ h1 محجوز لترويسة الموقع
        page_title = soup.title.get_text(strip=True) if soup.title else ""
        book_title = _TITLE_SITE_SUFFIX_RE.split(page_title)[0].strip()
        if book_title:
            return book_title
        heading = soup.select_one("div.book-text")
        if heading:
            return heading.get_text(" ", strip=True) or book_url
        return book_url

    def _extract_book_metadata(self, soup: Tag) -> dict:
        metadata: dict = {}
        cover = soup.select_one("div.book-cover")
        if cover and cover.get("style"):
            match = re.search(r"url\((['\"]?)(.*?)\1\)", str(cover["style"]))
            if match:
                metadata["cover_url"] = urljoin("https://www.sistani.org/", match.group(2))
        pdf = soup.select_one('a[href*="book-pdf"]')
        if pdf:
            metadata["pdf_url"] = urljoin("https://www.sistani.org/", str(pdf.get("href", "")))
        return metadata

    # ---------------------------------------------------------- صفحة المحتوى
    def parse_page(self, html: str, page_url: str) -> PageContent:
        soup_and_parts = self._parse_content_document(html)
        title, text, footnote = soup_and_parts
        return PageContent(title=title, text=text, footnote=footnote, metadata={"url": page_url})

    def _parse_content_document(self, html: str) -> tuple[str | None, str, str | None]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        heading = soup.select_one("h1.c") or soup.select_one("h1")
        title = heading.get_text(" ", strip=True) if heading else None
        text = ""
        main = soup.select_one("div.book-text")
        if main is not None:
            text = html_to_text(main)
        footnote = None
        footnote_node = soup.select_one("div.book-footnote")
        if footnote_node is not None:
            footnote_text = html_to_text(footnote_node)
            if footnote_text:
                footnote = footnote_text
        if not text and footnote:
            text, footnote = footnote, None
        return title, text, footnote

    # ----------------------------------------------------------- استخراج السجلات
    def extract_records(self, page: PageContent) -> list[RawRecord]:
        if not page.text.strip():
            return []
        records: list[RawRecord] = []
        for issue_number, segment in split_issues(page.text):
            records.append(RawRecord(issue_number=issue_number, text_original=segment))
        if not records and page.footnote:
            records.append(RawRecord(issue_number=None, text_original=page.footnote))
        return records
