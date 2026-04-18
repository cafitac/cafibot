"""Wire-level regression test for hermit-channel merger (PRD US-000 / US-005).

The probe_channel_notification.py script is the canonical executable
artifact. This test drives it as a subprocess via stdio, speaks the
initialize + tools/call handshake manually, and asserts on:

1. `initializeResult.capabilities.experimental` contains `claude/channel`
   and `claude/channel/permission`.
2. The `notifications/claude/channel` notification that the server emits
   preserves `content` and the full `meta` dict (including `step`).
3. JSONRPCNotification built in-process serialises the custom params
   without stripping `content` / `meta`.

If any of these regress across MCP SDK upgrades, the pin in
pyproject.toml is too loose.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mcp.types import JSONRPCMessage, JSONRPCNotification

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_SCRIPT = REPO_ROOT / "scripts" / "probe_channel_notification.py"


def _send(proc: subprocess.Popen, obj: dict) -> None:
    assert proc.stdin is not None
    line = json.dumps(obj) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def _read_until(proc: subprocess.Popen, predicate, timeout_s: float = 5.0) -> list[dict]:
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout_s
    lines: list[dict] = []
    while time.monotonic() < deadline:
        raw = proc.stdout.readline()
        if not raw:
            time.sleep(0.05)
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        lines.append(msg)
        if predicate(msg):
            return lines
    raise AssertionError(
        f"timeout waiting for predicate; collected {len(lines)} messages: {lines}"
    )


@pytest.fixture
def probe_proc():
    assert PROBE_SCRIPT.exists(), f"missing probe: {PROBE_SCRIPT}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.Popen(
        [sys.executable, str(PROBE_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    try:
        yield proc
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


def test_jsonrpc_notification_preserves_custom_params():
    """In-process sanity: the raw notification type round-trips content+meta."""
    notif = JSONRPCNotification(
        jsonrpc="2.0",
        method="notifications/claude/channel",
        params={
            "content": "<b>hi</b>",
            "meta": {"task_id": "t1", "type": "running", "step": "probe", "source": "hermit"},
        },
    )
    wrapped = JSONRPCMessage(notif)
    serialised = json.loads(wrapped.model_dump_json(exclude_none=True))
    assert serialised["method"] == "notifications/claude/channel"
    assert serialised["params"]["content"] == "<b>hi</b>"
    assert serialised["params"]["meta"]["task_id"] == "t1"
    assert serialised["params"]["meta"]["type"] == "running"
    assert serialised["params"]["meta"]["step"] == "probe"


def test_initialize_response_exposes_channel_capabilities(probe_proc):
    """initializeResult must advertise experimental claude/channel entries."""
    _send(
        probe_proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "wire-test", "version": "0.0"},
            },
        },
    )
    msgs = _read_until(probe_proc, lambda m: m.get("id") == 1)
    init_resp = next(m for m in msgs if m.get("id") == 1)
    exp = init_resp["result"]["capabilities"].get("experimental") or {}
    assert "claude/channel" in exp, f"missing claude/channel in {exp}"
    assert "claude/channel/permission" in exp, f"missing permission cap in {exp}"


def test_probe_emit_produces_channel_notification_on_wire(probe_proc):
    """Calling probe_emit yields a notifications/claude/channel line whose
    params carry the expected content and meta fields."""
    _send(
        probe_proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "wire-test", "version": "0.0"},
            },
        },
    )
    _read_until(probe_proc, lambda m: m.get("id") == 1)

    _send(probe_proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    _send(
        probe_proc,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "probe_emit", "arguments": {}},
        },
    )

    msgs = _read_until(
        probe_proc,
        lambda m: m.get("method") == "notifications/claude/channel",
        timeout_s=5.0,
    )
    channel_frame = next(m for m in msgs if m.get("method") == "notifications/claude/channel")
    params = channel_frame["params"]
    assert params["content"] == "<html>probe</html>"
    meta = params["meta"]
    assert meta["task_id"] == "t1"
    assert meta["type"] == "running"
    assert meta["step"] == "probe"
    assert meta["source"] == "hermit"
