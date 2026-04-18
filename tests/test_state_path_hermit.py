"""Verify that state_write/state_read saves to `.hermit/state/` instead of `.omc/state/` (G31 extension)."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.tools import StateReadTool, StateWriteTool


def test_state_write_saves_under_hermit_agent_state():
    with tempfile.TemporaryDirectory() as tmp:
        tool = StateWriteTool(cwd=tmp)
        result = tool.execute({"mode": "deep-interview", "data": {"active": True, "foo": "bar"}})
        assert not result.is_error
        expected = os.path.join(tmp, ".hermit", "state", "deep-interview-state.json")
        assert os.path.exists(expected), f"expected {expected}"
        assert expected in result.content
        # .omc/state is not created
        assert not os.path.exists(os.path.join(tmp, ".omc", "state", "deep-interview-state.json"))
        with open(expected) as f:
            assert json.load(f) == {"active": True, "foo": "bar"}


def test_state_read_reads_from_hermit_agent_state():
    with tempfile.TemporaryDirectory() as tmp:
        hermit_agent_state = os.path.join(tmp, ".hermit", "state")
        os.makedirs(hermit_agent_state)
        with open(os.path.join(hermit_agent_state, "deep-interview-state.json"), "w") as f:
            json.dump({"hello": "world"}, f)

        tool = StateReadTool(cwd=tmp)
        result = tool.execute({"mode": "deep-interview"})
        assert not result.is_error
        assert json.loads(result.content) == {"hello": "world"}


def test_state_read_backfill_from_omc_state_for_compat():
    """Support reading state from the existing `.omc/state/` during the migration phase (fallback if missing)."""
    with tempfile.TemporaryDirectory() as tmp:
        omc_state = os.path.join(tmp, ".omc", "state")
        os.makedirs(omc_state)
        with open(os.path.join(omc_state, "deep-interview-state.json"), "w") as f:
            json.dump({"legacy": True}, f)

        tool = StateReadTool(cwd=tmp)
        result = tool.execute({"mode": "deep-interview"})
        # .hermit/state may not exist in a clean installation — allow .omc fallback
        assert not result.is_error
        data = json.loads(result.content)
        assert data.get("legacy") is True


def test_state_read_missing_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        tool = StateReadTool(cwd=tmp)
        result = tool.execute({"mode": "nonexistent"})
        assert not result.is_error
        assert result.content == "{}"
