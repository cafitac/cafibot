"""`.hermit/rules/` directory loader.

HermitAgent version of the `~/.claude/rules/*.md` pattern. Injected alongside HERMIT.md to allow separate management of global/project
rules.

Search order (deep mode only):
1. Global: `~/.hermit/rules/*.md`
2. Project: `{cwd}/.hermit/rules/*.md`

In shallow mode, loads project only (same policy as HERMIT.md).

Red-Green:
1. No find_rules() function → Red
2. Implement → Green
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.loop import _find_rules


def _w(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_rules_empty_when_no_files():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        with patch.dict(os.environ, {"HOME": home}):
            assert _find_rules(project) == ""


def test_project_rule_loaded():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(project) / ".hermit" / "rules" / "coding.md", "PROJECT_RULE_X")
        with patch.dict(os.environ, {"HOME": home}):
            result = _find_rules(project)
        assert "PROJECT_RULE_X" in result


def test_global_rule_loaded_in_deep():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(home) / ".hermit" / "rules" / "prefs.md", "GLOBAL_RULE_Y")
        with patch.dict(os.environ, {"HOME": home}):
            result = _find_rules(project, depth="deep")
        assert "GLOBAL_RULE_Y" in result


def test_global_skipped_in_shallow():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(home) / ".hermit" / "rules" / "prefs.md", "GLOBAL_ONLY")
        _w(Path(project) / ".hermit" / "rules" / "coding.md", "PROJECT_ONLY")
        with patch.dict(os.environ, {"HOME": home}):
            result = _find_rules(project, depth="shallow")
        assert "PROJECT_ONLY" in result
        assert "GLOBAL_ONLY" not in result


def test_multiple_project_rules_concatenated():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(project) / ".hermit" / "rules" / "a.md", "RULE_A")
        _w(Path(project) / ".hermit" / "rules" / "b.md", "RULE_B")
        with patch.dict(os.environ, {"HOME": home}):
            result = _find_rules(project)
        assert "RULE_A" in result
        assert "RULE_B" in result


def test_non_md_files_ignored():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        rules_dir = Path(project) / ".hermit" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule.md").write_text("KEEPER")
        (rules_dir / "note.txt").write_text("IGNORE_ME")
        with patch.dict(os.environ, {"HOME": home}):
            result = _find_rules(project)
        assert "KEEPER" in result
        assert "IGNORE_ME" not in result


def test_invalid_depth_raises():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _find_rules(tmp, depth="banana")
        except ValueError:
            return
        raise AssertionError("expected ValueError")
