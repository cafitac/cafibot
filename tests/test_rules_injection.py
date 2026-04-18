"""Whether the contents of `.hermit/rules/*.md` are included in the `_build_dynamic_context` output. In the state with only the `_find_rules` function (previous commit), rules were not actually injected into the system prompt. This test ensures the injection connection."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.loop import _build_dynamic_context


def _w(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_project_rule_appears_in_dynamic_context():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(project) / ".hermit" / "rules" / "coding.md", "RULE_MARKER_AAA")
        with patch.dict(os.environ, {"HOME": home}):
            ctx = _build_dynamic_context(project)
        assert "RULE_MARKER_AAA" in ctx


def test_global_rule_appears_in_dynamic_context():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        _w(Path(home) / ".hermit" / "rules" / "prefs.md", "GLOBAL_RULE_BBB")
        with patch.dict(os.environ, {"HOME": home}):
            ctx = _build_dynamic_context(project)
        assert "GLOBAL_RULE_BBB" in ctx


def test_no_rules_does_not_break_context():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as project:
        with patch.dict(os.environ, {"HOME": home}):
            ctx = _build_dynamic_context(project)
        assert isinstance(ctx, str)
        assert len(ctx) > 0  # date/cwd/os are always present
