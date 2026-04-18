# The `-hermit` skill variants

> **The bundled `-hermit` skills are examples, not the product.** The product is the pattern: Claude does reasoning and final quality gates, a cheap executor does the grunt work. Four reference variants ship with the repo so you can see the pattern in action and fork them into whatever workflow you already use.

The spectrum this project sits on:

| Mode | Claude does | Executor does |
|---|---|---|
| Pure Claude Code | everything | nothing |
| **`-hermit` variants (bundled)** | interview + plan review + final verification | implementation, tests, edits, commits |
| Aggressive future variants | final QC only | interview, plan, implementation, tests, commits |

The less Claude does, the cheaper the session. The bundled variants are the conservative checkpoint — they still let Claude own the interview phase. Custom variants can push further.

## The pattern

```
/some-skill          → Claude does everything end-to-end
/some-skill-hermit   → Claude handles:  interview, plan, review, decision
                       Hermit handles:  file edits, tests, formatters, commits, pushes
```

Claude only sees Hermit's final summary (MCP result truncation, head 2000 + tail 1000 by default). The middle — 40+ Read/Edit/Bash rounds — never hits the Claude context.

## Reference variants that ship in this repo

These are **examples to read and fork**. Savings percentages are illustrative — real numbers live under `benchmarks/results/` (see [docs/measure-savings.md](measure-savings.md) for the protocol).

| Command | Who does what |
|---|---|
| `/feature-develop-hermit <ticket-or-task>` | Claude interviews you, writes the spec and acceptance criteria. Hermit implements, runs tests, iterates until green. |
| `/code-apply-hermit <pr-review>` | Claude reads the PR review comments and sequences them. Hermit applies every suggestion one by one. |
| `/code-polish-hermit` | Claude picks what to polish (naming, dead code, error paths). Hermit runs the lint/test loop until clean. |
| `/code-push-hermit` | Claude writes the PR title and description from the diff summary. Hermit does `git commit`, `git push`, and the `gh pr create` call. |

Savings come from routing grunt-work tool output away from Claude's context, not from the executor being smarter than Claude.

## Why split the work this way

Claude is best at:
- Understanding a vague ticket and asking the right clarifying questions
- Writing prose (PR descriptions, commit messages, design notes)
- Noticing that a proposed change is bad or risky

The local/cheap executor is good enough at:
- `Read` → `Edit` → `Bash(pytest)` loops
- Applying a concrete list of review suggestions line by line
- Running formatters and linters until they stop complaining
- Mechanical git/gh operations

You pay Claude-level prices only for Claude-level work.

## Anatomy of a variant

All four follow the same three-step protocol:

1. **Claude interview** (short, stays in Claude context)
   - Slash command handler asks you for a ticket, a PR review URL, or approves the intent
   - Writes a one-screen plan to `.omc/plans/<name>.md`
2. **Delegation** via `mcp__hermit__run_task`
   - The plan text becomes the task prompt
   - `check_task` polls for progress (or the `hermit-channel` push surfaces events immediately)
3. **Claude summary** (short, back in Claude context)
   - Hermit returns a truncated result
   - Claude reports back to you in one paragraph: what changed, what's next, what to review

If something during step 2 needs a judgment call, Hermit calls `reply_task` with a question; you answer inside the Claude Code session and Hermit resumes. No context hand-off loss.

## When **not** to use a `-hermit` variant

- Investigative work where the model has to reason across the output of many commands (`/trace`, deep debugging). Keep Claude in the loop — context awareness matters more than cost.
- One-shot fixes that fit in five tool calls. Delegation overhead eats the saving.
- Anything where you want to watch every step and may interrupt. The UX is smoother in pure Claude for that.

## Write your own variant (the expected path)

Any slash command you use can get a `-hermit` counterpart. That is where the real wins are — your workflow is not identical to the bundled one.

Recipe:

1. Identify the Claude-intensive step in your current skill. If it looks like "read N files → edit → run tests → repeat", that's the delegation target.
2. Copy `.claude/commands/<skill>.md` to `<skill>-hermit.md`.
3. Rewrite the body: keep the Claude-side steps concise (interview, decision, review, summary), and replace the execution block with `mcp__hermit__run_task(<plan-prompt>)`.
4. End with a short summary step that reads Hermit's truncated result and reports back.

Keep the Claude side under ~15 tool calls. If you notice it creeping up (frequent `Read` to re-anchor on files), push more context into the initial delegation prompt instead of fetching it in Claude.

**Pushing further**: once you trust the delegation, move more phases into the Hermit prompt. A skill that currently does "interview in Claude → delegate the rest" can become "delegate the interview too, Claude just does a final accept/reject". The four bundled variants are the conservative starting point.

## Measuring your own savings

Before and after a `-hermit` session, run:

```
/cost
```

In Claude Code, the `/cost` slash command prints session input/output tokens. Take the delta across the two runs of the same task — the difference is what the Hermit executor absorbed.

If you want structured numbers, point the gateway dashboard at `http://localhost:8765/dashboard`; it shows executor tokens per task.
