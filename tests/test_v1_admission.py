"""End-to-end admission check for /v1/chat/completions.

Runs the FastAPI app via TestClient and swaps the module-level admission
controller for one that either rejects or accepts deterministically.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hermit_agent.gateway import app
from hermit_agent.gateway.admission import AdmissionController, AdmissionDenied
from hermit_agent.gateway.routes import v1 as v1_mod


class _AlwaysDeny(AdmissionController):
    async def acquire(self, model: str):
        raise AdmissionDenied(
            f"ollama at capacity for '{model}'",
            retry_after=7,
        )


class _AlwaysAdmit(AdmissionController):
    def __init__(self):
        super().__init__(ollama_max_loaded=1, external_max_concurrent=1)
        self.released = 0

    async def acquire(self, model: str):
        class _Tok:
            def release(inner_self):
                self.released += 1
        return _Tok()


@pytest.fixture(autouse=True)
def _bypass_auth():
    from hermit_agent.gateway.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _reset_admission():
    v1_mod._admission = None


def test_chat_completions_returns_503_when_admission_denies():
    _reset_admission()
    v1_mod._admission = _AlwaysDeny(
        ollama_max_loaded=1, external_max_concurrent=1
    )
    client = TestClient(app)
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "new-model:tag",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        },
    )
    assert r.status_code == 503
    body = r.json()
    # FastAPI returns {"detail": {...}} for structured errors.
    assert body["detail"]["code"] == "server_busy"
    assert "capacity" in body["detail"]["message"].lower()
    assert r.headers.get("Retry-After") == "7"
    _reset_admission()
