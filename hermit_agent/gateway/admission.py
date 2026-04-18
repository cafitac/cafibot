"""Admission control for Gateway LLM requests.

Two responsibilities, corresponding to the two kinds of downstream LLM
the gateway talks to:

1. **Ollama (local).** Ollama happily swaps models in and out of GPU /
   unified memory, but a 30 B model is already close to the memory
   budget on most machines — loading a second large model usually OOMs
   the host. So we cap the number of models simultaneously resident
   (`ollama_max_loaded`). If a chat/completions request targets a model
   that is NOT currently loaded and we are already at the budget, we
   refuse fast with a retryable error instead of letting the upstream
   swap crash the box.

2. **External providers** (z.ai, OpenAI, etc.). These have their own
   rate limits; all we do locally is cap concurrency so a bursty client
   cannot open 500 sockets and starve everything else. Excess requests
   queue on a semaphore — they do not fail.

The controller is deliberately small and synchronous in feel: callers
`await acquire(model)`, run their work, and call `token.release()` in a
finally block. The release function is carried on the token so callers
can not confuse which semaphore to return the slot to.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import httpx


class AdmissionDenied(Exception):
    """Raised when the request is refused before reaching the LLM."""

    def __init__(self, message: str, retry_after: int = 5):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class AdmissionToken:
    _release: Callable[[], None]

    def release(self) -> None:
        self._release()


PsFactory = Callable[[], Awaitable[set[str]]]


class AdmissionController:
    def __init__(
        self,
        ollama_max_loaded: int = 1,
        external_max_concurrent: int = 10,
        ollama_url: str = "http://localhost:11434/v1",
        ps_client_factory: Optional[PsFactory] = None,
    ):
        self.ollama_max_loaded = max(1, int(ollama_max_loaded))
        self.external_max_concurrent = max(1, int(external_max_concurrent))
        self._ollama_sem = asyncio.Semaphore(self.ollama_max_loaded)
        self._external_sem = asyncio.Semaphore(self.external_max_concurrent)
        self._ollama_check_lock = asyncio.Lock()

        base = ollama_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        self._ollama_base = base.rstrip("/")
        self._ps_client_factory = ps_client_factory

    @staticmethod
    def is_ollama_model(model: str) -> bool:
        return bool(model) and ":" in model

    async def _currently_loaded(self) -> set[str]:
        try:
            if self._ps_client_factory is not None:
                return await self._ps_client_factory()
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self._ollama_base}/api/ps")
            if r.status_code != 200:
                return set()
            return {
                m.get("name", "")
                for m in r.json().get("models", [])
                if m.get("name")
            }
        except Exception:
            # Fail-open: a transient ollama-side problem must not turn
            # into a full gateway outage. Worst case, one extra request
            # makes it through while ollama is already overloaded —
            # which it was going to reject anyway.
            return set()

    async def acquire(self, model: str) -> AdmissionToken:
        if self.is_ollama_model(model):
            async with self._ollama_check_lock:
                loaded = await self._currently_loaded()
                if model not in loaded and len(loaded) >= self.ollama_max_loaded:
                    raise AdmissionDenied(
                        f"ollama at capacity: {len(loaded)}/{self.ollama_max_loaded} "
                        f"models loaded. Refusing to swap in '{model}' "
                        f"(would exceed memory budget).",
                        retry_after=5,
                    )
                await self._ollama_sem.acquire()
                return AdmissionToken(_release=self._ollama_sem.release)

        await self._external_sem.acquire()
        return AdmissionToken(_release=self._external_sem.release)
