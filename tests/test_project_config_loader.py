"""`_find_project_config` — HERMIT.md loader regression test.

Identical to Claude Code's CLAUDE.md pattern, verifies that the project-local HERMIT.md is
automatically injected.

Test cases:
- test_project_hermit_agent_md_picked_up: Loads HERMIT.md in cwd
- test_parent_hermit_agent_md_picked_up: Loads HERMIT.md from parent directory
- test_hidden_alternative_name_picked_up: Loads alternative filename .hermit_agent.md
- test_empty_when_no_config: Empty string if none exists
- test_global_and_project_both_included: Loads global + project simultaneously
- test_global_only_when_no_project: Loads global only when only global exists
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.loop import _find_project_config


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_project_hermit_agent_md_picked_up():
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "HERMIT.md", "PROJECT_MARKER_ABC")
        with patch.dict(os.environ, {"HOME": tmp}):
            result = _find_project_config(tmp)
        assert "PROJECT_MARKER_ABC" in result


def test_parent_hermit_agent_md_picked_up():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "HERMIT.md", "PARENT_MARKER_XYZ")
        child = root / "sub" / "nested"
        child.mkdir(parents=True)
        with patch.dict(os.environ, {"HOME": tmp}):
            result = _find_project_config(str(child))
        assert "PARENT_MARKER_XYZ" in result


def test_hidden_alternative_name_picked_up():
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / ".hermit_agent.md", "HIDDEN_VARIANT_MARKER")
        with patch.dict(os.environ, {"HOME": tmp}):
            result = _find_project_config(tmp)
        assert "HIDDEN_VARIANT_MARKER" in result


def test_empty_when_no_config():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.dict(os.environ, {"HOME": tmp}):
            result = _find_project_config(tmp)
        assert result == ""


def test_global_and_project_both_included():
    with tempfile.TemporaryDirectory() as home_dir:
        with tempfile.TemporaryDirectory() as project_dir:
            _write(Path(home_dir) / ".hermit" / "HERMIT.md", "GLOBAL_MARKER_111")
            _write(Path(project_dir) / "HERMIT.md", "PROJECT_MARKER_222")
            with patch.dict(os.environ, {"HOME": home_dir}):
                result = _find_project_config(project_dir)
            assert "GLOBAL_MARKER_111" in result
            assert "PROJECT_MARKER_222" in result


def test_global_only_when_no_project():
    with tempfile.TemporaryDirectory() as home_dir:
        with tempfile.TemporaryDirectory() as project_dir:
            _write(Path(home_dir) / ".hermit" / "HERMIT.md", "GLOBAL_ONLY_MARKER")
            with patch.dict(os.environ, {"HOME": home_dir}):
                result = _find_project_config(project_dir)
            assert "GLOBAL_ONLY_MARKER" in result
