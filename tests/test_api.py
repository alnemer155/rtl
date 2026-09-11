"""اختبارات نقاط نهاية الـAPI على قاعدة اختبار حقيقية."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import backend.api.deps as deps
from backend.main import create_app
from tests.test_search import _seed_two_madhhab_issues


def _client(engine):
    app = create_app()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    return TestClient(app)


def test_health(seeded_engine):
    client = _client(seeded_engine)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "issues_count" in data
    assert "ai_configured" in data


def test_madhhabs_sources_scholars(seeded_session):
    engine = seeded_session.get_bind()
    client = _client(engine)
    madhhabs = client.get("/api/madhhabs").json()
    assert {row["key"] for row in madhhabs} >= {"sunni", "shia"}
    assert any(school["key"] == "jaafari" for school in madhhabs[0]["schools"] + madhhabs[1]["schools"])
    sources = client.get("/api/sources").json()
    assert sources[0]["key"] == "sistani"
    scholars = client.get("/api/scholars").json()
    assert scholars[0]["name_ar"] == "السيد علي الحسيني السيستاني"


def test_books_and_issue_endpoints(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    books = client.get("/api/books").json()
    assert len(books) == 2
    book = client.get(f"/api/books/{books[0]['id']}").json()
    assert "toc" in book and book["issues_count"] >= 1

    issue = client.get("/api/issues/1").json()
    assert issue["id"] == 1
    assert issue["text_original"]

    by_number = client.get("/api/issues/by-number/33").json()
    assert len(by_number) == 2  # المسألة نفسها بمذهبين مختلفين

    missing = client.get("/api/issues/99999")
    assert missing.status_code == 404


def test_search_endpoint_with_filters(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    plain = client.get("/api/search", params={"q": "صيام يوم عرفة"}).json()
    assert plain["total"] == 2
    shia_only = client.get("/api/search", params={"q": "صيام يوم عرفة", "madhhab": "shia"}).json()
    assert shia_only["total"] == 1
    assert shia_only["results"][0]["issue"]["madhhab"] == "الشيعة"
    sunni_only = client.get("/api/search", params={"q": "صيام يوم عرفة", "madhhab": "sunni"}).json()
    assert sunni_only["total"] == 1
    assert "الشافعي" in sunni_only["results"][0]["issue"]["text_original"]


def test_search_returns_citations_metadata(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    data = client.get("/api/search", params={"q": "عرفة"}).json()
    result = data["results"][0]
    for field in ("book_title", "source_url", "section_path", "content_hash"):
        assert field in result["issue"]


def test_admin_stats(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    stats = client.get("/api/admin/stats").json()
    assert stats["issues"] == 2
    assert stats["books"] == 2
    assert "last_crawl" in stats
