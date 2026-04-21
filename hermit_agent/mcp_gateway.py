from __future__ import annotations

import os
import time

import httpx


def init_gateway_client(*, load_settings, log_fn):
    """Initialize Gateway client from config/env vars."""
    cfg = load_settings()
    gateway_url = os.environ.get("HERMIT_MCP_GATEWAY_URL") or cfg.get("gateway_url", "http://127.0.0.1:8765")
    gateway_api_key = os.environ.get("HERMIT_MCP_GATEWAY_API_KEY") or cfg.get("gateway_api_key") or None
    if not gateway_api_key:
        log_fn("[gateway] API key not set — using unauthenticated mode")
    client = httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0))
    return gateway_url, gateway_api_key, client


def gateway_headers(gateway_api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if gateway_api_key:
        headers["Authorization"] = f"Bearer {gateway_api_key}"
    return headers


def gateway_health_check(
    *,
    gateway_url: str | None,
    gateway_client,
    consecutive_failures: int,
    last_health_check: float,
    max_consecutive_failures: int,
    force: bool,
    log_fn,
) -> tuple[bool, int, float]:
    now = time.time()
    if not force and now - last_health_check < 10.0:
        return consecutive_failures < max_consecutive_failures, consecutive_failures, last_health_check

    last_health_check = now
    if not gateway_url or not gateway_client:
        return False, consecutive_failures, last_health_check

    try:
        r = gateway_client.get(f"{gateway_url}/health", timeout=5.0)
        is_healthy = r.status_code == 200
        if is_healthy:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
        return is_healthy, consecutive_failures, last_health_check
    except Exception as e:
        consecutive_failures += 1
        log_fn(f"[gateway] health check failed: {e}")
        return False, consecutive_failures, last_health_check
