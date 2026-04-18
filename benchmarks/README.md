# HermitAgent benchmarks

Reproducible task specs for measuring Claude-side cost savings from
`-hermit` skill variants. Anyone who clones the repo can run the same
task twice (once with `/feature-develop`, once with `/feature-develop-hermit`)
and contribute a datapoint.

## Tasks

| Directory | Summary |
|---|---|
| [`todo-api/`](./todo-api) | Extend a minimal FastAPI todo starter with list-with-filter, PATCH, and DELETE endpoints plus tests. ~20-30 min for pure Claude Code. |

More tasks welcome — refactor-style, bug-fix-style, etc.

## Running a comparison

See `docs/measure-savings.md` for the full protocol. Short version:

```bash
# 1. Copy the starter twice — one per run. Fresh working tree each time.
cp -r benchmarks/todo-api/starter /tmp/cc-run
cp -r benchmarks/todo-api/starter /tmp/cc-hermit-run

# 2. Run A — pure Claude Code
claude /tmp/cc-run
  /feature-develop         $(cat benchmarks/todo-api/TASK.md)
  /cost                    # note the session path shown by Claude Code

# 3. Run B — with Hermit delegation
claude /tmp/cc-hermit-run
  /feature-develop-hermit  $(cat benchmarks/todo-api/TASK.md)
  /cost

# 4. Diff the two sessions
scripts/measure-savings.sh \
  --session-a ~/.claude/projects/<proj>/<session-A>.jsonl \
  --session-b ~/.claude/projects/<proj>/<session-B>.jsonl
```

The script prints a markdown table you can paste into `results/`.

## Submitting a result

If you want to contribute a datapoint, add a file under `results/`:

```
benchmarks/results/YYYY-MM-DD-<handle>-<task>-<executor>.md
```

Template:

```markdown
# todo-api — 2026-05-01 — @alice — ollama qwen3-coder:30b

| ...measure-savings.sh table pasted here... |

## Environment
- CC model: claude-sonnet-4-5
- Executor: ollama qwen3-coder:30b (M3 Max)
- Hardware: MacBook Pro M3 Max 64 GB
- Hermit version: 0.1.0

## Notes
- Run B needed one clarifying reply during the interview (fine).
- Both runs ended with all tests passing.
```

Three or more independent datapoints for the same executor let us put
a defensible percentage in the README. Regressions are valuable too —
please submit them.

## Why not time?

See `docs/measure-savings.md`. Short answer: wall-clock depends on the
executor model's speed, which is orthogonal to the Claude-bill story
this project is about. A well-measured time benchmark is a welcome
separate contribution, but not a precondition for cost numbers.
