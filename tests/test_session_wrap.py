"""hermit_agent.session_wrap — session-end handoff generation and saving.

Save location: `.hermit/handoffs/{YYYYMMDD-HHMMSS}_{session_id}.md`

Red-Green:
1. hermit_agent/session_wrap.py does not exist → Red
2. build_handoff / save_handoff implemented → Green
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.session_wrap import build_handoff, save_handoff


def test_build_handoff_includes_sections():
    md = build_handoff(
        summary="Refactored gateway client.",
        files_touched=["hermit_agent/gateway/__init__.py", "hermit_agent/loop.py"],
        next_steps=["Add retry test", "Update docs"],
    )
    assert "Summary" in md
    assert "Refactored gateway client." in md
    assert "Files" in md
    assert "hermit_agent/gateway/__init__.py" in md
    assert "Next Steps" in md
    assert "Add retry test" in md


def test_build_handoff_empty_lists_still_renders():
    md = build_handoff(summary="Quick fix", files_touched=[], next_steps=[])
    assert "Quick fix" in md
    assert "Files" in md  # section header present even if empty
    assert "Next Steps" in md


def test_save_handoff_creates_file_and_dir():
    with tempfile.TemporaryDirectory() as tmp:
        path = save_handoff(content="hello", session_id="abc123", cwd=tmp)
        assert path.exists()
        assert path.read_text() == "hello"
        assert "abc123" in path.name
        assert (Path(tmp) / ".hermit" / "handoffs").is_dir()


def test_save_handoff_default_session_id():
    """Generates a timestamp-based name if `session_id` is omitted."""
    with tempfile.TemporaryDirectory() as tmp:
        path = save_handoff(content="x", cwd=tmp)
        assert path.exists()
        # Timestamp start
        assert path.stem[:4].isdigit()


def test_save_handoff_filename_prefixes_timestamp():
    with tempfile.TemporaryDirectory() as tmp:
        path = save_handoff(content="x", session_id="sid", cwd=tmp)
        # YYYYMMDD-HHMMSS_sid
        parts = path.stem.split("_", 1)
        assert len(parts) == 2
        assert "-" in parts[0]  # date-time separator
        assert parts[1] == "sid"


def test_build_handoff_markdown_structure():
    md = build_handoff(summary="S", files_touched=["f.py"], next_steps=["do x"])
    # Section headers start with '## '
    assert md.count("## ") >= 3
    # List item
    assert "- f.py" in md or "* f.py" in md
