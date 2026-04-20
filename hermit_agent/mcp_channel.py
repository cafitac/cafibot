from __future__ import annotations

import asyncio
import os
import threading
import time

from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCNotification

_LOG_PATH = os.path.expanduser("~/.hermit/mcp_server.log")


def _log(line: str) -> None:
    ts = time.strftime("%H:%M:%S")
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {line}\n")
            f.flush()
    except Exception:
        pass


_current_session = None  # type: ignore[assignment]
_current_loop = None     # type: ignore[assignment]
_session_lock = threading.Lock()
_pending_channel_notifications: list[tuple[str, dict]] = []


async def _send_channel_notification(session, content: str, meta: dict) -> None:
    notif = JSONRPCNotification(
        jsonrpc="2.0",
        method="notifications/claude/channel",
        params={"content": content, "meta": meta},
    )
    _log(f"[channel] -> write_stream.send type={meta.get('kind')} task={str(meta.get('task_id',''))[:8]}")
    await session._write_stream.send(SessionMessage(message=JSONRPCMessage(notif)))
    _log(f"[channel] <- write_stream.send ok type={meta.get('kind')}")


def _schedule_channel_send(loop, session, content: str, meta: dict) -> None:
    async def _send() -> None:
        await _send_channel_notification(session, content, meta)

    def _runner() -> None:
        task = asyncio.create_task(_send())

        def _done_callback(done_task: asyncio.Task) -> None:
            try:
                done_task.result()
            except Exception as e:
                _log(f"[channel] buffered send failed: {e}")

        task.add_done_callback(_done_callback)

    loop.call_soon_threadsafe(_runner)


def _flush_pending_channel_notifications(session, loop) -> None:
    with _session_lock:
        pending = list(_pending_channel_notifications)
        _pending_channel_notifications.clear()

    if not pending:
        return

    for content, meta in pending:
        _log(f"[channel] flushing buffered notification type={meta.get('kind')} task={str(meta.get('task_id',''))[:8]}")
        _schedule_channel_send(loop, session, content, meta)


def _set_active_session(session, loop) -> None:
    global _current_session, _current_loop
    with _session_lock:
        _current_session = session
        _current_loop = loop
    _flush_pending_channel_notifications(session, loop)


def _fire_channel_notification_sync(content: str, meta: dict) -> None:
    with _session_lock:
        session = _current_session
        loop = _current_loop
    if session is None or loop is None:
        with _session_lock:
            _pending_channel_notifications.append((content, meta))
        _log(f"[channel] no active session/loop — notification buffered type={meta.get('kind')}")
        return
    _log(f"[channel] scheduling coroutine type={meta.get('kind')} task={str(meta.get('task_id',''))[:8]}")
    try:
        fut = asyncio.run_coroutine_threadsafe(
            _send_channel_notification(session, content, meta),
            loop,
        )
        fut.result(timeout=5)
        _log(f"[channel] coroutine completed type={meta.get('kind')}")
    except Exception as e:
        _log(f"[channel] send failed: {e}")


def _notify_channel(task_id: str, question: str, options: list[str]) -> None:
    meta = {"task_id": task_id, "kind": "waiting"}
    if options:
        meta["options"] = ",".join(options)
    _fire_channel_notification_sync(question, meta)


def _notify_done(task_id: str, message: str | None = None) -> None:
    meta = {"task_id": task_id, "kind": "done"}
    _fire_channel_notification_sync(message or "task done", meta)


def _notify_reply(task_id: str, message: str) -> None:
    meta = {"task_id": task_id, "kind": "reply"}
    _fire_channel_notification_sync(message, meta)


def _notify_error(task_id: str, message: str) -> None:
    meta = {"task_id": task_id, "kind": "error"}
    _fire_channel_notification_sync(message, meta)


def _notify_running(task_id: str) -> None:
    _fire_channel_notification_sync(
        "task running",
        {"task_id": task_id, "kind": "running"},
    )
