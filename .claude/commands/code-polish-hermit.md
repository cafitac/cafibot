# /code-polish-hermit — state-machine polish loop

Unlike `/code-polish`, this variant is a **distributed state machine**.
Hermit runs its own review-and-apply loop until it is self-clean, and
Claude provides two independent review passes on top as a quality gate.
Claude's token spend is capped at ~2 review rounds.

## Arguments

`$ARGUMENTS` — PR number (required).

- `--strategy {aggressive|moderate|conservative}` — delegation depth.
  If omitted, read from the model-strategy map in the checkpoint
  config (same mechanism as `/feature-develop-hermit`).

## Prerequisites

- Hermit gateway + MCP server running.
- Valid PR branch / worktree resolved.
- Project's test runner works (Hermit will invoke it).

## State machine

```
HERMIT_LOOP          ← Hermit self-reviews and fixes until clean
     ↓
CC_REVIEW_1          ← Claude review pass 1
     │               ↓ findings? ←─────┐
     │                                 │
     └── clean ──→ CC_REVIEW_2         ↑
                        │              │
                        ↓              │
                     clean             │
                        ↓              │
                      DONE             │
                                       │
              findings? ──→ HERMIT_LOOP (iteration+1)
```

The loop terminates when **two Claude review passes back to back are
clean**, or the global iteration limit (5) is hit, or Hermit fails
three times in a row.

## Workflow

### Step 1 — lock

```bash
mkdir -p .hermit
cat > .hermit/active-task.lock <<EOF
{
  "task_id": "<filled-after-run_task>",
  "started_at": "$(date -Iseconds)",
  "skill": "code-polish-hermit",
  "state": "HERMIT_LOOP",
  "iteration": 0,
  "pr": "$ARGUMENTS"
}
EOF
```

### Step 2 — state HERMIT_LOOP (initial entry)

`mcp__hermit__run_task(cwd=<worktree>, background=true, model=<--model or "">)`

```
You are Hermit. Polish PR #<PR-number> to your own "first clean" state.

Loop (max 5 internal iterations):
1. Self-review the PR diff against the project's review criteria.
   Output Pn findings.
2. If findings are empty → STOP and report `self_clean: true`.
3. Otherwise, apply every finding.
4. Re-run the review.
5. Repeat.

Rules:
- TDD: every code change updates or adds tests; confirm the test
  runner passes before closing an iteration.
- Preserve existing behaviour — never silently drop validation,
  error handling, or cleanup.
- Do NOT commit or push.
- Stay in scope: touch only files in this PR's diff (or the
  refactoring targets listed in `.omc/plans/<branch>-patterns.md`
  if it exists).
- Ambiguous fix direction → call ask_user_question.

Completion:
- self_clean: true, OR internal iteration limit reached.
- Return: final state, iterations used, files modified.
```

**Re-entry prompt** (Claude found more issues):

```
You are Hermit. Resume polish on PR #<PR-number>. Claude's review pass
flagged remaining issues.

New findings:
<Claude review output — Pn list>

Apply these findings, then run your own review loop until self-clean.
Same rules as before. Return when self_clean.
```

Register the returned `task_id` with `mcp__hermit-channel__register_task`
and update the lock with `state` and `iteration`.

### Step 3 — wait and transition

- `status == "done"` → set lock `state = CC_REVIEW_1` → Step 4.
- `status == "failed"` or `self_clean: false` after limit →
  report to the user, offer retry / Claude takeover / cancel.

### Step 4 — state CC_REVIEW_1

Claude runs `/code-review $ARGUMENTS` (or the project's review
subagent). Evaluates findings:

- **No P1/P2/P3** → lock `state = CC_REVIEW_2` → Step 5.
- **P1/P2/P3 present** → save findings to
  `.omc/reviews/<branch>-polish-r1.md`, set lock
  `state = HERMIT_LOOP`, `iteration += 1` → Step 2 (re-entry prompt).

### Step 5 — state CC_REVIEW_2 (regression gate)

Same review, one more time. If it's clean too → Step 6 (DONE). If not,
loop back to Step 2.

The point of two back-to-back clean passes is to catch regressions
that only surface on a fresh read.

### Step 6 — DONE

1. Run the project's test runner in a `run_in_background` subagent.
   Failure aborts Step 6 — report, do not push.
2. Suggest the next step: `/code-push-hermit $ARGUMENTS` (recommended)
   or `/code-push $ARGUMENTS`.
3. Delete `.hermit/active-task.lock`.

### Repeated-pattern detection (from iteration 3)

If the same P1/P2 finding type appears in 3+ Claude review passes,
offer to turn it into a reusable learning skill:

1. Summarise the pattern.
2. Ask the user: "\[learn]: the '{name}' P2 finding has recurred N
   times — save as a skill?"
3. On approval, write `~/.claude/skills/learned-feedback/feedback_<name>.md`.
4. Inject the new skill's path into subsequent Hermit prompts.

## Termination conditions

1. **CC_REVIEW_1 + CC_REVIEW_2 both clean** → DONE.
2. **HERMIT_LOOP hit the global 5-iteration cap** → forced stop;
   Claude takeover or manual work.
3. **Hermit failed three times in a row** → hard stop; user must
   intervene.

## Output format

On every state transition:

```
## [state: <name>, iteration N]

### Hermit loop result
- self_clean: true (3 internal iterations)
- files modified: 5

### Claude review pass 1
- P1: 0, P2: 1, P3: 0
- finding: `apps/loan/service.py:42` — resource cleanup missing

→ HERMIT_LOOP re-entered (iteration 2)
```

Final:

```
## /code-polish-hermit complete

- Total iterations: Hermit N, Claude review M
- Final review: P1=0, P2=0, P3=0 (two consecutive clean passes)
- Tests: pass
- Next: /code-push-hermit $ARGUMENTS
```

## Safety rules

- No Hermit call without a lock.
- No Claude edits while the lock exists.
- Refuse to run if there is nothing to review.
- Hermit never commits or pushes.
- Out-of-scope changes are auto-reverted.
- **No compound shell commands**: use `git -C <path> ...`.
