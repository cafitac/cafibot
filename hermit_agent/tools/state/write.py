"""State write tool (StateWriteTool).

G31: primary save to `.hermit/state/`, legacy fallback to `.omc/state/`.
"""

from __future__ import annotations

import os

from ..base import Tool, ToolResult


class StateWriteTool(Tool):
    """HermitAgent state_write — save to .hermit/state/<mode>-state.json (G31)."""

    name = "state_write"
    description = "Persist state data to .hermit/state/ for resuming across turns."

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
                "data": {
                    "type": "object",
                    "description": "JSON-serialisable state object",
                },
            },
            "required": ["mode", "data"],
        }

    def execute(self, input: dict) -> ToolResult:
        import json as _json

        mode = input.get("mode", "default")
        data = input.get("data", {})
        state_dir = os.path.join(self.cwd, ".hermit", "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, f"{mode}-state.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2, ensure_ascii=False)
            return ToolResult(content=f"State saved: {path}")
        except Exception as e:
            return ToolResult(content=str(e), is_error=True)


__all__ = ['StateWriteTool']
