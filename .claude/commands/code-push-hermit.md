# /code-push-hermit — Claude writes the PR prose, Hermit does the git work

Commit-and-push are the textbook grunt-work target: short, mechanical,
deterministic, and unrelated to reasoning. This skill keeps the
*deciding* parts in Claude and delegates the `git` commands to Hermit.

## Arguments

`$ARGUMENTS` — PR number (required for the PR description update step;
the commit+push works without it).

- `--model <model_name>` — executor model override.

## Prerequisites

- Clean or stageable working tree with actual changes.
- Hermit gateway + MCP server running.
- `gh` CLI authenticated if you want the PR-description step.

## Workflow

### Step 1 — pre-flight (Claude)

- `git status --porcelain` in the worktree — confirm changes exist.
- Refuse if the branch is `main` or `develop`.
- Scan staged and unstaged files for sensitive names (`.env`,
  `*.pem`, `*.key`, `credentials*`). If any are present, report and
  stop — ask the user whether to add them to `.gitignore`.
- Read the last few commits to learn the project's message style
  (length, prefix conventions, language).

### Step 2 — lock

```bash
mkdir -p .hermit
cat > .hermit/active-task.lock <<EOF
{
  "task_id": "<filled-after-run_task>",
  "started_at": "$(date -Iseconds)",
  "skill": "code-push-hermit",
  "pr": "$ARGUMENTS",
  "cwd": "<worktree_path>"
}
EOF
```

### Step 3 — delegate commit + push to Hermit

`mcp__hermit__run_task(cwd=<worktree>, background=true, model=<--model or "">)`

```
You are Hermit. Commit and push the pending changes in this worktree
for PR #<PR-number>.

Context:
- Branch: <branch>
- PR title: <title>
- Changed files (already reviewed by Claude and confirmed in scope):
  <file list>

Rules:
1. Safety:
   - Refuse if the branch is main or develop.
   - Never stage .env, *.pem, *.key, credentials*.
   - Use `git -C <worktree> ...` (no `cd && git ...`).
2. Match the project's commit-message style — read
   `git log --oneline -5`. Prefix convention, length, language.
3. Split the changes into logical commits if they span multiple
   concerns (e.g. refactor + feat).
4. Per commit:
   - `git add` only the relevant files (never `-A` / `.`).
   - One conventional-prefix message (fix/feat/refactor/chore/test).
   - Do NOT add Co-Authored-By or AI attribution lines.
5. Push: `git push`, or `git push -u origin <branch>` if the branch
   has no upstream yet.

Return: commit list (short hash + message), push result, anything
skipped with a reason.

Do NOT:
- Edit the PR description — Claude does that.
- Create commits for files outside the current PR diff.
- Update external ticket systems.

Obey HERMIT.md, .hermit/rules/, and .claude/rules/.
```

Register the `task_id` and update the lock.

### Step 4 — monitor

- `waiting` → relay Hermit's question (e.g. "branch is
  `main`, refuse?") to the user; reply via `reply_task`.
- `done` → Step 5.
- `failed` → report, offer retry / Claude takeover / cancel.

### Step 5 — PR description update (Claude)

Using the commit summary Hermit returned and the existing PR
description:

1. Read the project's PR template if one exists
   (`~/.claude/templates/pr-description.md`,
   `.github/PULL_REQUEST_TEMPLATE.md`, or similar).
2. Write an updated description in the project's conventional
   language and structure.
3. `gh pr edit $ARGUMENTS --body "$(cat <<'EOF' … EOF)"`.

### Step 6 — external tracker sync (optional, Claude)

If the project uses an external tracker (Jira, Linear, etc.), and the
branch or PR title contains a recognizable ticket ID, let Claude
update the ticket in the project's standard way. Leave the exact
command to the project's conventions — no built-in assumption here.

### Step 7 — release the lock

1. Delete `.hermit/active-task.lock`.
2. Report:

```
## /code-push-hermit complete

- Branch: <branch>
- Commits (by Hermit):
  - `abc1234` fix: ...
  - `def5678` feat: ...
- PR: #$ARGUMENTS description updated (Claude)
- Tracker: <ticket> description + progress comment added (Claude)
```

## Safety rules

- **No push to `main` or `develop`** — enforced both in Claude's
  pre-flight and in Hermit's prompt.
- **No sensitive files** ever staged — enforced in both places plus
  the permissions floor.
- **No Co-Authored-By or AI-attribution lines** in commit messages —
  enforced in Hermit's prompt.
- **Abort on empty diff** — if Step 1 sees nothing to commit, exit
  cleanly instead of creating empty commits.
- **No compound shell commands** — `git -C <path> ...`.

## Difference vs pure `/code-push`

| Item | `/code-push` | `/code-push-hermit` |
|---|---|---|
| Pre-flight checks | Claude | Claude (same) |
| PR split decision | Claude | Claude (same) |
| **Commit messages** | Claude subagent | **Hermit** |
| **git push** | Claude subagent | **Hermit** |
| PR description | Claude subagent | Claude (direct) |
| Tracker sync | Claude subagent | Claude (direct) |
| Claude tokens | medium | low (commit/push is the hot spot) |
