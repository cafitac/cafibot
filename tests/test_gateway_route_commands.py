from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks


def test_help_slash_command_lists_available_commands():
    from hermit_agent.gateway.routes import tasks as tasks_mod

    result = tasks_mod._handle_slash_command("/help")

    assert result is not None
    assert result.startswith("Available commands:")
    assert "/help" in result


def test_status_and_resume_slash_commands_return_gateway_messages():
    from hermit_agent.gateway.routes import tasks as tasks_mod

    assert tasks_mod._handle_slash_command("/status") == "Gateway mode — /status is not yet supported."
    assert tasks_mod._handle_slash_command("/resume") == "Gateway mode does not support /resume."


@pytest.mark.anyio
async def test_create_task_endpoint_short_circuits_gateway_slash_commands():
    from hermit_agent.gateway.routes.tasks import TaskRequest, create_task_endpoint

    result = await create_task_endpoint(
        req=TaskRequest(task="/status", cwd="", model="", max_turns=1),
        background=BackgroundTasks(),
        auth=SimpleNamespace(user="tester"),
    )

    assert result == {
        "task_id": "instant",
        "status": "done",
        "result": "Gateway mode — /status is not yet supported.",
    }


@pytest.mark.anyio
async def test_create_task_endpoint_schedules_background_work_for_normal_tasks():
    from hermit_agent.gateway._singletons import sse_manager
    from hermit_agent.gateway.routes.tasks import TaskRequest, create_task_endpoint
    from hermit_agent.gateway.task_store import delete_task, get_task

    background = BackgroundTasks()
    result = await create_task_endpoint(
        req=TaskRequest(task="do work", cwd="", model="", max_turns=2),
        background=background,
        auth=SimpleNamespace(user="tester"),
    )
    task_id = result["task_id"]

    try:
        assert result == {"task_id": task_id, "status": "running"}
        assert len(background.tasks) == 1
        assert get_task(task_id) is not None
        assert task_id in sse_manager._queues
    finally:
        delete_task(task_id)
        sse_manager._queues.pop(task_id, None)
