-- HermitAgent Gateway initial schema
-- token_usage: LLM token usage tracking
-- api_keys: Gateway API key management

CREATE TABLE IF NOT EXISTS token_usage (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user              TEXT    NOT NULL,
    task_id           TEXT    NOT NULL UNIQUE,
    model             TEXT    NOT NULL DEFAULT '',
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    duration_ms       INTEGER NOT NULL DEFAULT 0,
    status            TEXT    NOT NULL DEFAULT 'done',
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_usage_user_date ON token_usage(user, created_at);

CREATE TABLE IF NOT EXISTS api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key    TEXT    NOT NULL UNIQUE,
    user       TEXT    NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
