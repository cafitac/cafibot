"""G38 — If the LLM tries to end the turn without tool_calls or text, retry once to force summary."""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.llm_client import OllamaClient, LLMResponse
from hermit_agent.loop import AgentLoop
from hermit_agent.permissions import PermissionMode
from hermit_agent.tools import create_default_tools


class _ScriptedLLM(OllamaClient):
    """A stub that returns the given response sequence in order."""

    def __init__(self, responses: list[LLMResponse]):
        self.model = "stub"
        self._responses = list(responses)
        self.calls = []

    def chat(self, *args, **kwargs) -> LLMResponse:
        self.calls.append({"args": args, "kwargs": kwargs})
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content=None, tool_calls=[])

    def chat_stream(self, *args, **kwargs):
        yield from []


def _make_agent(cwd: str, llm: OllamaClient) -> AgentLoop:
    agent = AgentLoop(
        llm=llm,
        tools=create_default_tools(cwd=cwd),
        cwd=cwd,
        permission_mode=PermissionMode.YOLO,
    )
    agent._context_injected = True  # Skip classification call (scripted LLM)
    return agent


def test_empty_response_triggers_summary_retry_once():
    """If the first response is completely empty, inject a system-reminder to request summary and retry."""
    with tempfile.TemporaryDirectory() as tmp:
        llm = _ScriptedLLM([
            LLMResponse(content=None, tool_calls=[]),       # 1st call: blank
            LLMResponse(content="All steps completed summary", tool_calls=[]),  # 2nd call: summary
        ])
        agent = _make_agent(tmp, llm)
        # Since _call_streaming uses chat_stream, a direct chat replacement path is needed:
        # Temporarily wrap chat_stream as chat to return the same sequence.
        def _fake_stream(*a, **kw):
            from hermit_agent.llm_client import StreamChunk
            r = llm.chat(*a, **kw)
            if r.content:
                yield StreamChunk(type="text", text=r.content)
        llm.chat_stream = _fake_stream  # type: ignore

        result = agent.run("start")
        # summary included in final result
        assert "completed summary" in result or "summary" in result.lower(), result
        # LLM is called at least twice
        assert len(llm.calls) >= 2, f"expected retry, got {len(llm.calls)} calls"
        # Whether messages contain reminder (user role, system-reminder tag)
        reminders = [
            m for m in agent.messages
            if m.get("role") == "user" and "system-reminder" in str(m.get("content", ""))
            and ("summary" in str(m.get("content", "")).lower() or "summary" in str(m.get("content", "")))
        ]
        assert reminders, f"summary reminder not injected. messages={agent.messages}"


def test_double_empty_response_ends_gracefully_no_infinite_loop():
    """If it is blank twice in a row, do not retry and just exit."""
    with tempfile.TemporaryDirectory() as tmp:
        llm = _ScriptedLLM([
            LLMResponse(content=None, tool_calls=[]),
            LLMResponse(content=None, tool_calls=[]),
            LLMResponse(content=None, tool_calls=[]),  # Safety net (exit if 3rd call is also empty)
        ])
        agent = _make_agent(tmp, llm)

        def _fake_stream(*a, **kw):
            from hermit_agent.llm_client import StreamChunk
            r = llm.chat(*a, **kw)
            if r.content:
                yield StreamChunk(type="text", text=r.content)
        llm.chat_stream = _fake_stream  # type: ignore

        result = agent.run("start")
        # Call up to 2 times and exit (not an infinite loop)
        assert len(llm.calls) <= 3, f"infinite loop? {len(llm.calls)} calls"
        assert "[No response]" in result or result == "" or result is None or "summary" not in result


def test_response_with_text_skips_summary_retry():
    """If the first response contains text, do not retry."""
    with tempfile.TemporaryDirectory() as tmp:
        llm = _ScriptedLLM([
            LLMResponse(content="First response with summary", tool_calls=[]),
        ])
        agent = _make_agent(tmp, llm)

        def _fake_stream(*a, **kw):
            from hermit_agent.llm_client import StreamChunk
            r = llm.chat(*a, **kw)
            if r.content:
                yield StreamChunk(type="text", text=r.content)
        llm.chat_stream = _fake_stream  # type: ignore

        result = agent.run("start")
        assert "First response" in result
        # Called exactly once
        assert len(llm.calls) == 1, f"unexpected extra calls: {len(llm.calls)}"
