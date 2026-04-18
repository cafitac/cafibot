"""G27 — Background tool execution + MonitorTool callback."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.tools.shell.bash import BashTool, _background_registry
from hermit_agent.tools.shell.monitor import MonitorTool


def _fresh_registry():
    """Initialize registry for test isolation."""
    _background_registry.clear()


def test_background_bash_returns_process_id():
    """If run_in_background=true, return process_id immediately."""
    _fresh_registry()
    tool = BashTool()
    result = tool.execute({"command": "sleep 0.1", "run_in_background": True})

    assert not result.is_error, result.content
    assert "process_id" in result.content.lower() or any(
        k in _background_registry for k in _background_registry
    ), f"No process registered. content={result.content}"
    assert len(_background_registry) == 1


def test_background_bash_does_not_block():
    """If run_in_background=true, even long commands return immediately."""
    _fresh_registry()
    tool = BashTool()
    start = time.monotonic()
    result = tool.execute({"command": "sleep 2", "run_in_background": True})
    elapsed = time.monotonic() - start

    assert not result.is_error
    assert elapsed < 1.0, f"Background bash blocked for {elapsed:.2f}s"
    # Cleanup
    for entry in _background_registry.values():
        entry["proc"].kill()


def test_monitor_running_process():
    """A process still running returns a 'running' status."""
    _fresh_registry()
    bash = BashTool()
    bash.execute({"command": "sleep 2", "run_in_background": True})
    pid = next(iter(_background_registry))

    monitor = MonitorTool()
    result = monitor.execute({"process_id": pid})

    assert not result.is_error
    assert "running" in result.content.lower(), result.content
    # Cleanup
    _background_registry[pid]["proc"].kill()


def test_monitor_completed_process_shows_stdout():
    """Completed processes return stdout and 'done'."""
    _fresh_registry()
    bash = BashTool()
    bash.execute({"command": "echo hello_from_bg", "run_in_background": True})
    pid = next(iter(_background_registry))

    # Wait for completion
    _background_registry[pid]["proc"].wait()
    time.sleep(0.05)  # Allow time for file flush

    monitor = MonitorTool()
    result = monitor.execute({"process_id": pid})

    assert not result.is_error
    assert "done" in result.content.lower(), result.content
    assert "hello_from_bg" in result.content, result.content


def test_monitor_unknown_process_id_returns_error():
    """A non-existent process_id returns is_error=True."""
    _fresh_registry()
    monitor = MonitorTool()
    result = monitor.execute({"process_id": "nonexistent"})

    assert result.is_error, result.content


def test_monitor_removes_registry_entry_after_done():
    """Monitoring a completed process removes it from the registry."""
    _fresh_registry()
    bash = BashTool()
    bash.execute({"command": "echo done_check", "run_in_background": True})
    pid = next(iter(_background_registry))

    _background_registry[pid]["proc"].wait()
    time.sleep(0.05)

    monitor = MonitorTool()
    monitor.execute({"process_id": pid})

    assert pid not in _background_registry, "Entry should be removed after completion"
