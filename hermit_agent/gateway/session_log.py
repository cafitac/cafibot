"""GatewaySessionLog — per-task structured event logging that mirrors what
SessionLogger does for the agent loop, but at the gateway tier. Writes:
  ~/.hermit/logs/gateway/{cwd_slug}/{task_id}/meta.json
  ~/.hermit/logs/gateway/{cwd_slug}/{task_id}/events.jsonl

Distinct from the operational stdlib log at ~/.hermit/gateway.log — keep that
file intact for ops; this is for /recap and per-conversation reconstruction.
"""
from __future__ import annotations
import datetime
import json
import os
import threading
from typing import Optional

from ..session_store import SessionStore


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class GatewaySessionLog:
    def __init__(self, task_id: str, cwd: str, model: str, parent_session_id: Optional[str] = None):
        self._store = SessionStore()
        self._session_dir = self._store.create_session(
            mode='gateway',
            session_id=task_id,
            cwd=cwd,
            model=model,
            parent_session_id=parent_session_id,
        )
        self._events_path = os.path.join(self._session_dir, 'events.jsonl')
        self._lock = threading.Lock()
        self.write_event({'type': 'start', 'ts': _now_iso(), 'task_id': task_id, 'model': model})

    def write_event(self, record: dict) -> None:
        with self._lock:
            try:
                with open(self._events_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            except Exception:
                pass

    def mark_completed(self, token_totals: Optional[dict] = None) -> None:
        self.write_event({'type': 'done', 'ts': _now_iso(), 'token_totals': token_totals or {}})
        try:
            self._store.update_meta(self._session_dir, status='completed')
        except Exception:
            pass

    def mark_crashed(self, error: str) -> None:
        self.write_event({'type': 'error', 'ts': _now_iso(), 'message': error})
        try:
            self._store.update_meta(self._session_dir, status='crashed')
        except Exception:
            pass

    @property
    def session_dir(self) -> str:
        return self._session_dir
