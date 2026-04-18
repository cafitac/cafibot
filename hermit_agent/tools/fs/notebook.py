"""NotebookEditTool implementation."""

from __future__ import annotations

from ..base import Tool, ToolResult, _expand_path


class NotebookEditTool(Tool):
    """Jupyter notebook cell editing tool."""
    name = "notebook_edit"
    description = "Edit a Jupyter notebook cell by index. Can modify code or markdown cells."

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to .ipynb file"},
                "cell_index": {"type": "integer", "description": "Cell index (0-based)"},
                "new_source": {"type": "string", "description": "New cell content"},
                "cell_type": {"type": "string", "enum": ["code", "markdown"], "description": "Cell type (optional)"},
            },
            "required": ["path", "cell_index", "new_source"],
        }

    def execute(self, input: dict) -> ToolResult:
        import json as _json
        path = _expand_path(input["path"])
        try:
            with open(path) as f:
                nb = _json.load(f)
            cells = nb.get("cells", [])
            idx = input["cell_index"]
            if idx < 0 or idx >= len(cells):
                return ToolResult(content=f"Cell index {idx} out of range ({len(cells)} cells)", is_error=True)
            cells[idx]["source"] = input["new_source"].splitlines(keepends=True)
            if "cell_type" in input:
                cells[idx]["cell_type"] = input["cell_type"]
            with open(path, "w") as f:
                _json.dump(nb, f, indent=1, ensure_ascii=False)
            return ToolResult(content=f"Updated cell {idx} in {path}")
        except Exception as e:
            return ToolResult(content=f"Error: {e}", is_error=True)


__all__ = ["NotebookEditTool"]
