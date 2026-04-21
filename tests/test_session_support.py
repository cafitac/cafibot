from __future__ import annotations

from hermit_agent.session_support import infer_context_size, run_pytest


def test_infer_context_size_matches_known_model_families():
    assert infer_context_size("glm-5.1") == 65536
    assert infer_context_size("qwen3-coder:30b") == 32768
    assert infer_context_size("qwen3-64k") == 65536
    assert infer_context_size("devstral-128k") == 131072
    assert infer_context_size("unknown-model") == 32000


def test_run_pytest_returns_not_found_for_missing_venv(tmp_path):
    passed, output = run_pytest(str(tmp_path))
    assert passed is False
    assert output == "pytest not found"
