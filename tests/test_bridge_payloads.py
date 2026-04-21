from __future__ import annotations

from hermit_agent.bridge_payloads import build_gateway_task_request, build_ready_payload


def test_build_ready_payload_matches_bridge_contract():
    payload = build_ready_payload(
        model="gpt-5.4",
        cwd="/tmp/project",
        version="1.2.3",
        commands={"/help": "Get help"},
    )

    assert payload == {
        "type": "ready",
        "model": "gpt-5.4",
        "session_id": "gateway",
        "cwd": "/tmp/project",
        "permission": "accept_edits",
        "version": "1.2.3",
        "commands": {"/help": "Get help"},
    }


def test_build_gateway_task_request_matches_bridge_task_creation_shape():
    payload = build_gateway_task_request(
        task="do work",
        cwd="/tmp/project",
        model="__auto__",
        max_turns=9,
        parent_session_id="session-1",
    )

    assert payload == {
        "task": "do work",
        "cwd": "/tmp/project",
        "model": "__auto__",
        "max_turns": 9,
        "parent_session_id": "session-1",
    }
