from __future__ import annotations

import os

AUTO_MODEL_SENTINEL = "__auto__"


def normalize_requested_model(model: str | None) -> str:
    normalized = (model or "").strip()
    return normalized or AUTO_MODEL_SENTINEL


def normalize_task_cwd(cwd: str | None) -> str:
    return cwd or os.getcwd()
