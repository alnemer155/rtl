"""سجل المحولات — إضافة مصدر جديد تتم هنا دون تعديل محرك الزحف."""

from __future__ import annotations

from crawler.adapters.base import SourceAdapter
from crawler.adapters.sistani import SistaniAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {
    SistaniAdapter.source_key: SistaniAdapter,
    # مستقبلاً: KhameneiAdapter, KhoeiAdapter, DorarAdapter, ShamelaAdapter ...
}


def get_adapter(source_key: str) -> SourceAdapter:
    try:
        return ADAPTERS[source_key]()
    except KeyError as error:
        raise KeyError(f"no adapter registered for source '{source_key}'") from error
