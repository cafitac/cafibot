"""Tests for result lazy handoff truncation (US-002)."""
from hermit_agent.mcp_server import _truncate_result, RESULT_CAP, HEAD_SIZE, TAIL_SIZE


def test_short_result_unchanged():
    result = "short text"
    truncated, meta = _truncate_result(result)
    assert truncated == result
    assert meta == {}


def test_long_result_truncated():
    result = "A" * (RESULT_CAP + 1000)
    truncated, meta = _truncate_result(result)
    assert len(truncated) < len(result)
    assert meta["truncated"] is True
    assert meta["original_length"] == RESULT_CAP + 1000
    assert meta["head_size"] == HEAD_SIZE
    assert meta["tail_size"] == TAIL_SIZE


def test_truncation_preserves_head_and_tail():
    head_marker = "HEAD_MARKER"
    tail_marker = "TAIL_MARKER"
    middle = "X" * RESULT_CAP
    result = head_marker + middle + tail_marker
    truncated, _ = _truncate_result(result)
    assert truncated.startswith(head_marker)
    assert truncated.endswith(tail_marker)


def test_truncation_notice_contains_hint():
    result = "X" * (RESULT_CAP + 500)
    truncated, _ = _truncate_result(result)
    assert "check_task" in truncated
    assert "full=true" in truncated


def test_cap_boundary_exactly_at_limit():
    result = "X" * RESULT_CAP
    truncated, meta = _truncate_result(result)
    assert truncated == result
    assert meta == {}


def test_non_string_result_unchanged():
    result = {"key": "value"}
    truncated, meta = _truncate_result(result)
    assert truncated == result
    assert meta == {}
