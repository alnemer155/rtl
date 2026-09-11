"""اختبارات نقطة المحادثة وجلساتها على قاعدة اختبار حقيقية."""

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


def test_chat_creates_conversation_and_saves_messages(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    with client.stream("POST", "/api/chat", json={"message": "ما حكم صيام يوم عرفة عند السيستاني؟"}) as response:
        assert response.status_code == 200
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: meta" in body
    assert "event: status" in body
    assert "event: sources" in body
    # بلا مفتاح Gemini: خطأ عام مهذب بدل انهيار
    assert "event: error" in body or "event: done" in body

    conversations = client.get("/api/chat/conversations").json()
    assert len(conversations) == 1
    detail = client.get(f"/api/chat/conversations/{conversations[0]['id']}").json()
    roles = [message["role"] for message in detail["messages"]]
    assert "user" in roles  # رسالة المستخدم حُفظت فوراً حتى لو فشل النموذج
    assert detail["title"].startswith("ما حكم")


def test_chat_followup_reuses_conversation(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    with client.stream("POST", "/api/chat", json={"message": "السلام عليكم"}) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    import json as json_module

    meta_line = next(line for line in body.splitlines() if line.startswith("data: ") and "conversation_id" in line)
    conversation_id = json_module.loads(meta_line[6:])["conversation_id"]

    with client.stream(
        "POST", "/api/chat", json={"message": "وش رأيك؟", "conversation_id": conversation_id}
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: meta" in body

    detail = client.get(f"/api/chat/conversations/{conversation_id}").json()
    assert len([m for m in detail["messages"] if m["role"] == "user"]) == 2


def test_chat_greeting_skips_retrieval(seeded_engine):
    _seed_two_madhhab_issues(seeded_engine)
    client = _client(seeded_engine)
    with client.stream("POST", "/api/chat", json={"message": "السلام عليكم"}) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: sources" not in body  # تحية: لا استرجاع مصادر


def test_delete_conversation(seeded_engine):
    client = _client(seeded_engine)
    with client.stream("POST", "/api/chat", json={"message": "سؤال تجريبي"}) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    import json as json_module

    meta_line = next(line for line in body.splitlines() if line.startswith("data: ") and "conversation_id" in line)
    conversation_id = json_module.loads(meta_line[6:])["conversation_id"]
    assert client.delete(f"/api/chat/conversations/{conversation_id}").json() == {"deleted": conversation_id}
    assert client.get(f"/api/chat/conversations/{conversation_id}").status_code == 404


def test_chat_unknown_conversation_id_creates_it(seeded_engine):
    """معرف غير موجود: يُعامل كمحادثة جديدة بمعرفه المرسل (بلا فشل)."""
    client = _client(seeded_engine)
    response = client.post(
        "/api/chat", json={"message": "سؤال", "conversation_id": "unknown-id-1234"}
    )
    assert response.status_code == 200
    detail = client.get("/api/chat/conversations/unknown-id-1234")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) >= 1
