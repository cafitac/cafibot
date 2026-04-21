from __future__ import annotations

import os
import subprocess
from pathlib import Path


def infer_context_size(model: str) -> int:
    """Estimate context window size from model name."""
    m = model.lower()
    if "glm" in m:
        return 65536
    if "qwen3" in m:
        if "64k" in m:
            return 65536
        return 32768
    if "devstral" in m:
        if "64k" in m:
            return 65536
        if "128k" in m:
            return 131072
        return 32768
    return 32000


def run_pytest(cwd: str) -> tuple[bool, str]:
    """Run .venv/bin/pytest in cwd. Returns (passed, output)."""
    venv_pytest = None
    for root in [cwd] + [str(p) for p in Path(cwd).parents]:
        candidate = os.path.join(root, ".venv", "bin", "pytest")
        if os.path.exists(candidate):
            venv_pytest = candidate
            break

    if not venv_pytest:
        return False, "pytest not found"

    try:
        result = subprocess.run(
            [venv_pytest, "-x", "-q", "--tb=short"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)
