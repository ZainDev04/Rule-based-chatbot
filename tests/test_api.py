"""Flask API: request validation, session handling and health reporting."""

import pytest

from app import create_app, MAX_MESSAGE_LENGTH
from chatbot import RuleBasedChatbot


@pytest.fixture
def client():
    app = create_app(RuleBasedChatbot(seed=1))
    app.config["TESTING"] = True
    return app.test_client()


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Nova" in response.data


def test_chat_returns_reply_and_trace(client):
    response = client.post("/api/chat", json={"message": "hello", "session_id": "test-session-1"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["intent"] == "greeting"
    assert body["tier"] == "exact"
    assert body["confidence"] == 1.0
    assert body["cleaned_input"] == "hello"
    assert body["session_id"] == "test-session-1"
    assert "processing_ms" in body
    assert body["session_ended"] is False


def test_chat_assigns_session_id_when_missing(client):
    body = client.post("/api/chat", json={"message": "hi"}).get_json()
    assert len(body["session_id"]) == 32


def test_chat_remembers_name_per_session(client):
    client.post("/api/chat", json={"message": "my name is zain", "session_id": "session-a"})
    a = client.post("/api/chat", json={"message": "what is my name", "session_id": "session-a"}).get_json()
    b = client.post("/api/chat", json={"message": "what is my name", "session_id": "session-b"}).get_json()
    assert "Zain" in a["response"]
    assert "Zain" not in b["response"]


def test_exit_ends_session(client):
    body = client.post("/api/chat", json={"message": "bye", "session_id": "session-c"}).get_json()
    assert body["session_ended"] is True
    assert body["intent"] == "exit"


def test_rejects_non_json(client):
    response = client.post("/api/chat", data="hello", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_json"


def test_rejects_non_string_message(client):
    response = client.post("/api/chat", json={"message": 42})
    assert response.status_code == 400


def test_rejects_long_message(client):
    response = client.post("/api/chat", json={"message": "a" * (MAX_MESSAGE_LENGTH + 1)})
    assert response.status_code == 413


def test_reset_forgets_session(client):
    client.post("/api/chat", json={"message": "my name is zain", "session_id": "session-d"})
    reset = client.post("/api/reset", json={"session_id": "session-d"}).get_json()
    assert reset == {"reset": True, "existed": True}
    body = client.post("/api/chat", json={"message": "what is my name", "session_id": "session-d"}).get_json()
    assert "Zain" not in body["response"]


def test_intents_endpoint(client):
    body = client.get("/api/intents").get_json()
    assert body["count"] == len(body["intents"]) > 20
    first = body["intents"][0]
    assert {"name", "description", "examples", "dynamic"} <= set(first)


def test_health_endpoint(client):
    client.post("/api/chat", json={"message": "zzzz qqqq"})
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok"
    assert body["requests_served"] == 1
    assert body["fallback_rate"] == 1.0


def test_unknown_api_route_is_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
