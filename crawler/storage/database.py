"""طبقة التخزين المشتركة للزاحف: تهيئة المخطط والبيانات المرجعية الحقيقية."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from shared.db import fts
from shared.db.models import Base, Madhhab, Scholar, School, Source, SourceAdapter

logger = logging.getLogger("[crawler.database]")


def ensure_schema(engine: Engine) -> None:
    """إنشاء المخطط والفهارس — للترحيلات الرسمية يُستخدم Alembic، وهذه للبيئات الاختبارية."""
    Base.metadata.create_all(engine)
    fts.ensure_fts(engine)


# ---------------------------------------------------------------------------
# بيانات مرجعية حقيقية فقط (معلومات عامة موثقة، لا محتوى منسوخ)
# ---------------------------------------------------------------------------

REFERENCE_MADHHABS: list[dict[str, object]] = [
    {
        "key": "sunni",
        "name_ar": "أهل السنة",
        "name_en": "Sunni",
        "schools": [
            {"key": "hanafi", "name_ar": "الحنفي", "name_en": "Hanafi"},
            {"key": "maliki", "name_ar": "المالكي", "name_en": "Maliki"},
            {"key": "shafii", "name_ar": "الشافعي", "name_en": "Shafi'i"},
            {"key": "hanbali", "name_ar": "الحنبلي", "name_en": "Hanbali"},
        ],
    },
    {
        "key": "shia",
        "name_ar": "الشيعة",
        "name_en": "Shia",
        "schools": [
            {"key": "jaafari", "name_ar": "الجعفري / الإثنا عشري", "name_en": "Jaafari / Twelver"},
            {"key": "zaidi", "name_ar": "الزيدي", "name_en": "Zaidi"},
            {"key": "ismaili", "name_ar": "الإسماعيلي", "name_en": "Ismaili"},
        ],
    },
]


def seed_reference_data(session: Session) -> None:
    """تهيئة المذاهب والمدارس — بيانات تصنيفية عامة لا تحتاج مصادر خارجية."""
    for madhhab_data in REFERENCE_MADHHABS:
        madhhab_key = str(madhhab_data["key"])
        madhhab = session.scalar(select(Madhhab).where(Madhhab.key == madhhab_key))
        if madhhab is None:
            madhhab = Madhhab(
                key=madhhab_data["key"], name_ar=madhhab_data["name_ar"], name_en=madhhab_data["name_en"]
            )
            session.add(madhhab)
            session.flush()
        schools = madhhab_data.get("schools", [])
        assert isinstance(schools, list)
        for school_data in schools:
            assert isinstance(school_data, dict)
            school = session.scalar(select(School).where(School.key == str(school_data["key"])))
            if school is None:
                session.add(
                    School(
                        madhhab_id=madhhab.id,
                        key=str(school_data["key"]),
                        name_ar=str(school_data["name_ar"]),
                        name_en=str(school_data["name_en"]),
                    )
                )
    session.commit()


def upsert_source(
    session: Session,
    *,
    key: str,
    domain: str,
    base_url: str,
    name: str | None = None,
    source_type: str = "website",
    language: str = "ar",
    madhhab_key: str | None = None,
    school_key: str | None = None,
    adapter_name: str | None = None,
    adapter_config: dict | None = None,
) -> Source:
    """تسجيل مصدر ومحوله — مرجعية إضافته لمصادر جديدة مستقبلاً.

    الاسم وبيانات الانتماء لا تُكتب فوق قيم موجودة إلا إذا مُررت صراحة.
    """
    source = session.scalar(select(Source).where(Source.key == key))
    madhhab_id = school_id = None
    if madhhab_key:
        madhhab_id = session.scalar(select(Madhhab.id).where(Madhhab.key == madhhab_key))
    if school_key:
        school_id = session.scalar(select(School.id).where(School.key == school_key))
    if source is None:
        source = Source(key=key, name=name or key, domain=domain, base_url=base_url)
        session.add(source)
    if name:
        source.name = name
    source.domain = domain
    source.base_url = base_url
    if source_type:
        source.source_type = source_type
    if language:
        source.language = language
    if madhhab_id:
        source.madhhab_id = madhhab_id
    if school_id:
        source.school_id = school_id
    session.flush()
    if adapter_name:
        adapter = session.scalar(select(SourceAdapter).where(SourceAdapter.source_id == source.id))
        if adapter is None:
            adapter = SourceAdapter(source_id=source.id, adapter_name=adapter_name)
            session.add(adapter)
        adapter.adapter_name = adapter_name
        adapter.config = adapter_config or {}
    session.commit()
    logger.info("[source] upserted key=%s domain=%s", key, domain)
    return source


def upsert_scholar(
    session: Session,
    *,
    key: str,
    name_ar: str,
    name_en: str | None = None,
    madhhab_key: str | None = None,
    school_key: str | None = None,
    source_key: str | None = None,
    metadata_json: dict | None = None,
) -> Scholar:
    scholar = session.scalar(select(Scholar).where(Scholar.key == key))
    madhhab_id = session.scalar(select(Madhhab.id).where(Madhhab.key == madhhab_key)) if madhhab_key else None
    school_id = session.scalar(select(School.id).where(School.key == school_key)) if school_key else None
    source_id = session.scalar(select(Source.id).where(Source.key == source_key)) if source_key else None
    if scholar is None:
        scholar = Scholar(key=key, name_ar=name_ar)
        session.add(scholar)
    scholar.name_ar = name_ar
    scholar.name_en = name_en
    scholar.madhhab_id = madhhab_id
    scholar.school_id = school_id
    scholar.source_id = source_id
    scholar.metadata_json = metadata_json or {}
    session.commit()
    return scholar
