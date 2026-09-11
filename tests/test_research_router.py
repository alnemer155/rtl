"""اختبارات Research Router: قرارات التوجيه الصريحة."""

from backend.research.router import route_message


def test_greeting_needs_no_search():
    decision = route_message("السلام عليكم")
    assert decision.islamic is False
    assert decision.web is False


def test_sistani_mention_restricts_to_sistani():
    decision = route_message("ما حكم صيام يوم عرفة عند السيد السيستاني؟")
    assert decision.islamic is True
    assert decision.providers == ["sistani"]
    assert decision.madhhab_filter == "shia"


def test_shia_mention_routes_to_shia_source():
    decision = route_message("ما حكم كذا عند الشيعة؟")
    assert decision.islamic is True
    assert "sistani" in decision.providers


def test_sunni_book_routes_to_turath():
    decision = route_message("ابحث في صحيح البخاري عن بر الوالدين")
    assert decision.islamic is True
    assert decision.providers == ["turath"]


def test_shia_and_sunni_together_compare_both():
    decision = route_message("ما رأي الشيعة والسنة في المتعة؟")
    assert decision.islamic is True
    assert "sistani" in decision.providers
    assert "turath" in decision.providers


def test_explicit_compare_word():
    decision = route_message("قارن بين أقوال الفقهاء في المسألة")
    assert decision.islamic is True
    assert "sistani" in decision.providers and "turath" in decision.providers


def test_news_goes_to_web():
    decision = route_message("ما آخر أخبار الطقس؟")
    assert decision.web is True


def test_general_question_uses_web():
    decision = route_message("اشرح لي كيف يعمل الذكاء الاصطناعي في السيارات")
    assert decision.web is True


def test_generic_religious_question_searches_both():
    decision = route_message("ما حكم الشك في الصلاة؟")
    assert decision.islamic is True
    assert "sistani" in decision.providers and "turath" in decision.providers
