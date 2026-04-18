#!/usr/bin/env bun
/**
 * ollama-proxy — Ollama OpenAI API auth proxy
 *
 * Features:
 *   - Bearer token authentication (block unauthorized access)
 *   - Concurrent connection limit (memory protection — qwen3 fixed at 18GB)
 *   - Transparent forwarding for Ollama OpenAI-compatible API (including streaming)
 *
 * Environment variables:
 *   PROXY_API_KEYS     — Allowed API keys (comma-separated). e.g. "key1,key2"
 *   PROXY_PORT         — Proxy listen port (default: 11435)
 *   PROXY_MAX_CONCURRENT — Max concurrent requests (default: 1)
 *   OLLAMA_URL         — Ollama server address (default: http://127.0.0.1:11434)
 *
 * Usage for friends:
 *   HERMIT_LLM_URL=http://YOUR_IP:11435/v1 \
 *   HERMIT_API_KEY=your-key \
 *   hermit_agent "message"
 */

// ── Configuration ──────────────────────────────────────────────────────────────

const PORT = parseInt(process.env.PROXY_PORT ?? "11435");
const OLLAMA_URL = (process.env.OLLAMA_URL ?? "http://127.0.0.1:11434").replace(/\/$/, "");
const MAX_CONCURRENT = parseInt(process.env.PROXY_MAX_CONCURRENT ?? "1");

const ALLOWED_KEYS = new Set(
  (process.env.PROXY_API_KEYS ?? "")
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean)
);

if (ALLOWED_KEYS.size === 0) {
  console.error("[ollama-proxy] Warning: PROXY_API_KEYS not set — allowing all requests");
}

// ── Concurrency semaphore ──────────────────────────────────────────────────────

let activeCount = 0;
const waitQueue: Array<() => void> = [];

function acquire(): Promise<void> {
  if (activeCount < MAX_CONCURRENT) {
    activeCount++;
    return Promise.resolve();
  }
  return new Promise((resolve) => waitQueue.push(resolve));
}

function release(): void {
  const next = waitQueue.shift();
  if (next) {
    next(); // wake the next queued request
  } else {
    activeCount--;
  }
}

// ── Authentication ──────────────────────────────────────────────────────────────

function isAuthorized(req: Request): boolean {
  if (ALLOWED_KEYS.size === 0) return true; // allow all when no keys configured

  const auth = req.headers.get("Authorization") ?? "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  if (!match) return false;

  return ALLOWED_KEYS.has(match[1].trim());
}

// ── Proxy ──────────────────────────────────────────────────────────────────────

async function proxyToOllama(req: Request, path: string): Promise<Response> {
  const targetUrl = `${OLLAMA_URL}${path}`;

  const headers = new Headers(req.headers);
  // Strip auth header before forwarding to Ollama (internal communication)
  headers.delete("Authorization");
  headers.set("Host", new URL(OLLAMA_URL).host);

  const upstreamReq = new Request(targetUrl, {
    method: req.method,
    headers,
    body: req.body,
    // @ts-ignore — Bun-specific
    duplex: "half",
  });

  try {
    const upstream = await fetch(upstreamReq);

    // Pass streaming response through as-is
    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return new Response(
      JSON.stringify({ error: { message: `Ollama connection failed: ${msg}`, type: "proxy_error" } }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

// ── HTTP server ────────────────────────────────────────────────────────────────

Bun.serve({
  port: PORT,

  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url);

    // Health check (no auth required)
    if (req.method === "GET" && url.pathname === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          port: PORT,
          ollama: OLLAMA_URL,
          active: activeCount,
          max: MAX_CONCURRENT,
          queue: waitQueue.length,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // Check authentication
    if (!isAuthorized(req)) {
      return new Response(
        JSON.stringify({ error: { message: "Unauthorized", type: "auth_error" } }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    }

    // Allow only OpenAI-compatible paths
    const allowedPaths = ["/v1/chat/completions", "/v1/models", "/v1/embeddings"];
    if (!allowedPaths.some((p) => url.pathname.startsWith(p))) {
      return new Response(
        JSON.stringify({ error: { message: "Not found", type: "not_found" } }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    // Concurrency limit (acquire semaphore)
    await acquire();
    try {
      return await proxyToOllama(req, url.pathname + url.search);
    } finally {
      release();
    }
  },
});

console.error(
  `[ollama-proxy] Started — port:${PORT}, ollama:${OLLAMA_URL}, max:${MAX_CONCURRENT}, keys:${ALLOWED_KEYS.size}`
);
