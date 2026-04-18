"""`should_auto_verify` tuning — only on file changes + cooldown.

Current state (before tuning): Unconditionally calls verifier if auto_verify=True + "done" pattern.
Problem: Running the verifier even on read-only sessions wastes costs.

Tuning:
1. Trigger verifier only if modified_files exists (only on actual changes)
2. Skip duplicate verify within verify_cooldown_turns (default 5)

Red-Green:
1. Before tuning: should_auto_verify is True even without modifications → Red (expect first case to fail)
2. Implementation → Green
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.auto_agents import AutoAgentConfig, AutoAgentRunner


def _runner() -> AutoAgentRunner:
    cfg = AutoAgentConfig(auto_verify=True, verify_cooldown_turns=5)
    return AutoAgentRunner(cfg)


def test_skip_when_auto_verify_disabled():
    cfg = AutoAgentConfig(auto_verify=False)
    r = AutoAgentRunner(cfg)
    r.modified_files.append("x.py")
    assert r.should_auto_verify("task done") is False


def test_skip_when_no_modified_files():
    r = _runner()
    assert r.should_auto_verify("task done") is False


def test_trigger_when_done_and_modified_files_and_fresh():
    r = _runner()
    r.modified_files.append("x.py")
    assert r.should_auto_verify("task done") is True


def test_skip_when_done_pattern_missing():
    r = _runner()
    r.modified_files.append("x.py")
    assert r.should_auto_verify("still working") is False


def test_cooldown_blocks_repeated_verify():
    r = _runner()
    r.modified_files.append("x.py")
    r.note_verify_ran(turn=1)
    r.current_turn = 2  # within 5-turn cooldown
    assert r.should_auto_verify("done") is False


def test_cooldown_clears_after_n_turns():
    r = _runner()
    r.modified_files.append("x.py")
    r.note_verify_ran(turn=1)
    r.current_turn = 7  # past 5-turn cooldown
    assert r.should_auto_verify("done") is True


def test_cooldown_default_value():
    cfg = AutoAgentConfig(auto_verify=True)
    assert cfg.verify_cooldown_turns == 5


def test_skip_when_max_auto_agents_reached():
    r = _runner()
    r.modified_files.append("x.py")
    r.active_count = r.config.max_auto_agents
    assert r.should_auto_verify("done") is False
