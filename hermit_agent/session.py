"""Session save/restore — based on Claude Code's sessionHistory.ts pattern.

Saves conversation history to disk and resumes with --resume.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


SESSION_DIR = os.path.expanduser("~/.hermit/sessions")
LATEST_LINK = os.path.join(SESSION_DIR, "latest.json")


@dataclass
class SessionMeta:
    session_id: str
    model: str
    cwd: str
    created_at: float
    updated_at: float
    turn_count: int
    preview: str  # preview of the first user message


@dataclass
class SavedSession:
    meta: SessionMeta
    messages: list[dict]
    system_prompt: str


def save_session(
    session_id: str,
    messages: list[dict],
    system_prompt: str,
    model: str,
    cwd: str,
    turn_count: int,
) -> str:
    """Save session to disk."""
    os.makedirs(SESSION_DIR, exist_ok=True)

    # Extract preview from the first user message
    preview = ""
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            preview = msg["content"][:80]
            break

    meta = SessionMeta(
        session_id=session_id,
        model=model,
        cwd=cwd,
        created_at=time.time(),
        updated_at=time.time(),
        turn_count=turn_count,
        preview=preview,
    )

    session = SavedSession(meta=meta, messages=messages, system_prompt=system_prompt)
    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")

    with open(filepath, "w") as f:
        json.dump({
            "meta": asdict(meta),
            "messages": messages,
            "system_prompt": system_prompt,
        }, f, ensure_ascii=False, indent=2)

    # Update latest link
    with open(LATEST_LINK, "w") as f:
        json.dump({"session_id": session_id}, f)

    return filepath


def load_session(session_id: str | None = None) -> SavedSession | None:
    """Restore session. If session_id is None, loads the most recent session."""
    if session_id is None:
        if not os.path.exists(LATEST_LINK):
            return None
        with open(LATEST_LINK) as f:
            data = json.load(f)
        session_id = data.get("session_id")
        if not session_id:
            return None

    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")
    if not os.path.exists(filepath):
        return None

    with open(filepath) as f:
        data = json.load(f)

    meta = SessionMeta(**data["meta"])
    return SavedSession(
        meta=meta,
        messages=data["messages"],
        system_prompt=data["system_prompt"],
    )


def list_sessions(limit: int = 10) -> list[SessionMeta]:
    """List recent sessions."""
    if not os.path.exists(SESSION_DIR):
        return []

    sessions = []
    for f in Path(SESSION_DIR).glob("*.json"):
        if f.name == "latest.json":
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
            sessions.append(SessionMeta(**data["meta"]))
        except Exception:
            continue

    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions[:limit]


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False
