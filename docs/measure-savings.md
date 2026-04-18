# Measuring real Claude-side cost savings

The numbers in the README should come from real runs, not vibes. This
document is the protocol.

## What we measure (and why we stop there)

Only one thing: **Claude-side tokens and their USD cost**.

We deliberately ignore:

- **Executor cost.** Hermit runs on ollama (free) or a flat-rate z.ai /
  GLM subscription. Either way it does not scale per-token the way
  Claude billing does. For budgeting purposes, treat it as `$0`.
- **Wall-clock time.** A local 30B model is slower per token than
  Claude. If you want that number, measure it separately — it is not
  the story the Claude bill tells.

So every number below is answering one question: *how many Claude tokens
and dollars did this session spend?*

## Data sources

| Metric | Where it lives |
|---|---|
| Claude input / output tokens | Claude Code session JSONL: `~/.claude/projects/<project>/<session>.jsonl`, `usage.input_tokens` / `usage.output_tokens` on every assistant message |
| Claude cache read / create   | same JSONL, `usage.cache_read_input_tokens` / `usage.cache_creation_input_tokens` |
| Claude cost                  | tokens × model list price (default: Sonnet 4 — \$3/1M in, \$15/1M out; override per-model with flags) |

Pricing is a moving target. The script takes `--claude-price-in` /
`--claude-price-out` so you can pin the rate used for a run.

## Protocol (pairwise)

Use the benchmark task so both runs do exactly the same work.

```bash
# prep two fresh copies of the starter
cp -r benchmarks/todo-api/starter /tmp/cc-run
cp -r benchmarks/todo-api/starter /tmp/cc-hermit-run

# run A — pure Claude Code
claude /tmp/cc-run
  /feature-develop   $(cat benchmarks/todo-api/TASK.md)
  /cost              # capture input/output tokens + cost

# run B — with Hermit delegation
claude /tmp/cc-hermit-run
  /feature-develop-hermit   $(cat benchmarks/todo-api/TASK.md)
  /cost              # capture input/output tokens + cost
```

Both runs must:

- Start from an identical starter copy.
- Use the same Claude model (don't switch between sonnet and opus
  mid-comparison).
- End with passing tests (`pytest`) — a run that skipped the work is
  not a comparable datapoint.

## Running the analyzer

Find the two Claude Code session JSONLs (`~/.claude/projects/...`) and
pass them to the script:

```bash
scripts/measure-savings.sh \
  --session-a ~/.claude/projects/<proj>/<session-A>.jsonl \
  --session-b ~/.claude/projects/<proj>/<session-B>.jsonl \
  [--claude-price-in 3.0] [--claude-price-out 15.0]
```

It prints a markdown table ready to paste into the README:

```
|                        | Pure Claude Code | CC + Hermit | Δ    |
|------------------------|-----------------:|------------:|-----:|
| Claude input tokens    | ...              | ...         | ...  |
| Claude output tokens   | ...              | ...         | ...  |
| Claude cache read      | ...              | ...         | —    |
| Claude-side cost       | $x.xx            | $y.yy       | -Z%  |
```

## Minimum dataset before publishing a percentage

One pair is suggestive, not evidence. Target before updating the
README with a marketing number:

- **3 pairs** minimum — different task types if possible (feature,
  refactor, bug fix). Store the raw rows under `benchmarks/results/`.
- **Per-executor rows** if you support more than one executor
  (ollama qwen3-coder, z.ai glm-5.1, …) — a well-performing local
  model is a different claim than a cloud API.
- **Include regressions.** Runs where Hermit spent *more* Claude
  tokens (often: extra clarifying questions, failed delegation that
  Claude had to recover from) belong in the dataset too. They stop
  the published number from being cherry-picked.

## What not to claim

- "Up to X% savings" without listing the ticket / task type.
- A percentage from a single run.
- Savings from a run where Hermit failed and Claude took over —
  that is a Claude session with extra overhead, not a win.

The honest framing:

> Across N runs of the todo-api benchmark task with `<executor>` as
> Hermit, `/feature-develop-hermit` used **X% fewer Claude tokens**
> than `/feature-develop`. Raw data: `benchmarks/results/`.
