"""MonitorTool — check background process status (incremental output streaming)."""
from __future__ import annotations
import os
from ..base import Tool, ToolResult


def _read_new(path: str, offset: int) -> tuple[str, int]:
    """Read new content from file after offset, return (new_content, new_offset)."""
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read()
        new_offset = offset + len(data)
        return data.decode("utf-8", errors="replace"), new_offset
    except Exception:
        return "", offset


class MonitorTool(Tool):
    name = "monitor"
    description = (
        "Check the status and new output of a background process started with "
        "bash run_in_background=true. Each call returns only output produced "
        "since the previous monitor call (incremental streaming)."
    )
    is_read_only = True
    is_concurrent_safe = True

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "Process ID returned by bash with run_in_background=true",
                },
            },
            "required": ["process_id"],
        }

    def execute(self, input: dict) -> ToolResult:
        from .bash import _background_registry
        pid = input["process_id"]
        entry = _background_registry.get(pid)
        if entry is None:
            return ToolResult(content=f"No background process with ID: {pid}", is_error=True)

        proc = entry["proc"]
        poll = proc.poll()

        stdout, new_stdout_offset = _read_new(entry["stdout_path"], entry["stdout_offset"])
        stderr, new_stderr_offset = _read_new(entry["stderr_path"], entry["stderr_offset"])

        entry["stdout_offset"] = new_stdout_offset
        entry["stderr_offset"] = new_stderr_offset

        if poll is None:
            parts = [f"Status: running (PID {proc.pid})"]
        else:
            parts = [f"Status: done (exit code {poll})"]
            # Clean up temp files + remove from registry
            for path in (entry["stdout_path"], entry["stderr_path"]):
                try:
                    os.unlink(path)
                except Exception:
                    pass
            del _background_registry[pid]

        if stdout:
            parts.append(f"New stdout:\n{stdout.rstrip()}")
        if stderr:
            parts.append(f"New stderr:\n{stderr.rstrip()}")
        if not stdout and not stderr and poll is None:
            parts.append("(no new output)")

        return ToolResult(content="\n".join(parts))


__all__ = ["MonitorTool"]
