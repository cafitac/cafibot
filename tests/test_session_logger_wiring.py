"""G1 wiring — Verify that loop.py and tools.py actually call SessionLogger's logging methods.

The unit test (test_session_logger.py) only verifies SessionLogger itself. This file verifies from an integration perspective whether tool_use/tool_result/attachment records are logged to session.jsonl during actual tool execution / compact occurrence.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Iterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.llm_client import OllamaClient, LLMResponse, ToolCall
from hermit_agent.loop import AgentLoop
from hermit_agent.permissions import PermissionMode
from hermit_agent.session_logger import SessionLogger
from hermit_agent.tools import create_default_tools


class _StubLLM(OllamaClient):
    def __init__(self):
        self.model = "stub"

    def chat(self, *args, **kwargs) -> LLMResponse:
        return LLMResponse(content=None, tool_calls=[])

    def chat_stream(self, *args, **kwargs) -> Iterator:
        yield from []


def _read_jsonl(path: str) -> list[dict]:
    records = []
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _make_agent_with_logger(cwd: str) -> tuple[AgentLoop, SessionLogger]:
    tools = create_default_tools(cwd=cwd)
    logger = SessionLogger(cwd=cwd)
    agent = AgentLoop(
        llm=_StubLLM(),
        tools=tools,
        cwd=cwd,
        permission_mode=PermissionMode.YOLO,
    )
    # `# Inject SessionLogger into LLM + emitter (same approach as bridge.py).`
    agent.llm.session_logger = logger
    agent.emitter.session_logger = logger
    return agent, logger


def test_tool_execution_writes_tool_use_and_tool_result():
    """`_execute_tool_calls` writes the tool_use + tool_result record to session.jsonl."""
    with tempfile.TemporaryDirectory() as tmp:
        agent, logger = _make_agent_with_logger(tmp)
        path = os.path.join(tmp, "file.txt")
        with open(path, "w") as f:
            f.write("hello\n")

        tc = ToolCall(id="call_1", name="read_file", arguments={"path": path})
        agent._execute_tool_calls([tc])

        records = _read_jsonl(logger.jsonl_path)
        kinds = [(r.get("type"), r.get("content")[0].get("type") if isinstance(r.get("content"), list) else None) for r in records]

        tool_use_records = [r for r in records if r.get("type") == "assistant" and isinstance(r.get("content"), list) and any(c.get("type") == "tool_use" for c in r["content"])]
        tool_result_records = [r for r in records if r.get("type") == "tool_result"]

        assert tool_use_records, f"tool_use record missing. records={kinds}"
        assert tool_result_records, f"tool_result record missing. records={kinds}"

        tu = tool_use_records[0]["content"][0]
        assert tu["name"] == "read_file"
        assert tu["input"]["path"] == path

        tr = tool_result_records[0]
        assert tr["tool_use_id"] == "call_1"
        assert "hello" in tr["content"]


def test_tool_result_error_records_is_error_flag():
    """Failed tool executions are also logged to tool_result with is_error=True."""
    with tempfile.TemporaryDirectory() as tmp:
        agent, logger = _make_agent_with_logger(tmp)
        tc = ToolCall(
            id="call_err",
            name="read_file",
            arguments={"path": "/nonexistent/file.txt"},
        )
        agent._execute_tool_calls([tc])

        records = _read_jsonl(logger.jsonl_path)
        tr_records = [r for r in records if r.get("type") == "tool_result"]
        assert tr_records, "tool_result missing"
        assert tr_records[0].get("is_error") is True, tr_records[0]


def test_compact_event_records_attachment():
    """When a compact occurs, an attachment(kind='compact') record is logged to session.jsonl."""
    with tempfile.TemporaryDirectory() as tmp:
        agent, logger = _make_agent_with_logger(tmp)

        agent.emitter.compact_notice(token_count=20000, threshold=24000, level=1, trigger_point=19200)

        records = _read_jsonl(logger.jsonl_path)
        compact_records = [
            r for r in records
            if r.get("type") == "attachment" and r.get("kind") == "compact"
        ]
        assert compact_records, f"compact attachment missing. records={records}"
        rec = compact_records[0]
        assert rec.get("token_count") == 20000 or "20000" in rec.get("content", "")
