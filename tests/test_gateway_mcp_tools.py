from __future__ import annotations

import asyncio
import uuid


class _DummyMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def test_run_task_leaves_slash_preprocessing_to_task_runner(monkeypatch):
    import hermit_agent.gateway.mcp_tools as mcp_tools_mod
    import hermit_agent.gateway.task_store as task_store_mod
    import hermit_agent.gateway.task_runner as task_runner_mod
    from hermit_agent.gateway._singletons import sse_manager
    from hermit_agent.gateway.task_store import GatewayTaskState

    dummy = _DummyMCP()
    state = GatewayTaskState(task_id="fixed-task")
    captured: dict[str, object] = {}

    monkeypatch.setattr(task_store_mod, "acquire_worker_slot", lambda: True)
    monkeypatch.setattr(task_store_mod, "create_task", lambda task_id: state)
    monkeypatch.setattr(task_store_mod, "get_task", lambda task_id: state)
    monkeypatch.setattr(sse_manager, "register", lambda task_id: captured.setdefault("registered", task_id))
    monkeypatch.setattr(mcp_tools_mod.uuid, "uuid4", lambda: uuid.UUID(int=0))

    async def fake_run_task_async(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(task_runner_mod, "run_task_async", fake_run_task_async)

    mcp_tools_mod.register_mcp_tools(dummy)
    run_task = dummy.tools["run_task"]

    async def _scenario():
        result = await run_task(task="/plan\nbody", cwd="", model="", max_turns=7)
        await asyncio.sleep(0)
        return result

    result = asyncio.run(_scenario())

    assert result == {"status": "running", "task_id": str(uuid.UUID(int=0))}
    assert captured["registered"] == str(uuid.UUID(int=0))
    assert captured["task"] == "/plan\nbody"
    assert captured["model"] == "__auto__"
    assert captured["max_turns"] == 7
