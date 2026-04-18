"""hermit_agent.plans — test saving/listing/loading plan artifacts.

Storage location: `.hermit/plans/` (project local) — same layer as `.hermit/task_state.md`.

Red-Green:
1. hermit_agent/plans.py missing → Red
2. Implement save_plan/load_plan/list_plans → Green
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.plans import (
    PlanInfo,
    list_plans,
    load_plan,
    save_plan,
)


def test_save_plan_creates_file_and_returns_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = save_plan("Step 1. Foo\nStep 2. Bar", name="my-plan", cwd=tmp)
        assert path.exists()
        assert "my-plan" in path.name
        assert path.read_text().startswith("Step 1.")


def test_save_plan_default_name_is_timestamp():
    with tempfile.TemporaryDirectory() as tmp:
        path = save_plan("body", cwd=tmp)
        assert path.exists()
        # Start with # YYYYMMDD-HHMMSS prefix
        assert path.stem.split("_")[0][:4].isdigit()


def test_save_plan_sanitizes_name():
    """Replace spaces, slashes, and special characters with hyphens."""
    with tempfile.TemporaryDirectory() as tmp:
        path = save_plan("body", name="hello world/foo?bar", cwd=tmp)
        assert "/" not in path.stem
        assert "?" not in path.stem
        assert " " not in path.stem


def test_load_plan_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        save_plan("content-1", name="alpha", cwd=tmp)
        assert load_plan("alpha", cwd=tmp) == "content-1"


def test_load_plan_by_partial_name_match():
    with tempfile.TemporaryDirectory() as tmp:
        save_plan("payload", name="refactor-gateway", cwd=tmp)
        # Allow prefix matching
        assert load_plan("refactor", cwd=tmp) == "payload"


def test_load_plan_missing_raises():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            load_plan("nonexistent", cwd=tmp)
        except FileNotFoundError:
            return
        raise AssertionError("expected FileNotFoundError")


def test_list_plans_empty_when_no_dir():
    with tempfile.TemporaryDirectory() as tmp:
        assert list_plans(cwd=tmp) == []


def test_list_plans_sorted_newest_first():
    with tempfile.TemporaryDirectory() as tmp:
        save_plan("old", name="first", cwd=tmp)
        time.sleep(0.01)
        save_plan("new", name="second", cwd=tmp)
        plans = list_plans(cwd=tmp)
        assert len(plans) == 2
        assert isinstance(plans[0], PlanInfo)
        assert plans[0].mtime >= plans[1].mtime
        assert plans[0].name.endswith("second") or "second" in plans[0].name


def test_plan_info_fields():
    with tempfile.TemporaryDirectory() as tmp:
        save_plan("hi", name="p1", cwd=tmp)
        plans = list_plans(cwd=tmp)
        p = plans[0]
        assert p.path.exists()
        assert p.size_chars == 2
        assert isinstance(p.mtime, float)


def test_save_plan_dir_created_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        plans_dir = Path(tmp) / ".hermit" / "plans"
        assert not plans_dir.exists()
        save_plan("x", cwd=tmp)
        assert plans_dir.exists()
