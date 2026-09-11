"""Research Router: يقرر مسار البحث لكل رسالة قبل استدعاء المزودات.

No Search / Islamic Sources / Web Search / Islamic + Web
قواعد صريحة قابلة للاختبار — لا LLM في التوجيه.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SISTANI_PATTERNS = [r"السيستاني", r"سيستاني", r"sistani", r"المرجع\s+السيد", r"الجعفري"]
_SHIA_PATTERNS = [r"الشيعة", r"شيعي", r"الجعفري", r"الإمامية", r"الاثنا\s*عشري"]
_SUNNI_PATTERNS = [
    r"السنة\s+والجماعة", r"أهل\s+السنة", r"اهل\s+السنه", r"سني",
    r"البخاري", r"صحيح\s+مسلم", r"سنن\s+أبي\s+داود", r"الترمذي",
    r"الحنفي", r"الشافعي", r"المالكي", r"الحنبلي", r"الشافعي",
    r"turath", r"التراث", r"شاملة", r"shamela",
]
_COMPARE_PATTERNS = [r"قارن\s+بين", r"قارن", r"مقارنة", r"الفرق\s+بين", r"الاختلاف\s+بين", r"أقوال\s+العلماء", r"اقوال\s+العلماء"]
_WEB_PATTERNS = [
    r"أخبار", r"اخبار", r"خبر\s+جديد", r"آخر\s+خبر", r"آخر\s+أخبار",
    r"بيان\s+جديد", r"تصريح\s+جديد", r"سعر", r"طقس", r"على\s+الإنترنت",
    r"على\s+الانترنت", r"في\s+الويب", r"ابحث\s+على\s+النت",
]
_RELIGIOUS_PATTERNS = [
    r"ما\s+حكم", r"حكم\s+", r"هل\s+يجوز", r"هل\s+يصح", r"هل\s+يجب",
    r"فتوى", r"فتوي", r"مسألة", r"مساله", r"يجب", r"يستحب", r"يكره", r"حرام", r"حلال",
    r"صيام", r"الصلاة", r"صلاة", r"الزكاة", r"زكاة", r"الحج", r"الطهارة", r"النكاح", r"الطلاق",
    r"حديث", r"الأحاديث", r"دعاء", r"رواه", r"سند", r"إسناد",
]
_SMALLTALK_PATTERNS = [
    r"^(السلام\s+عليكم|سلام\s+عليكم|سلام|مرحبا|مرحبتين|هلا|أهلا|اهلا|هاي|hi|hello|شكرا|شكراً|كيف\s+حالك|كيفك)\b",
]


@dataclass
class RouteDecision:
    islamic: bool = False
    web: bool = False
    providers: list[str] = field(default_factory=list)  # ["sistani"], ["turath"] أو كلاهما
    madhhab_filter: str | None = None
    reason: str = "general"


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def route_message(message: str) -> RouteDecision:
    """قرار التوجيه لرسالة المستخدم — قواعد صريحة سريعة وقابلة للاختبار."""
    text = message.strip()
    lowered = text.lower()

    # تحية أو محادثة اجتماعية قصيرة: لا بحث
    if len(text) <= 30 and _matches_any(text, _SMALLTALK_PATTERNS):
        return RouteDecision(reason="smalltalk")

    mentions_sistani = _matches_any(lowered, _SISTANI_PATTERNS)
    mentions_shia = _matches_any(lowered, _SHIA_PATTERNS)
    mentions_sunni = _matches_any(lowered, _SUNNI_PATTERNS)
    wants_compare = _matches_any(lowered, _COMPARE_PATTERNS)
    wants_web = _matches_any(lowered, _WEB_PATTERNS)
    is_religious = _matches_any(lowered, _RELIGIOUS_PATTERNS)

    providers: list[str] = []
    madhhab_filter: str | None = None

    if mentions_sistani and not wants_compare:
        providers.append("sistani")
        madhhab_filter = "shia"
    if mentions_sunni or mentions_shia and not mentions_sistani:
        if "turath" not in providers:
            providers.append("turath")
        if mentions_shia:
            madhhab_filter = "shia"
    # ذكر الشيعة وحده يستدعي مصدرها الرسمي أيضاً
    if mentions_shia and "sistani" not in providers:
        providers.insert(0, "sistani")
        madhhab_filter = madhhab_filter or "shia"
    if wants_compare or (is_religious and not providers):
        for provider in ("sistani", "turath"):
            if provider not in providers:
                providers.append(provider)
    if mentions_sistani and wants_compare and "turath" not in providers:
        providers.append("turath")

    islamic = bool(providers)

    # سؤال ديني عام دون تحديد مدرسة: المصادر المحلية أولاً (البيانات المتاحة)
    if not islamic and is_religious:
        providers = ["sistani", "turath"]
        islamic = True

    if wants_web:
        web = True
    elif not islamic and not is_religious:
        # سؤال عام غير ديني: بحث ويب يوفر سياقاً محدثاً
        web = len(text) > 12
    else:
        web = False

    reason = "explicit"
    if not islamic and not web:
        reason = "smalltalk" if len(text) <= 40 else "general"
    return RouteDecision(
        islamic=islamic,
        web=web,
        providers=providers,
        madhhab_filter=madhhab_filter,
        reason=reason,
    )
