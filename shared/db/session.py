"""إنشاء محرك وجلسات قاعدة البيانات من DATABASE_URL — يدعم SQLite وPostgreSQL.

المحركات تُخزَّن مؤقتاً لكل رابط: إنشاء محرك جديد لكل طلب يعني اتصال
TCP+TLS جديداً في كل مرة (مكلف جداً مع قواعد سحابية مثل Neon).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_ENGINES: dict[str, Engine] = {}


def _load_dotenv() -> None:
    """تحميل متغيرات ملف .env من المجلد الحالي إن وُجد (بلا اعتماديات خارجية)."""
    import os
    from pathlib import Path

    env_file = Path(".env")
    if not env_file.exists() or os.environ.get("MASADIR_SKIP_DOTENV"):
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def default_database_url() -> str:
    _load_dotenv()
    return os.environ.get("DATABASE_URL", "sqlite:///./data/masadir.db")


def normalize_url(url: str) -> str:
    """توحيد رابط قاعدة البيانات لمحرك psycopg3.

    - postgres:// وpostgresql:// يتحولان إلى postgresql+psycopg://
    - channel_binding (الافتراضي في روابط Neon) غير مدعوم في psycopg3 ويُسقط
      — المصادقة SCRAM تستخدم channel binding تلقائياً عبر TLS.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if "channel_binding=" in url:
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query) if key != "channel_binding"]
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return url


def create_db_engine(url: str | None = None) -> Engine:
    url = normalize_url(url or default_database_url())
    cached = _ENGINES.get(url)
    if cached is not None:
        return cached
    if url.startswith("sqlite:///"):
        relative = url[len("sqlite:///") :]
        if not url.startswith("sqlite:////") and relative.startswith("./"):
            db_dir = Path(relative).parent
            db_dir.mkdir(parents=True, exist_ok=True)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30}, pool_pre_ping=True)
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    else:
        # prepare_threshold=0 يلغي العبارات المحضّرة — الأنسب للـPoolers مثل Neon
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"prepare_threshold": 0},
        )
    _ENGINES[url] = engine
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def session_scope(engine: Engine) -> Iterator[Session]:
    """سياق جلسة يضمن الالتزام أو التراجع."""
    session = make_session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
