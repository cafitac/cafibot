from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cli_setup_tests_do_not_emit_unawaited_coroutine_warnings():
    """Setup-flow tests should mock async DB work without leaking coroutine objects."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_cli_setup.py::test_run_setup_auto_detect_ollama",
            "tests/test_cli_setup.py::test_run_setup_explicit_ollama",
            "tests/test_cli_setup.py::test_run_setup_cloud_fallback",
            "tests/test_cli_setup.py::test_run_setup_openai_compatible",
            "-q",
            "-W",
            "always::RuntimeWarning",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "was never awaited" not in output
