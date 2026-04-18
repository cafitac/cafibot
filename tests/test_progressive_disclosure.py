"""`_find_project_config(cwd, depth)` Progressive Disclosure.

depth option:
- "deep" (default): global + project walk-up — maintains existing behavior
- "shallow": exactly the project cwd level only. Ignores global/parent directories → reduces context cost

Red-Green:
1. No depth parameter → Red
2. Implementation added → Green
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.loop import _find_project_config


def _w(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_default_depth_is_deep():
    """Existing behavior: loads both global and walk-up."""
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as project:
            _w(Path(home) / ".hermit" / "HERMIT.md", "GLOBAL")
            _w(Path(project) / "HERMIT.md", "PROJECT")
            with patch.dict(os.environ, {"HOME": home}):
                result = _find_project_config(project)
            assert "GLOBAL" in result
            assert "PROJECT" in result


def test_shallow_depth_skips_global():
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as project:
            _w(Path(home) / ".hermit" / "HERMIT.md", "GLOBAL_XYZ")
            _w(Path(project) / "HERMIT.md", "PROJECT_XYZ")
            with patch.dict(os.environ, {"HOME": home}):
                result = _find_project_config(project, depth="shallow")
            assert "PROJECT_XYZ" in result
            assert "GLOBAL_XYZ" not in result


def test_shallow_depth_skips_parent_walk_up():
    """shallow: ignores HERMIT.md in parent directories."""
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as root:
            _w(Path(root) / "HERMIT.md", "ROOT_MARKER")
            child = Path(root) / "sub" / "nested"
            child.mkdir(parents=True)
            with patch.dict(os.environ, {"HOME": home}):
                result = _find_project_config(str(child), depth="shallow")
            assert "ROOT_MARKER" not in result


def test_shallow_depth_still_picks_up_immediate_file():
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as project:
            _w(Path(project) / "HERMIT.md", "IMMEDIATE_MARKER")
            with patch.dict(os.environ, {"HOME": home}):
                result = _find_project_config(project, depth="shallow")
            assert "IMMEDIATE_MARKER" in result


def test_deep_depth_explicit_matches_default():
    with tempfile.TemporaryDirectory() as home:
        with tempfile.TemporaryDirectory() as project:
            _w(Path(home) / ".hermit" / "HERMIT.md", "G")
            _w(Path(project) / "HERMIT.md", "P")
            with patch.dict(os.environ, {"HOME": home}):
                explicit = _find_project_config(project, depth="deep")
                default = _find_project_config(project)
            assert explicit == default


def test_invalid_depth_raises():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _find_project_config(tmp, depth="banana")
        except ValueError:
            return
        raise AssertionError("expected ValueError for invalid depth")
