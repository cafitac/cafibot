"""WriteFileTool implementation."""

from __future__ import annotations

import os

from ..base import (
    Tool,
    ToolResult,
    _check_secrets,
    _display_path,
    _expand_path,
    _format_content_preview,
    _is_safe_path,
    _redirect_to_worktree_path,
)


class WriteFileTool(Tool):
    name = "write_file"
    description = "Create a new file or completely overwrite an existing file with new content."

    SENSITIVE_PATTERNS = [".env", "credentials", "secret", "private_key"]

    def __init__(self, cwd: str = "."):
        self.cwd = cwd

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    def validate(self, input: dict) -> str | None:
        path = input.get("path", "")

        if path.startswith("\\\\"):
            return f"Blocked: UNC paths are not allowed: {path}"

        path_lower = path.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in path_lower:
                return f"Warning: path '{path}' contains sensitive pattern '{pattern}'. Proceed with caution."

        safe_err = _is_safe_path(path, self.cwd)
        if safe_err:
            return safe_err

        return None

    # G40: preview max lines — CC style (show first N lines, omit the rest)
    PREVIEW_MAX_LINES = 10

    def execute(self, input: dict) -> ToolResult:
        input = dict(input)
        input["path"] = _expand_path(input["path"], self.cwd)
        # G39: auto-redirect when accidentally targeting main repo path during worktree work
        redirected_path, redirect_notice = _redirect_to_worktree_path(input["path"], self.cwd)
        input["path"] = redirected_path
        warning = self.validate(input)
        if warning and not warning.startswith("Warning:"):
            return ToolResult(content=warning, is_error=True)

        path = input["path"]
        content = input["content"]

        prefix_parts = []
        if redirect_notice:
            prefix_parts.append(redirect_notice)
        if warning:
            prefix_parts.append(warning)
        prefix = ("\n".join(prefix_parts) + "\n") if prefix_parts else ""

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            display_path = _display_path(path, self.cwd)
            preview = _format_content_preview(content, max_lines=self.PREVIEW_MAX_LINES)
            result_msg = f"{prefix}Wrote {line_count} lines to {display_path}\n{preview}"
            warnings = _check_secrets(content)
            if warnings:
                result_msg += "\n⚠️ " + "; ".join(warnings)
            return ToolResult(content=result_msg)
        except Exception as e:
            return ToolResult(content=f"Error writing file: {e}", is_error=True)


__all__ = ["WriteFileTool"]
