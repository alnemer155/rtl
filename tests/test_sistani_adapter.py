"""اختبارات محول السيستاني على HTML حقيقية محفوظة (بلا اتصال بالشبكة)."""

from pathlib import Path

from crawler.adapters.registry import get_adapter

FIXTURES = Path(__file__).parent / "fixtures" / "sistani"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_book_extracts_title_and_toc():
    adapter = get_adapter("sistani")
    outline = adapter.parse_book(load("book-23720.html"), "https://www.sistani.org/arabic/book/23720/")
    assert "منهاج الصالحين" in outline.title
    assert len(outline.toc) == 232
    assert outline.toc[0].url.endswith("/arabic/book/23720/3599/")
    assert outline.metadata.get("pdf_url")


def test_parse_book_toc_titles_contain_hierarchy_separator():
    adapter = get_adapter("sistani")
    outline = adapter.parse_book(load("book-23720.html"), "https://www.sistani.org/arabic/book/23720/")
    assert any("»" in entry.title_full for entry in outline.toc)


def test_parse_page_extracts_main_text_without_navigation():
    adapter = get_adapter("sistani")
    page = adapter.parse_page(load("section-3605.html"), "https://www.sistani.org/arabic/book/23720/3605/")
    assert page.title is not None and "الطهارة" in page.title
    # النص يحتوي مسألة 33 الموجودة في الصفحة الأصلية
    assert "مسألة 33" in page.text
    # لا يجب أن يتسرب هيدر/فوتر الموقع إلى النص
    assert "الأرشيف" not in page.text
    assert "jQuery" not in page.text


def test_extract_records_splits_page_into_issues():
    adapter = get_adapter("sistani")
    page = adapter.parse_page(load("section-3605.html"), "https://www.sistani.org/arabic/book/23720/3605/")
    records = adapter.extract_records(page)
    numbers = [record.issue_number for record in records]
    # تمهيد بلا رقم ثم مسائل متتالية 33..52
    assert numbers[0] is None
    assert 33 in numbers and 52 in numbers
    assert numbers.count(None) == 1
    # النص الأصلي محفوظ حرفياً
    issue_33 = next(record for record in records if record.issue_number == 33)
    assert issue_33.text_original.startswith("مسألة 33:")


def test_extract_records_outline_page_without_issues_is_empty_but_safe():
    """صفحة 3896 بلا منطقة نص رئيسية — يجب ألا تنهار ولا تنتج سجلات وهمية."""
    adapter = get_adapter("sistani")
    page = adapter.parse_page(load("section-fasting.html"), "https://www.sistani.org/arabic/book/23720/3896/")
    records = adapter.extract_records(page)
    assert records == []


def test_validate_record_flags_empty_text():
    adapter = get_adapter("sistani")
    from crawler.adapters.base import RawRecord

    assert "empty_text" in adapter.validate_record(RawRecord(issue_number=None, text_original="  "))
    assert adapter.validate_record(RawRecord(issue_number=5, text_original="نص صالح")) == []


def test_adapter_registry_rejects_unknown_source():
    import pytest

    with pytest.raises(KeyError):
        get_adapter("unknown_source")
