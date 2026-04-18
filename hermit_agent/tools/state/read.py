"""State read tool (StateReadTool).

G31: primary save to `.hermit/state/`, legacy fallback to `.omc/state/`.
"""

from __future__ import annotations

import os

from ..base import Tool, ToolResult


class StateReadTool(Tool):
    """HermitAgent state_read — read from .hermit/state/<mode>-state.json (OMC .omc/state fallback)."""

    name = "state_read"
    description = "Read persisted state from .hermit/state/ (falls back to .omc/state/ for legacy compat)."
    is_read_only = True
    is_concurrent_safe = True

    def __init__(self, cwd: str = "."):
        self.cwd = cwd

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "State namespace, e.g. 'deep-interview'",
                },
            },
            "required": ["mode"],
        }

    def execute(self, input: dict) -> ToolResult:
        mode = input.get("mode", "default")
        primary = os.path.join(self.cwd, ".hermit", "state", f"{mode}-state.json")
        # Try .hermit/state/ first, fall back to .omc/state/ legacy path
        candidates = [primary, os.path.join(self.cwd, ".omc", "state", f"{mode}-state.json")]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        return ToolResult(content=f.read())
                except Exception as e:
                    return ToolResult(content=str(e), is_error=True)
        return ToolResult(content="{}")


__all__ = ['StateReadTool']
