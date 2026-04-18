"""Baseline tests the benchmark starter ships with."""
from fastapi.testclient import TestClient

from todo.app import app
from todo.models import STORE


def _client() -> TestClient:
    # Reset the in-memory store so each test starts clean.
    STORE._items.clear()
    STORE._ids = iter(range(1, 10**9))
    return TestClient(app)


def test_health() -> None:
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get_todo() -> None:
    c = _client()
    created = c.post("/todos", json={"title": "write tests"})
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "write tests"
    assert body["completed"] is False

    fetched = c.get(f"/todos/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_get_unknown_todo_returns_404() -> None:
    r = _client().get("/todos/999")
    assert r.status_code == 404
