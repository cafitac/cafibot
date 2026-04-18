# Security Architecture

Security design principles and implementation strategy for serving local LLMs on Mac Studio.

---

## Isolation Layers

Security for LLM-based agents is divided into two layers.

### Layer 1 — Model Alignment (Soft)
- Training/prompts guide the model to refuse dangerous requests
- Imperfect — vulnerable to prompt injection and jailbreak attempts
- Trust only as a supplementary measure

### Layer 2 — Infrastructure Isolation (Hard)
- Structurally blocks access itself
- Whatever the model generates, the execution environment is restricted
- **Design this layer first**

```
[LLM Inference Server]   → Token generation only, no shell access
[Tool Executor]          → Only allowed tools, only validated paths
[Path validation]        → `_is_safe_path(cwd)` guards every file op
[Host Firewall]          → Minimized port exposure
```

---

## Network Isolation

### ollama Binding
```bash
# Default: exposes all interfaces (dangerous)
# OLLAMA_HOST=0.0.0.0:11434

# Recommended: localhost only
OLLAMA_HOST=127.0.0.1:11434
```

If you need to expose externally, do not expose ollama directly; place it behind an authentication proxy:
```
Internet → nginx (HTTPS + API key verification) → ollama (127.0.0.1)
```

### VPN / SSH Tunneling
When external access is needed, SSH tunneling is recommended over directly exposing ports:
```bash
# From a friend's machine
ssh -L 11434:localhost:11434 user@mac-studio.local
```

---

## Filesystem Isolation

### Path Validation (`_is_safe_path`)
All HermitAgent file tools block access outside allowed paths:
```python
def _is_safe_path(path: str, cwd: str) -> bool:
    # Only allow paths under cwd, /tmp, and allowed home directory paths
    # Must pass the actual cwd (including worktree paths)
```

---

## Tool Execution Restrictions

### BashTool Dangerous Command Blocklist
```python
DANGEROUS_PREFIXES = [
    "sudo ", "rm -rf /", "mkfs", "dd if=",
    "> /dev/", "chmod 777", "curl | sh", "wget | bash",
]
```

### Permission Request Flow
Sensitive operations (bash, write_file, etc.) require user approval before execution:
```
HermitAgent → ask_user_question(permission request) → CC session → User approval → Execute
```
`yolo` mode is only allowed for trusted users.

---

## Audit Logging

Log all tool executions for post-incident traceability.

Current implementation: `~/.hermit/mcp_server.log`
```
[07:16:38] ⏺ bash(find /path -name "*.py" ...)
[07:16:53]   ⎿  result...
```

### Additional Recommendations for Mac Studio Serving
- Record `user_id`, `task_id`, `timestamp` per request
- Anomaly detection: bulk file access or external network requests in a short time
- Set log retention period (e.g., 30 days)

---

## API Authentication

### Token-Based Authentication
```json
// ~/.hermit/server/tokens.json
{
  "tokens": {
    "abc123": {"user": "friend1", "created": "2026-09-01", "expires": "2027-09-01"},
    "def456": {"user": "friend2", "created": "2026-09-01", "expires": null}
  }
}
```

### Rate Limiting
```python
# 1 concurrent task per user + hourly request limit
MAX_CONCURRENT_PER_USER = 1
MAX_REQUESTS_PER_HOUR = 20
```

---

## Threat Model Summary

| Threat | Likelihood | Response Layer |
|--------|------------|----------------|
| Dangerous command execution via prompt injection | Medium | Infrastructure (blocklist + permission requests) |
| Unauthorized API access | Medium | Authentication tokens + firewall |
| Filesystem escape | Low | `_is_safe_path(cwd)` validation on every file-path tool |
| Direct attack on LLM server | Low | 127.0.0.1 binding + proxy front-end |
| Network eavesdropping | Low | HTTPS/WSS required |
| Excessive GPU usage | Medium | Concurrent connection limits + token quotas |
