"""واجهة مزوّدي الذكاء الاصطناعي — قابلة لإضافة OpenAI/Anthropic/نماذج محلية لاحقاً."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """خطأ مزود مصنّف — لا تُعرض رسائل Google الخام للمستخدم أبداً."""

    def __init__(self, code: str, provider: str = "gemini", status: int = 0) -> None:
        super().__init__(code)
        self.code = code
        self.provider = provider
        self.status = status


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


def public_provider_error(error: Exception) -> str:
    """تحويل أخطاء المزود إلى رسائل عامة آمنة بالعربية."""
    if isinstance(error, ProviderError):
        if error.code == "length_limit":
            return "وصل الرد إلى حد الطول. يمكنك طلب إكماله."
        if error.code == "blocked":
            return "تعذر تقديم رد على هذا الطلب. جرّب توضيح ما تحتاجه."
        if error.code == "not_configured":
            return "خدمة الأسئلة الذكية غير مهيأة بعد على هذا الخادم."
        if error.status == 429:
            return "الخدمة مشغولة الآن. حاول من جديد بعد قليل."
    return "تعذر إكمال الرد. حاول من جديد."


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def stream_generate(self, system: str, messages: list[ChatMessage]):
        """بثّ نص الرد — async generator of str. يرفع ProviderError عند الفشل."""
