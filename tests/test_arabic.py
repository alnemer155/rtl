"""اختبارات معالجة النص العربي والتطبيع واستخراج المسائل."""

from shared.arabic import (
    arabic_to_int,
    extract_issue_number,
    normalise_digits,
    split_issues,
    to_embedding_text,
    to_search_text,
)


def test_normalise_digits_arabic_indic():
    assert normalise_digits("مسألة ١٠٦٣") == "مسألة 1063"


def test_normalise_digits_persian():
    assert normalise_digits("مسأله ۴۵۶") == "مسأله 456"


def test_arabic_to_int_mixed():
    assert arabic_to_int("۱۰۶۳") == 1063
    assert arabic_to_int("42") == 42
    assert arabic_to_int("لا رقم") is None


def test_to_search_text_removes_diacritics_and_tatweel():
    original = "الـمَـاءُ الْمُطْلَقُ"
    result = to_search_text(original)
    assert "ماء" in result or "الماء" in result
    for diacritic in "ًٌٍَُِّْ":
        assert diacritic not in result
    assert "\u0640" not in result  # تطويل


def test_to_search_text_unifies_alef_and_taa():
    assert to_search_text("أحمد إبراهيم آل") == "احمد ابراهيم ال"
    assert to_search_text("مَدرسةٌ كبيرة") == "مدرسه كبيره"


def test_to_search_text_unifies_persian_letters():
    assert "ك" in to_search_text("ماء کثير")  # ک الفارسية -> ك
    assert "ي" in to_search_text("یوم")  # ی الفارسية -> ي


def test_to_search_text_normalises_punctuation_and_spaces():
    result = to_search_text("كتاب  الصوم،   والصلاة.")
    assert result == "كتاب الصوم والصلاه"


def test_text_original_is_never_modified():
    original = "الْمَاءُ الْمُطْلَقُ إمَّا ١٢٣"
    assert to_search_text(original) != original  # نسخة البحث مختلفة
    assert original == "الْمَاءُ الْمُطْلَقُ إمَّا ١٢٣"  # والأصل كما هو


def test_to_embedding_text_keeps_content():
    result = to_embedding_text("مسألة ٣٣: إذا كانت النجاسة")
    assert "33" in result
    assert "مساله" in result


def test_extract_issue_number_plain():
    assert extract_issue_number("مسألة 1063: إلى ...") == 1063


def test_extract_issue_number_arabic_digits():
    assert extract_issue_number("مسألة ١٠٦٣: إلى ...") == 1063


def test_extract_issue_number_persian_digits():
    assert extract_issue_number("مسألة ۱۰۶۳: إلى ...") == 1063


def test_extract_issue_number_none_for_references():
    # الإحالة داخل النص ليست علامة مسألة
    assert extract_issue_number("كما يأتي في المسألة (415)") is None


def test_split_issues_three_records():
    text = "مسألة 100\nالنص الأول\nمسألة 101\nالنص الثاني\nمسألة 102\nالنص الثالث"
    records = split_issues(text)
    numbers = [number for number, _ in records]
    assert numbers == [100, 101, 102]
    assert len(records) == 3


def test_split_issues_keeps_preamble_as_unnumbered_record():
    text = "مقدمة الصفحة بلا رقم\nمسألة 33: نص المسألة"
    records = split_issues(text)
    assert records[0][0] is None
    assert "مقدمة الصفحة" in records[0][1]
    assert records[1][0] == 33


def test_split_issues_unnumbered_page():
    text = "نص مهم بلا رقم مسألة"
    records = split_issues(text)
    assert len(records) == 1
    assert records[0][0] is None


def test_split_issues_preserves_original_text_verbatim():
    text = "مسألة ١٥: النصُّ بالتشكيل والأرقام ١٥ كما هي"
    records = split_issues(text)
    number, segment = records[0]
    assert number == 15
    assert "١٥" in segment  # الأرقام الأصلية لا تُغيَّر في النص المعروض
