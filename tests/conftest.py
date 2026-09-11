"""تهيئة مشتركة للاختبارات: قاعدة SQLite مؤقتة ببيانات مرجعية حقيقية."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from crawler.storage.database import ensure_schema, seed_reference_data, upsert_scholar, upsert_source
from shared.db.session import create_db_engine


@pytest.fixture()
def engine(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path.as_posix()}/test-masadir.db")
    ensure_schema(engine)
    return engine


@pytest.fixture()
def seeded_session(engine):
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    seed_reference_data(session)
    upsert_source(
        session,
        key="sistani",
        name="موقع مكتب سماحة المرجع الديني الأعلى السيد علي الحسيني السيستاني",
        domain="sistani.org",
        base_url="https://www.sistani.org/",
        madhhab_key="shia",
        school_key="jaafari",
        adapter_name="SistaniAdapter",
    )
    upsert_scholar(
        session,
        key="sistani",
        name_ar="السيد علي الحسيني السيستاني",
        madhhab_key="shia",
        school_key="jaafari",
        source_key="sistani",
    )
    yield session
    session.close()


@pytest.fixture()
def seeded_engine(seeded_session: Session):
    yield seeded_session.get_bind()
