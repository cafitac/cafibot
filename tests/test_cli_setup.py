"""Tests for cli_setup.py — setup wizard with auto-detection.

Covers:
  - _pick_recommended priority logic
  - _display_detected_backends output
  - _run_auto_detect with available/unavailable backends
  - run_setup flows: auto-detect, explicit MLX/llama.cpp/Ollama, cloud fallback
"""
from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hermit_agent.cli_setup import (
    _display_detected_backends,
    _pick_recommended,
    _run_auto_detect,
    run_setup,
)
from hermit_agent.local_runtime import (
    BACKEND_LLAMA_CPP,
    BACKEND_MLX,
    BACKEND_OLLAMA,
    LocalRuntimeInfo,
)


# ── _pick_recommended ──────────────────────────────────────────────────


def test_pick_recommended_mlx_over_all():
    """MLX is recommended when all three backends are available."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_MLX, base_url="http://localhost:8080/v1", available=True, default_port=8080),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, base_url="http://localhost:8081/v1", available=True, default_port=8081),
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, base_url="http://localhost:11434/v1", available=True, default_port=11434),
    ]
    result = _pick_recommended(runtimes)
    assert result.backend == BACKEND_MLX


def test_pick_recommended_llama_cpp_over_ollama():
    """llama.cpp is recommended over Ollama when MLX is unavailable."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, base_url="http://localhost:8081/v1", available=True, default_port=8081),
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, base_url="http://localhost:11434/v1", available=True, default_port=11434),
    ]
    result = _pick_recommended(runtimes)
    assert result.backend == BACKEND_LLAMA_CPP


def test_pick_recommended_ollama_as_fallback():
    """Ollama is picked when MLX and llama.cpp are unavailable."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, base_url="http://localhost:11434/v1", available=True, default_port=11434),
    ]
    result = _pick_recommended(runtimes)
    assert result.backend == BACKEND_OLLAMA


def test_pick_recommended_nothing_available():
    """Returns unavailable info when nothing is available."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, available=False),
    ]
    result = _pick_recommended(runtimes)
    assert result.available is False


# ── _display_detected_backends ─────────────────────────────────────────


def test_display_detected_backends_shows_available(capsys):
    """Available backends show a checkmark and URL."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, base_url="http://localhost:11434/v1", available=True, default_port=11434),
    ]
    _display_detected_backends(runtimes)
    captured = capsys.readouterr()
    assert "ollama" in captured.out
    assert "11434" in captured.out


def test_display_detected_backends_shows_unavailable(capsys):
    """Unavailable backends show install hints."""
    runtimes = [
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
    ]
    _display_detected_backends(runtimes)
    captured = capsys.readouterr()
    assert "not available" in captured.out
    assert "mlx-lm" in captured.out


# ── _run_auto_detect ───────────────────────────────────────────────────


def test_run_auto_detect_with_ollama_available():
    """Auto-detect configures settings when Ollama is available."""
    settings = {}
    ollama_info = LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url="http://localhost:11434/v1",
        available=True,
        default_port=11434,
    )
    with patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        ollama_info,
    ]), patch("builtins.input", return_value="Y"):
        result = _run_auto_detect(settings, yes=False)

    assert result is True
    assert settings["local_backend"] == BACKEND_OLLAMA
    assert settings["local_llm_url"] == "http://localhost:11434/v1"
    assert settings["local_backend_auto_detected"] is True


def test_run_auto_detect_nothing_available(capsys):
    """Auto-detect returns False and prints install hints when nothing is available."""
    settings = {}
    with patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        LocalRuntimeInfo(backend=BACKEND_OLLAMA, available=False),
    ]):
        result = _run_auto_detect(settings, yes=True)

    assert result is False
    captured = capsys.readouterr()
    assert "No local LLM backend" in captured.out


def test_run_auto_detect_yes_skips_prompt():
    """With yes=True, auto-detect doesn't prompt user."""
    settings = {}
    ollama_info = LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url="http://localhost:11434/v1",
        available=True,
        default_port=11434,
    )
    with patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
        LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        ollama_info,
    ]):
        result = _run_auto_detect(settings, yes=True)

    assert result is True
    assert settings["local_backend"] == BACKEND_OLLAMA


def test_run_auto_detect_user_declines_picks_alternative():
    """When user declines recommended backend, they can pick an alternative."""
    settings = {}
    mlx_info = LocalRuntimeInfo(
        backend=BACKEND_MLX,
        base_url="http://localhost:8080/v1",
        available=True,
        default_port=8080,
    )
    ollama_info = LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url="http://localhost:11434/v1",
        available=True,
        default_port=11434,
    )
    # User says "no" to MLX, then picks option 2 (Ollama)
    with patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
        mlx_info,
        LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
        ollama_info,
    ]), patch("builtins.input", side_effect=["n", "2"]):
        result = _run_auto_detect(settings, yes=False)

    assert result is True
    assert settings["local_backend"] == BACKEND_OLLAMA


# ── run_setup integration flows ────────────────────────────────────────


def _make_fake_settings_dir():
    """Create a temp dir and return (settings_path, tmpdir)."""
    tmpdir = tempfile.mkdtemp()
    settings_path = Path(tmpdir) / "settings.json"
    return settings_path, tmpdir


async def _fake_init_db() -> None:
    return None


async def _fake_create_api_key(api_key: str, user: str, *, grant_all_platforms: bool = False) -> None:
    return None


