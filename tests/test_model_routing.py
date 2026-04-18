"""Gateway model routing test.

LLM requests must go to the appropriate endpoint, such as ollama / z.ai, depending on the `model` argument.
Previously, it always used a single `llm_url` setting, sending ollama models to z.ai and causing an HTTP 400 error.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.config import DEFAULTS, select_llm_endpoint


def _cfg(**overrides):
    base = {
        "llm_url": "https://api.z.ai/api/coding/paas/v4",
        "llm_api_key": "zai-key",
        "ollama_url": "http://localhost:11434/v1",
    }
    base.update(overrides)
    return base


def test_ollama_url_default_present():
    """ollama_url must exist in the config defaults."""
    assert "ollama_url" in DEFAULTS
    assert "11434" in DEFAULTS["ollama_url"]


def test_zai_model_routes_to_zai():
    """Model names without a colon (cloud API style) go to the configured llm_url."""
    cfg = _cfg()
    url, api_key = select_llm_endpoint("glm-5.1", cfg)
    assert "z.ai" in url
    assert api_key == "zai-key"


def test_ollama_tagged_model_routes_to_ollama():
    """The name:tag pattern is routed to ollama."""
    cfg = _cfg()
    url, api_key = select_llm_endpoint("qwen3:8b", cfg)
    assert "11434" in url
    assert api_key == ""


def test_ollama_coder_model_routes_to_ollama():
    cfg = _cfg()
    url, _ = select_llm_endpoint("qwen3-coder:30b", cfg)
    assert "11434" in url


def test_empty_model_uses_configured_default():
    """If the model name is empty, it goes to the configured llm_url (default)."""
    cfg = _cfg()
    url, api_key = select_llm_endpoint("", cfg)
    assert "z.ai" in url
    assert api_key == "zai-key"


def test_routing_uses_cfg_override_for_ollama_url():
    """If the ollama_url setting is different, that value is used."""
    cfg = _cfg(ollama_url="http://10.0.0.1:11434/v1")
    url, _ = select_llm_endpoint("gemma4:e4b", cfg)
    assert url == "http://10.0.0.1:11434/v1"
