"""التجزئة ووقف التكرار: SHA-256 لكل سجل ومعرّف مستقر لكل مصدر نصي."""

from __future__ import annotations

import hashlib


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_record_key(*parts: object) -> str:
    """معرّف مستقر للسجل ضمن المنصة: تجزئة أول 32 محرفاً من SHA-256 للمكوّنات.

    المكوّنات النموذجية: نطاق المصدر، رابط الكتاب، رابط القسم، رقم المسألة.
    يُستخدم لكشف التكرار عند إعادة الزحف دون الاعتماد على أعمدة auto-increment.
    """
    joined = "|".join(str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]
