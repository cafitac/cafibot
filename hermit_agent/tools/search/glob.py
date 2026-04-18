"""File glob search tool (GlobTool)."""

from __future__ import annotations

from pathlib import Path

from ..base import Tool, ToolResult, _expand_path


class GlobTool(Tool):
    name = "glob"
    description = "Find files matching a glob pattern. Returns file paths sorted by modification time."
    is_read_only = True
    is_concurrent_safe = True

    def __init__(self, cwd: str = "."):
        self.cwd = cwd

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": 'Glob pattern (e.g. "**/*.py", "src/**/*.ts")',
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, input: dict) -> ToolResult:
        pattern = input["pattern"]
        search_path = Path(_expand_path(input.get("path", self.cwd), self.cwd))

        try:
            matches = sorted(search_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if not matches:
                return ToolResult(content=f"No files matching pattern: {pattern}")
            result = "\n".join(str(m) for m in matches[:100])
            if len(matches) > 100:
                result += f"\n... and {len(matches) - 100} more"
            return ToolResult(content=result)
        except Exception as e:
            return ToolResult(content=f"Error: {e}", is_error=True)


__all__ = ['GlobTool']
