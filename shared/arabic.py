"""معالجة النص العربي: فواصل بين text_original و text_search و text_embedding.

القاعدة الأساسية: text_original يُحفظ كما ورد من المصدر بأقل تعديل ممكن،
أما text_search وtext_embedding فنسخ مشتقة للبحث فقط ولا تُعرض للمستخدم.
"""

from __future__ import annotations

import re
import unicodedata

# تشكيل: فتح/ضم/كسر/سكون/شدّة/تنوين + ألف خنجرية + علامات قرآنية
_DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed\u08f0-\u08f3]")
_TATWEEL_RE = re.compile(r"\u0640+")
_ARABIC_DIGITS_RE = re.compile(r"[\u0660-\u0669\u06f0-\u06f9]")
_NON_WORD_RE = re.compile(r"[^\w\u0621-\u064a]+", re.UNICODE)
_WS_RE = re.compile(r"\s+")

_DIGIT_TABLE = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

# فواصل علامة المسألة: «مسألة 1063» أو «مسألة ١٠٦٣:» بأي تنويع في الفراغ والرقم.
# مثبتة على بداية السطر حتى لا تُقسم الإحالات الداخلية مثل «في المسألة (415)».
_OPT_DIACRITICS = r"[\u064b-\u065f]*"
ISSUE_MARKER_RE = re.compile(
    rf"^[\s\u200e\u200f]*م{_OPT_DIACRITICS}[سص]{_OPT_DIACRITICS}أ{_OPT_DIACRITICS}"
    rf"[لإ]{_OPT_DIACRITICS}ة\s*[:：\-]?\s*([0-9٠-٩۰-۹]+)\s*[:：\-،,]?",
    re.MULTILINE,
)


def normalise_digits(text: str) -> str:
    """تحويل الأرقام العربية والفارسية إلى أرقام ASCII للمعالجة الداخلية فقط."""
    return text.translate(_DIGIT_TABLE)


def arabic_to_int(text: str) -> int | None:
    """تحويل نص رقم عربي/فارسي/لاتيني إلى int، أو None إن لم يكن رقماً."""
    ascii_digits = normalise_digits(text.strip())
    return int(ascii_digits) if ascii_digits.isascii() and ascii_digits.isdigit() else None


def _unify_letters(text: str) -> str:
    # توحيد صور الألف والهمزات والياء والتاء المربوطة لزيادة الاستدعاء في البحث
    text = re.sub(r"[\u0623\u0625\u0622\u0671]", "\u0627", text)  # أ إ آ ٱ -> ا
    text = text.replace("\u0624", "\u0648")  # ؤ -> و
    text = text.replace("\u0626", "\u064a")  # ئ -> ي
    text = text.replace("\u0649", "\u064a")  # ى -> ي
    text = text.replace("\u0629", "\u0647")  # ة -> ه
    text = text.replace("\u06a9", "\u0643")  # ک فارسية -> ك
    text = text.replace("\u06cc", "\u064a")  # ی فارسية -> ي
    text = text.replace("\u064a", "\u064a")  # ي
    return text


def to_search_text(original: str) -> str:
    """نسخة البحث: تطبيع Unicode وإزالة التشكيل والتطويل وتوحيد الحروف والأرقام.

    لا تُستبدل أبداً بالنسخة الأصلية المعروضة للمستخدم.
    """
    text = unicodedata.normalize("NFC", original)
    text = _DIACRITICS_RE.sub("", text)
    text = _TATWEEL_RE.sub("", text)
    text = normalise_digits(text)
    text = _unify_letters(text)
    text = _NON_WORD_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def to_embedding_text(original: str) -> str:
    """نسخة الـ Embedding: نفس تطبيع البحث مع الحفاظ على حدود الجمل.

    مستقلة عن text_original ولا تُعرض في الواجهة.
    """
    text = unicodedata.normalize("NFC", original)
    text = _DIACRITICS_RE.sub("", text)
    text = _TATWEEL_RE.sub("", text)
    text = normalise_digits(text)
    text = _unify_letters(text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def tokenize_for_query(query: str) -> list[str]:
    """تقطيع استعلام المستخدم إلى حدود مطبّعة للاستخدام في FTS."""
    return [token for token in to_search_text(query).split(" ") if token]


def extract_issue_number(text: str) -> int | None:
    """استخراج رقم المسألة من بداية نص أو سطر، مع تحويل الأرقام داخلياً فقط."""
    match = ISSUE_MARKER_RE.search(text)
    if not match:
        return None
    return arabic_to_int(match.group(1))


def split_issues(original: str) -> list[tuple[int | None, str]]:
    """تقسيم نص الصفحة إلى مسائل مستقلة على علامات «مسألة N».

    النص قبل أول علامة يُعاد كسجل بلا رقم (issue_number=None) حتى لا تُفقد
    أي مادة علمية. النصوص المعادة هي مقاطع حرفية من الأصل دون تعديل.
    """
    matches = list(ISSUE_MARKER_RE.finditer(original))
    if not matches:
        stripped = original.strip()
        return [(None, stripped)] if stripped else []

    records: list[tuple[int | None, str]] = []
    preamble = original[: matches[0].start()].strip()
    if preamble:
        records.append((None, preamble))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(original)
        segment = original[match.start() : end].strip()
        if segment:
            records.append((arabic_to_int(match.group(1)), segment))
    return records
