"""G30-C: LLM response timeout test.

- On SLOW_CALL_THRESHOLD elapsed: on_slow_call callback + [LLM_CALL_SLOW] log
- On CALL_TIMEOUT elapsed: request cancellation + [LLM_CALL_TIMEOUT] log + TimeoutError
- Caller messages list immutable on timeout
- Normal responses pass through existing path
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from hermit_agent.llm_client import OllamaClient, LLMCallTimeout


class _FakeLogger:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    def log(self, tag: str, content: str) -> None:
        self.entries.append((tag, content))


class _FakeResponse:
    """Mock response compatible with httpx.Response."""
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.status_code = 200

    def json(self):
        import json
        return json.loads(self._data)

    def raise_for_status(self):
        pass


def _make_client(monkeypatch, delay: float, logger: _FakeLogger | None = None) -> OllamaClient:
    """Replace httpx.Client.post with sleep followed by an empty response. Raises ReadTimeout on timeout exceeded."""
    import httpx as _httpx
    _delay = delay

    class _FakeClient:
        def __init__(self, timeout=None):
            self._timeout = timeout

        def post(self, url, json=None, headers=None):
            read_timeout = None
            if self._timeout:
                # read field of httpx.Timeout object or simple float
                read_timeout = getattr(self._timeout, 'read', self._timeout)
            if read_timeout and _delay > read_timeout:
                time.sleep(read_timeout)
                raise _httpx.ReadTimeout(f"Timed out after {read_timeout}s")
            time.sleep(_delay)
            payload = (
                b'{"choices":[{"message":{"role":"assistant","content":"ok","tool_calls":null}}]}'
            )
            return _FakeResponse(payload)

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("hermit_agent.llm_client.httpx.Client", _FakeClient)

    client = OllamaClient(base_url="http://localhost:9", model="fake")
    # Short threshold for testing
    client.SLOW_CALL_THRESHOLD = 0.05
    client.CALL_TIMEOUT = 0.25
    client.MAX_RETRIES = 0
    if logger is not None:
        client.session_logger = logger
    return client


def test_normal_response_under_threshold(monkeypatch):
    """Normal responses (delay < SLOW_CALL_THRESHOLD) pass through the existing path."""
    logger = _FakeLogger()
    client = _make_client(monkeypatch, delay=0.01, logger=logger)

    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp.content == "ok"
    # No SLOW events should occur
    tags = {t for t, _ in logger.entries}
    assert "LLM_CALL_SLOW" not in tags
    assert "LLM_CALL_TIMEOUT" not in tags


def test_slow_call_emits_warning(monkeypatch):
    """If exceeding SLOW_CALL_THRESHOLD but below CALL_TIMEOUT, log only a SLOW warning."""
    logger = _FakeLogger()
    client = _make_client(monkeypatch, delay=0.12, logger=logger)

    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp.content == "ok"
    tags = [t for t, _ in logger.entries]
    assert "LLM_CALL_SLOW" in tags
    assert "LLM_CALL_TIMEOUT" not in tags


def test_call_timeout_cancels(monkeypatch):
    """Raise LLMCallTimeout + log on CALL_TIMEOUT exceeded."""
    logger = _FakeLogger()
    client = _make_client(monkeypatch, delay=2.0, logger=logger)

    messages = [{"role": "user", "content": "hi"}]
    snapshot = list(messages)

    with pytest.raises(LLMCallTimeout):
        client.chat(messages=messages)

    # Message state immutable
    assert messages == snapshot
    tags = [t for t, _ in logger.entries]
    assert "LLM_CALL_TIMEOUT" in tags


def test_timeout_wall_time_is_bounded(monkeypatch):
    """Even if the actual response is delayed, it must return near CALL_TIMEOUT."""
    logger = _FakeLogger()
    client = _make_client(monkeypatch, delay=2.0, logger=logger)

    start = time.monotonic()
    with pytest.raises(LLMCallTimeout):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    elapsed = time.monotonic() - start
    # Timeout + slight margin — must not wait for actual response (2.0s)
    assert elapsed < 1.0, f"chat blocked for {elapsed:.2f}s, expected timeout near 0.25s"
