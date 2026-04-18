"""ReadFileTool implementation."""

from __future__ import annotations

import os

from ..base import Tool, ToolResult, _expand_path


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file. Always read a file before editing it."
    is_read_only = True
    is_concurrent_safe = True

    BLOCKED_PATHS = [
        "/dev/zero",
        "/dev/random",
        "/dev/urandom",
        "/dev/null",
        "/dev/stdin",
        "/dev/stdout",
        "/dev/stderr",
    ]

    FILE_SIZE_LIMIT = 100 * 1024 * 1024  # 100MB

    def __init__(self, cwd: str = "."):
        self.cwd = cwd
        self.read_files: set[str] = set()
        self._file_mtimes: dict[str, float] = {}
        # C2: (abs_path, offset, limit) → read content cache (for re-read detection after compaction)
        self._read_cache: dict[tuple[str, int, int | None], str] = {}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-based, default: 0)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of lines to read (default: 200)",
                },
            },
            "required": ["path"],
        }

    def validate(self, input: dict) -> str | None:
        path = input["path"]

        for blocked in self.BLOCKED_PATHS:
            if path.startswith(blocked):
                return f"Blocked: reading from '{path}' is not allowed"

        if not os.path.exists(path):
            return f"File not found: {path}"
        if os.path.isdir(path):
            return f"Path is a directory, not a file: {path}"

        try:
            size = os.path.getsize(path)
            if size > self.FILE_SIZE_LIMIT:
                return f"File too large: {size} bytes exceeds limit of {self.FILE_SIZE_LIMIT} bytes (100MB)"
        except OSError as e:
            return f"Cannot stat file: {e}"

        return None

    def execute(self, input: dict) -> ToolResult:
        input = dict(input)
        input["path"] = _expand_path(input["path"], self.cwd)
        error = self.validate(input)
        if error:
            return ToolResult(content=error, is_error=True)

        path = input["path"]
        limit = input.get("limit")
        ext = os.path.splitext(path)[1].lower()

        # Image file
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'):
            size = os.path.getsize(path)
            return ToolResult(content=f"[Image file: {path} ({size} bytes). Use a multimodal model to view.]")

        # PDF file
        if ext == '.pdf':
            try:
                import subprocess
                result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    self.read_files.add(os.path.abspath(path))
                    return ToolResult(content=result.stdout[:50000])
            except FileNotFoundError:
                pass
            size = os.path.getsize(path)
            return ToolResult(content=f"[PDF file: {path} ({size} bytes). Install pdftotext for text extraction.]")

        # Jupyter notebook
        if ext == '.ipynb':
            try:
                import json as _json
                with open(path) as f:
                    nb = _json.load(f)
                out_lines = []
                for i, cell in enumerate(nb.get("cells", [])):
                    ctype = cell.get("cell_type", "unknown")
                    source = "".join(cell.get("source", []))
                    out_lines.append(f"--- Cell {i} ({ctype}) ---")
                    out_lines.append(source)
                    for output in cell.get("outputs", []):
                        if "text" in output:
                            out_lines.append("Output: " + "".join(output["text"]))
                self.read_files.add(os.path.abspath(path))
                return ToolResult(content="\n".join(out_lines)[:50000])
            except Exception as e:
                return ToolResult(content=f"Error reading notebook: {e}", is_error=True)

        try:
            offset = input.get("offset", 0)
            if limit is None:
                limit = 200  # default 200 lines (32K context protection)

            abs_path = os.path.abspath(path)
            cache_key = (abs_path, offset, limit)
            current_mtime = os.path.getmtime(path)

            # C2: on re-reading the same file with identical params, return cached content (full content)
            if cache_key in self._read_cache and self._file_mtimes.get(abs_path) == current_mtime:
                cached = self._read_cache[cache_key]
                return ToolResult(
                    content=(
                        f"[Already read — file unchanged]\n"
                        f"path: {path} (offset={offset})\n\n"
                        f"{cached}"
                    )
                )

            with open(path, "r") as f:
                raw = f.read()
            all_lines = raw.splitlines(keepends=True)
            total_lines = len(all_lines)
            sliced = all_lines[offset:offset + limit]
            content = "".join(f"{offset + i + 1}\t{line}" for i, line in enumerate(sliced))

            # Add truncation notice if content was cut
            remaining = total_lines - (offset + len(sliced))
            if remaining > 0:
                content += f"\n[...{remaining} more lines. Use offset={offset + limit} to continue reading.]"

            self.read_files.add(abs_path)
            self._file_mtimes[abs_path] = current_mtime
            self._read_cache[cache_key] = content
            return ToolResult(content=content or "(empty file)")
        except Exception as e:
            return ToolResult(content=f"Error reading file: {e}", is_error=True)


__all__ = ["ReadFileTool"]
