# HermitAgent Gateway-specific Rules

Applies only to `hermit_agent/gateway/` package.

## Gateway Responsibilities (Included) [P1]

- LLM relay (Ollama/z.ai/OpenAI compatible) — protocol conversion + routing.
- Model routing: name-prefix-based provider selection.
- Token-saving classifier, 429 failover, prompt cache hints, rate limit, auth token management.

## Gateway Responsibilities (Excluded) [P1]

- **No harness primitives** — CLAUDE.md loader, hooks, skills, permissions. These belong in `hermit_agent/` upper layer.
- **No HERMIT.md reading** — Gateway is stateless relay only.
- **No user experience features** — progress rendering, session saving, UI prompts.

## Error Handling [P1]

### 429 / Rate Limit
- On first attempt failure: short backoff then immediate failover. Avoid long backoff (looks like a hang). max_retries 3, timeout 120s.

### 5xx
- 1 retry with same provider → failover on failure. Log provider_id, request_id, status_code.

## Configuration Management [P2]

- All env vars read from `hermit_agent/gateway/config.py`. No hardcoded URLs/keys.
- New provider: (1) `LLMClientBase` impl, (2) name-prefix mapping, (3) document in `.env.example`.

## Testing [P2]

- No real network calls — mock httpx/requests.
- Test 429/5xx/timeout paths. Follow patterns in `tests/test_llm_retry.py`, `test_llm_timeout.py`, `test_model_routing.py`.