def test_run_setup_auto_detect_ollama():
    """Full setup flow: auto-detect finds Ollama."""
    settings_path, tmpdir = _make_fake_settings_dir()
    ollama_info = LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url="http://localhost:11434/v1",
        available=True,
        default_port=11434,
    )

    inputs = iter([
        "1",    # Choose Auto-detect
        "Y",    # Confirm Ollama
        "qwen3-coder:30b",  # Model name
        "http://localhost:8765",  # Gateway URL
        "1",    # Auto-generate API key
        "200",  # max_turns
    ])

    with patch("hermit_agent.cli_setup.GLOBAL_SETTINGS_PATH", settings_path), \
         patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
             LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
             LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
             ollama_info,
         ]), \
         patch("builtins.input", side_effect=inputs), \
         patch("hermit_agent.gateway.db.init_db", _fake_init_db), \
         patch("hermit_agent.gateway.db.create_api_key", _fake_create_api_key), \
         patch("hermit_agent.cli_setup.DEFAULTS", new={}):
        run_setup()

    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["local_backend"] == BACKEND_OLLAMA
    assert saved["local_llm_url"] == "http://localhost:11434/v1"
    assert saved["model"] == "qwen3-coder:30b"


def test_run_setup_explicit_ollama():
    """Full setup flow: user explicitly picks Ollama."""
    settings_path, tmpdir = _make_fake_settings_dir()
    ollama_info = LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url="http://localhost:11434/v1",
        available=True,
        default_port=11434,
    )

    inputs = iter([
        "4",    # Choose Ollama
        "qwen3-coder:30b",  # Model name
        "http://localhost:8765",  # Gateway URL
        "1",    # Auto-generate API key
        "200",  # max_turns
    ])

    with patch("hermit_agent.cli_setup.GLOBAL_SETTINGS_PATH", settings_path), \
         patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
             LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
             LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
             ollama_info,
         ]), \
         patch("builtins.input", side_effect=inputs), \
         patch("hermit_agent.gateway.db.init_db", _fake_init_db), \
         patch("hermit_agent.gateway.db.create_api_key", _fake_create_api_key), \
         patch("hermit_agent.cli_setup.DEFAULTS", new={}):
        run_setup()

    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["local_backend"] == BACKEND_OLLAMA


def test_run_setup_cloud_fallback():
    """Full setup flow: no local backend → user picks cloud (z.ai)."""
    settings_path, tmpdir = _make_fake_settings_dir()

    inputs = iter([
        "1",    # Choose Auto-detect
        # No local backend detected → fallback to cloud
        "1",    # Choose z.ai GLM
        "test-api-key",  # API key
        "glm-5.1",  # Model name
        "http://localhost:8765",  # Gateway URL
        "1",    # Auto-generate API key
        "200",  # max_turns
    ])

    with patch("hermit_agent.cli_setup.GLOBAL_SETTINGS_PATH", settings_path), \
         patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
             LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
             LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
             LocalRuntimeInfo(backend=BACKEND_OLLAMA, available=False),
         ]), \
         patch("builtins.input", side_effect=inputs), \
         patch("hermit_agent.gateway.db.init_db", _fake_init_db), \
         patch("hermit_agent.gateway.db.create_api_key", _fake_create_api_key), \
         patch("hermit_agent.cli_setup.DEFAULTS", new={}):
        run_setup()

    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["llm_url"] == "https://api.z.ai/api/coding/paas/v4"
    assert saved["llm_api_key"] == "test-api-key"


def test_run_setup_explicit_mlx_unavailable(capsys):
    """Setup shows install hint when user picks MLX but it's unavailable."""
    settings_path, tmpdir = _make_fake_settings_dir()

    inputs = iter(["2"])  # Choose MLX

    with patch("hermit_agent.cli_setup.GLOBAL_SETTINGS_PATH", settings_path), \
         patch("hermit_agent.cli_setup.detect_all_runtimes", return_value=[
             LocalRuntimeInfo(backend=BACKEND_MLX, available=False),
             LocalRuntimeInfo(backend=BACKEND_LLAMA_CPP, available=False),
             LocalRuntimeInfo(backend=BACKEND_OLLAMA, available=False),
         ]), \
         patch("builtins.input", side_effect=inputs), \
         patch("hermit_agent.cli_setup.DEFAULTS", new={}):
        run_setup()

    captured = capsys.readouterr()
    assert "MLX not available" in captured.out
    assert "pip install mlx-lm" in captured.out


def test_run_setup_openai_compatible():
    """Full setup flow: user picks OpenAI-compatible API."""
    settings_path, tmpdir = _make_fake_settings_dir()

    inputs = iter([
        "6",    # Choose OpenAI-compatible
        "https://api.openai.com/v1",  # URL
        "sk-test-key",  # API key
        "gpt-4o",  # Model name
        "http://localhost:8765",  # Gateway URL
        "1",    # Auto-generate API key
        "200",  # max_turns
    ])

    with patch("hermit_agent.cli_setup.GLOBAL_SETTINGS_PATH", settings_path), \
         patch("builtins.input", side_effect=inputs), \
         patch("hermit_agent.gateway.db.init_db", _fake_init_db), \
         patch("hermit_agent.gateway.db.create_api_key", _fake_create_api_key), \
         patch("hermit_agent.cli_setup.DEFAULTS", new={}):
        run_setup()

    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["llm_url"] == "https://api.openai.com/v1"
    assert saved["llm_api_key"] == "sk-test-key"
    assert saved["model"] == "gpt-4o"
