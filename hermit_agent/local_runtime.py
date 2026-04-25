"""Local LLM runtime auto-detection.

Probe order (first healthy wins):
  1. MLX        — Apple Silicon only (darwin/arm64 + mlx-lm importable)
  2. llama.cpp  — cross-platform (llama-server binary)
  3. Ollama     — universal fallback (ollama binary)

All probes: binary/module exists AND HTTP health check succeeds.
v1 uses default ports only: MLX 8080, llama.cpp 8081, Ollama 11434.
"""

from __future__ import annotations

import importlib.util
import logging
import platform
import shutil
import sys
from dataclasses import dataclass

import httpx

logger = logging.getLogger("hermit_agent.local_runtime")

# Backend constants
BACKEND_MLX = "mlx"
BACKEND_LLAMA_CPP = "llama_cpp"
BACKEND_OLLAMA = "ollama"

# Default ports
_MLX_DEFAULT_PORT = 8080
_LLAMA_CPP_DEFAULT_PORT = 8081
_OLLAMA_DEFAULT_PORT = 11434

_HEALTH_TIMEOUT = 3.0  # seconds


@dataclass
class LocalRuntimeInfo:
    """Result of a local runtime probe."""

    backend: str | None = None
    base_url: str | None = None
    default_port: int | None = None
    model_hint: str | None = None
    available: bool = False


def detect_local_runtime() -> LocalRuntimeInfo:
    """Probe for local LLM backends in priority order.

    Returns the first healthy backend found, or an unavailable info if none.
    """
    probes = [_probe_mlx, _probe_llama_cpp, _probe_ollama]
    for probe in probes:
        try:
            result = probe()
            if result.available:
                return result
        except Exception as exc:
            logger.debug("Probe %s failed: %s", probe.__name__, exc)
    return LocalRuntimeInfo(available=False)


def _health_check(url: str, timeout: float = _HEALTH_TIMEOUT) -> bool:
    """Return True if the server responds at the given base URL."""
    try:
        resp = httpx.get(url, timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _probe_mlx() -> LocalRuntimeInfo:
    """Probe for MLX runtime (Apple Silicon only)."""
    if sys.platform != "darwin":
        return LocalRuntimeInfo(available=False)

    if platform.machine() != "arm64":
        return LocalRuntimeInfo(available=False)

    # Check if mlx-lm is importable
    if importlib.util.find_spec("mlx_lm") is None:
        return LocalRuntimeInfo(available=False)

    base_url = f"http://localhost:{_MLX_DEFAULT_PORT}/v1"
    if not _health_check(f"http://localhost:{_MLX_DEFAULT_PORT}/health"):
        return LocalRuntimeInfo(available=False)

    return LocalRuntimeInfo(
        backend=BACKEND_MLX,
        base_url=base_url,
        default_port=_MLX_DEFAULT_PORT,
        available=True,
    )


def _probe_llama_cpp() -> LocalRuntimeInfo:
    """Probe for llama.cpp server (llama-server binary)."""
    if shutil.which("llama-server") is None:
        return LocalRuntimeInfo(available=False)

    base_url = f"http://localhost:{_LLAMA_CPP_DEFAULT_PORT}/v1"
    if not _health_check(f"http://localhost:{_LLAMA_CPP_DEFAULT_PORT}/health"):
        return LocalRuntimeInfo(available=False)

    return LocalRuntimeInfo(
        backend=BACKEND_LLAMA_CPP,
        base_url=base_url,
        default_port=_LLAMA_CPP_DEFAULT_PORT,
        available=True,
    )


def _probe_ollama() -> LocalRuntimeInfo:
    """Probe for Ollama runtime."""
    if shutil.which("ollama") is None:
        return LocalRuntimeInfo(available=False)

    base_url = f"http://localhost:{_OLLAMA_DEFAULT_PORT}/v1"
    if not _health_check(f"http://localhost:{_OLLAMA_DEFAULT_PORT}"):
        return LocalRuntimeInfo(available=False)

    return LocalRuntimeInfo(
        backend=BACKEND_OLLAMA,
        base_url=base_url,
        default_port=_OLLAMA_DEFAULT_PORT,
        available=True,
    )


def detect_all_runtimes() -> list[LocalRuntimeInfo]:
    """Return ALL detected backends (not just the first)."""
    probes = [_probe_mlx, _probe_llama_cpp, _probe_ollama]
    results: list[LocalRuntimeInfo] = []
    for probe in probes:
        try:
            result = probe()
            results.append(result)
        except Exception as exc:
            logger.debug("Probe %s failed: %s", probe.__name__, exc)
            results.append(LocalRuntimeInfo(available=False))
    return results


_BACKEND_INSTALL_HINTS: dict[str, str] = {
    BACKEND_MLX: "pip install mlx-lm",
    BACKEND_LLAMA_CPP: "https://github.com/ggerganov/llama.cpp/releases",
    BACKEND_OLLAMA: "curl -fsSL https://ollama.com/install.sh | sh",
}


def get_install_hints(unavailable_backend: str) -> str | None:
    """Return install hint for an unavailable backend."""
    return _BACKEND_INSTALL_HINTS.get(unavailable_backend)
