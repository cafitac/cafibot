from __future__ import annotations

from pathlib import Path


REMOVED_LEGACY_LEARNER_FILES = [
    "hermit_agent/learner.py",
    "hermit_agent/learner_extraction.py",
    "hermit_agent/learner_reporting.py",
    "hermit_agent/learner_storage.py",
    "hermit_agent/learner_verification.py",
    "hermit_agent/learner_guard.py",
]

REMOVED_LEGACY_LEARNER_TESTS = [
    "tests/test_learner_auto.py",
    "tests/test_learner_deprecation_warning_hygiene.py",
    "tests/test_learner_extraction.py",
    "tests/test_learner_guard.py",
    "tests/test_learner_project_local.py",
    "tests/test_learner_reporting.py",
    "tests/test_learner_storage.py",
    "tests/test_learner_verification.py",
]


def test_legacy_in_process_learner_modules_are_removed() -> None:
    remaining = [path for path in REMOVED_LEGACY_LEARNER_FILES if Path(path).exists()]

    assert remaining == []


def test_legacy_in_process_learner_tests_are_removed() -> None:
    remaining = [path for path in REMOVED_LEGACY_LEARNER_TESTS if Path(path).exists()]

    assert remaining == []
