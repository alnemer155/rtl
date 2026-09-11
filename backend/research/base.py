"""واجهات موحدة لمزودات المصادر الإسلامية وبحث الويب.

كل مزود يعيد ResearchChunk بطبقة Metadata خاصة به دون خلط بينها،
ويستطيع RAG البحث في المصدرين (sistani / turath) والويب من دون تعديل الـChat API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ResearchChunk:
    """قطعة بحثية موحدة من أي مزود — الأساس لبناء استشهادات مرقمة."""

    provider: str  # sistani | turath | web
    title: str
    text: str
    url: str
    detail: str = ""  # سطر ثانوي: الكتاب/الباب/المؤلف/الصفحة
    metadata: dict = field(default_factory=dict)

    def trim(self, max_chars: int) -> ResearchChunk:
        if len(self.text) > max_chars:
            self.text = self.text[:max_chars] + " …"
        return self


class IslamicSourceProvider(ABC):
    """مزود مصدر إسلامي (قاعدة محلية أو API خارجي)."""

    key: str = ""
    name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 6) -> list[ResearchChunk]:
        """بحث نصي يعيد أفضل القطع المطابقة."""


class WebSearchProvider(ABC):
    """مزود بحث ويب — أداة اكتشاف، وليست مصدراً شرعياً بحد ذاته."""

    key: str = "web"
    name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[ResearchChunk]:
        """بحث ويب يعيد نتائج مع روابطها."""
