from __future__ import annotations


def build_ready_payload(*, model: str, cwd: str, version: str, commands: dict[str, str]) -> dict:
    return {
        "type": "ready",
        "model": model,
        "session_id": "gateway",
        "cwd": cwd,
        "permission": "accept_edits",
        "version": version,
        "commands": commands,
    }


def build_gateway_task_request(
    *,
    task: str,
    cwd: str,
    model: str,
    max_turns: int,
    parent_session_id: str,
) -> dict:
    return {
        "task": task,
        "cwd": cwd,
        "model": model,
        "max_turns": max_turns,
        "parent_session_id": parent_session_id,
    }
