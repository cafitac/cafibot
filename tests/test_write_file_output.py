"""G40 — write_file output UI: relative path + content preview + omission indicator."""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.tools import WriteFileTool


def test_write_file_output_uses_relative_path_from_cwd():
    """The path in the output must be displayed as a relative path based on cwd."""
    with tempfile.TemporaryDirectory() as tmp:
        tool = WriteFileTool(cwd=tmp)
        sub = os.path.join(tmp, "a", "b", "file.txt")
        result = tool.execute({"path": sub, "content": "hello\n"})
        assert not result.is_error
        # Display relative path instead of absolute path
        assert "a/b/file.txt" in result.content
        # Avoid truncating the middle of absolute paths (`...`)
        assert not result.content.strip().endswith("..."), result.content


def test_write_file_output_shows_content_preview_with_line_numbers():
    """The first N lines of content in the output must be displayed with line numbers."""
    with tempfile.TemporaryDirectory() as tmp:
        tool = WriteFileTool(cwd=tmp)
        path = os.path.join(tmp, "out.py")
        content = "line 1\nline 2\nline 3\n"
        result = tool.execute({"path": path, "content": content})
        assert not result.is_error
        # Each line is displayed with a line number
        assert "1" in result.content and "line 1" in result.content
        assert "2" in result.content and "line 2" in result.content


def test_write_file_output_truncates_long_content_with_more_notice():
    """If content is long, display only the first N lines + `... +M more lines` notice."""
    with tempfile.TemporaryDirectory() as tmp:
        tool = WriteFileTool(cwd=tmp)
        path = os.path.join(tmp, "big.py")
        content = "\n".join(f"row {i}" for i in range(1, 31)) + "\n"  # 30 lines
        result = tool.execute({"path": path, "content": content})
        assert not result.is_error
        # Some lines at the beginning are visible, and the 30th line is not visible (omitted)
        assert "row 1" in result.content
        # Omission notice message
        assert "more lines" in result.content.lower() or "+" in result.content
        # The 30th line must not be displayed (must be below the preview cap)
        lines_in_content = result.content.count("row ")
        assert lines_in_content < 30, f"expected preview truncation, got {lines_in_content} rows shown"


def test_write_file_output_absolute_path_when_outside_cwd():
    """Paths outside cwd must be displayed as absolute paths (cannot be relativized)."""
    with tempfile.TemporaryDirectory() as tmp1:
        with tempfile.TemporaryDirectory() as tmp2:
            tool = WriteFileTool(cwd=tmp1)
            outside_path = os.path.join(tmp2, "external.txt")
            result = tool.execute({"path": outside_path, "content": "x\n"})
            assert not result.is_error
            # Maintain absolute path
            assert tmp2 in result.content or outside_path in result.content
