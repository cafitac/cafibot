"""Automatic sub-agent system — Claude Code's builtInAgents + OMC pattern.

Automatically spawns specialized agents under certain conditions:
- After code changes → auto review
- Explore request → auto Explore Agent
- Planning request → auto Plan Agent
- Error occurred → auto debugger
- Task completed → auto verification
- Context exceeded → auto compaction (already implemented in context.py)
- Conversation ended → auto memory extraction (already implemented in loop.py)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class AutoAgentType(Enum):
    EXPLORE = "explore"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    PLANNER = "planner"
    VERIFIER = "verifier"


@dataclass
class AutoAgentConfig:
    """Auto-agent configuration."""
    enabled: bool = True
    auto_review: bool = True       # Auto review after code changes
    auto_explore: bool = True      # Auto explore on search requests
    auto_plan: bool = True         # Auto planning on plan requests
    auto_debug: bool = True        # Auto debug on errors
    auto_verify: bool = False      # Auto verify after task completion (default off, high cost)
    review_threshold: int = 3      # Trigger review after N file changes
    verify_cooldown_turns: int = 5  # Skip re-verify within N turns of previous verify
    max_auto_agents: int = 3       # Limit on concurrent auto-agents


@dataclass
class AutoAgentResult:
    agent_type: AutoAgentType
    triggered: bool
    result: str = ""
    files_reviewed: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Builtin agent system prompts (matching builtInAgents.ts pattern)
# ---------------------------------------------------------------------------

EXPLORE_SYSTEM_PROMPT = (
    "You are an Explore Agent. Read-only mode. Search and find code patterns. "
    "Do NOT modify any files. Use glob, grep, and read_file to locate relevant "
    "code and return a concise, structured summary of what you found."
)

PLAN_SYSTEM_PROMPT = (
    "You are a Plan Agent. Analyze the codebase and create a step-by-step "
    "implementation plan. Read-only mode — do NOT modify any files. "
    "Produce a numbered, actionable plan with file references."
)

REVIEWER_SYSTEM_PROMPT = (
    "You are a Code Reviewer Agent. Review changed files for correctness, "
    "error handling, edge cases, and style consistency. "
    "Rate issues as P1 (must fix), P2 (should fix), or P3 (nice to have). "
    "Be concise. Reference file:line."
)

DEBUGGER_SYSTEM_PROMPT = (
    "You are a Debugger Agent. Analyze errors and identify root causes. "
    "Read relevant source files, pinpoint the problem, and suggest a specific "
    "fix with file, line, and the exact change required."
)

VERIFIER_SYSTEM_PROMPT = (
    "You are a strict verification agent. Do not assume — verify by execution. "
    "Use ALL available tools: read_file to check code, bash to run tests/commands, glob/grep to locate files. "
    "For execution criteria (tests pass, server starts, import works): actually RUN the command and inspect output. "
    "If a criterion says 'tests pass' but import errors exist, it FAILS. "
    "Report every finding with evidence (file:line, command output). "
    "The first line of your final reply MUST be exactly `VERDICT: PASS` or `VERDICT: FAIL`."
)

TEST_ENGINEER_SYSTEM_PROMPT = (
    "You are a Test Engineer Agent. Your job is to write high-quality tests. "
    "Analyze the code under test, identify edge cases, normal paths, and error paths. "
    "Write pytest-style tests. Mock only external dependencies (HTTP, external APIs). "
    "Do NOT mock internal DB, models, services, or QuerySets — use real objects. "
    "Follow TDD: write the failing test first, then verify it passes after implementation."
)

# ---------------------------------------------------------------------------
# Prompt templates (filled at runtime)
# ---------------------------------------------------------------------------

EXPLORE_PROMPT = """You are an Explore Agent. Your job is to quickly search and find relevant code.
Read-only mode: do NOT modify any files.

Task: {prompt}

Instructions:
1. Use glob to find relevant files
2. Use grep to search for patterns
3. Use read_file to examine key files
4. Return a concise summary of what you found
"""

PLAN_PROMPT = """You are a Plan Agent. Analyze the codebase and create an implementation plan.
Read-only mode: do NOT modify any files.

Task: {prompt}

Instructions:
1. Use glob/grep/read_file to understand the relevant codebase areas
2. Identify the files that will need to change
3. Produce a numbered, step-by-step implementation plan with file references
"""

REVIEWER_PROMPT = """You are a Code Reviewer Agent. Review the following changes:

Changed files:
{changed_files}

Review each change for:
1. Logic correctness
2. Error handling
3. Edge cases
4. Style consistency

Rate issues as:
- P1: Must fix (bugs, security)
- P2: Should fix (design, missing error handling)
- P3: Nice to have (style, naming)

Be concise. Reference file:line.
"""

DEBUGGER_PROMPT = """You are a Debugger Agent. Analyze this error and suggest a fix:

Error context:
{error_context}

Instructions:
1. Read the relevant source files
2. Identify the root cause
3. Suggest a specific fix (file, line, change)
"""

VERIFIER_PROMPT = """Verify that the recent changes actually work — by execution, not assumption.

Task that was performed:
{task_description}

Checks to perform (all):
1. Syntax/import: `python -c "import <module>"` or `node -e "require(...)"` — fail if error
2. Tests: run the project's test command (pytest, npm test, etc.) and report pass/fail counts
3. Static: read modified files for obvious issues (TODO/FIXME left, unresolved merge markers)
4. Acceptance: if the task mentions specific behavior, exercise it (bash the binary, curl the endpoint)

Output format (strict):
- Line 1: `VERDICT: PASS` or `VERDICT: FAIL`
- Then a short evidence section: each bullet = one check with the command run + observed output summary.
- If FAIL: list the specific failing check(s) first.
"""

# ---------------------------------------------------------------------------
# Verifier output parsing
# ---------------------------------------------------------------------------


_VERDICT_RE = re.compile(r"VERDICT:\s*(PASS|FAIL)\b", re.IGNORECASE)


def parse_verdict(output: str) -> str:
    """Extract VERDICT from Verifier output. Returns 'PASS' / 'FAIL' / 'UNKNOWN'."""
    if not output:
        return "UNKNOWN"
    m = _VERDICT_RE.search(output)
    if not m:
        return "UNKNOWN"
    return m.group(1).upper()


# ---------------------------------------------------------------------------
# Auto-trigger keyword patterns
# ---------------------------------------------------------------------------

_EXPLORE_PATTERNS = re.compile(
    r"search|find|where|grep|locate|look for|show me where",
    re.IGNORECASE,
)

_PLAN_PATTERNS = re.compile(
    r"plan|approach|strategy|how (should|do) (i|we)|design|roadmap",
    re.IGNORECASE,
)

_DONE_PATTERNS = re.compile(
    r"\bdone\b|\bfinished\b|\bcomplete\b",
    re.IGNORECASE,
)


def detect_auto_agent(
    user_message: str,
    assistant_response: str,
) -> AutoAgentType | None:
    """Analyze user message and assistant response to determine which auto agent to trigger.

    Returns the appropriate AutoAgentType or None if no agent should be triggered.

    Trigger priority:
    1. ExploreAgent  — user message contains explore keywords
    2. PlanAgent     — user message contains plan keywords
    3. VerifierAgent — assistant response signals task completion
    """
    if _EXPLORE_PATTERNS.search(user_message):
        return AutoAgentType.EXPLORE

    if _PLAN_PATTERNS.search(user_message):
        return AutoAgentType.PLANNER

    if _DONE_PATTERNS.search(assistant_response):
        return AutoAgentType.VERIFIER

    return None


# ---------------------------------------------------------------------------
# Read-only tool filter helpers
# ---------------------------------------------------------------------------

_READ_ONLY_TOOL_NAMES = frozenset({"read_file", "glob", "grep"})


def _filter_readonly_tools(tools: list) -> list:
    """Return only the read-only subset of a tool list."""
    return [t for t in tools if getattr(t, "name", None) in _READ_ONLY_TOOL_NAMES]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class AutoAgentRunner:
    """Automatic agent runner.

    Checks conditions after AgentLoop tool execution and spawns agents automatically.

    Builtin agent types (matching Claude Code's builtInAgents.ts pattern):
    - ExploreAgent : read-only, triggered by explore keywords in user message
    - PlanAgent    : read-only, triggered by plan/strategy keywords
    - ReviewerAgent: triggered after N file modifications
    - DebuggerAgent: triggered after consecutive errors
    - VerifierAgent: triggered when assistant signals task completion
    """

    def __init__(self, config: AutoAgentConfig | None = None):
        self.config = config or AutoAgentConfig()
        self.modified_files: list[str] = []
        self.error_history: list[str] = []
        self.active_count = 0
        self._review_pending = False
        self.current_turn: int = 0
        self._last_verify_turn: int | None = None

    def note_verify_ran(self, turn: int | None = None) -> None:
        """Record the last turn when verifier ran (used for cooldown calculation)."""
        self._last_verify_turn = turn if turn is not None else self.current_turn

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track_file_change(self, path: str) -> None:
        """Track file changes."""
        if path not in self.modified_files:
            self.modified_files.append(path)

        if len(self.modified_files) >= self.config.review_threshold:
            self._review_pending = True

    def track_error(self, tool_name: str, error: str) -> None:
        """Track errors."""
        self.error_history.append(f"[{tool_name}] {error[:200]}")

    # ------------------------------------------------------------------
    # Trigger predicates
    # ------------------------------------------------------------------

    def should_auto_review(self) -> bool:
        return (
            self.config.enabled
            and self.config.auto_review
            and self._review_pending
            and self.active_count < self.config.max_auto_agents
        )

    def should_auto_debug(self) -> bool:
        return (
            self.config.enabled
            and self.config.auto_debug
            and len(self.error_history) >= 2
            and self.active_count < self.config.max_auto_agents
        )

    def should_auto_explore(self, user_message: str) -> bool:
        return (
            self.config.enabled
            and self.config.auto_explore
            and bool(_EXPLORE_PATTERNS.search(user_message))
            and self.active_count < self.config.max_auto_agents
        )

    def should_auto_plan(self, user_message: str) -> bool:
        return (
            self.config.enabled
            and self.config.auto_plan
            and bool(_PLAN_PATTERNS.search(user_message))
            and self.active_count < self.config.max_auto_agents
        )

    def should_auto_verify(self, assistant_response: str) -> bool:
        if not (self.config.enabled and self.config.auto_verify):
            return False
        if not _DONE_PATTERNS.search(assistant_response):
            return False
        if self.active_count >= self.config.max_auto_agents:
            return False
        if not self.modified_files:
            return False  # skip verifier if no actual changes
        if self._last_verify_turn is not None:
            turns_since = self.current_turn - self._last_verify_turn
            if turns_since < self.config.verify_cooldown_turns:
                return False
        return True

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def get_review_prompt(self) -> str:
        files_str = "\n".join(f"- {f}" for f in self.modified_files)
        return REVIEWER_PROMPT.format(changed_files=files_str)

    def get_debug_prompt(self) -> str:
        errors = "\n".join(self.error_history[-5:])
        return DEBUGGER_PROMPT.format(error_context=errors)

    def get_explore_prompt(self, user_query: str) -> str:
        return EXPLORE_PROMPT.format(prompt=user_query)

    def get_plan_prompt(self, user_query: str) -> str:
        return PLAN_PROMPT.format(prompt=user_query)

    def get_verify_prompt(self, task: str) -> str:
        return VERIFIER_PROMPT.format(task_description=task)

    # ------------------------------------------------------------------
    # Internal runner helper
    # ------------------------------------------------------------------

    def _run_agent(
        self,
        llm,
        cwd: str,
        prompt: str,
        agent_type: AutoAgentType,
        system_prompt: str,
        readonly: bool,
        max_turns: int = 10,
    ) -> AutoAgentResult:
        from .loop import AgentLoop
        from .permissions import PermissionMode
        from .tools import create_default_tools

        self.active_count += 1
        label = agent_type.value.capitalize()
        print(f"\n\033[35m  [Auto-{label}: starting]\033[0m")

        try:
            all_tools = create_default_tools(cwd=cwd)
            tools = _filter_readonly_tools(all_tools) if readonly else all_tools

            agent = AgentLoop(
                llm=llm,
                tools=tools,
                cwd=cwd,
                permission_mode=PermissionMode.YOLO,
                system_prompt=system_prompt,
            )
            agent.MAX_TURNS = max_turns
            agent.streaming = False

            result = agent.run(prompt)
            print(f"\033[35m  [Auto-{label}: done]\033[0m")
            return AutoAgentResult(agent_type=agent_type, triggered=True, result=result)
        except Exception as e:
            return AutoAgentResult(
                agent_type=agent_type,
                triggered=True,
                result=f"{label} failed: {e}",
            )
        finally:
            self.active_count -= 1

    # ------------------------------------------------------------------
    # Public run methods
    # ------------------------------------------------------------------

    def run_auto_review(self, llm, cwd: str) -> AutoAgentResult:
        """Run the auto-review agent."""
        if not self.should_auto_review():
            return AutoAgentResult(agent_type=AutoAgentType.REVIEWER, triggered=False)

        print(f"\n\033[35m  [Auto-Review: {len(self.modified_files)} files changed]\033[0m")
        result = self._run_agent(
            llm=llm,
            cwd=cwd,
            prompt=self.get_review_prompt(),
            agent_type=AutoAgentType.REVIEWER,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            readonly=False,
        )

        reviewed = self.modified_files.copy()
        self.modified_files.clear()
        self._review_pending = False
        result.files_reviewed = reviewed
        return result

    def run_auto_debug(self, llm, cwd: str) -> AutoAgentResult:
        """Run the auto-debugger agent."""
        if not self.should_auto_debug():
            return AutoAgentResult(agent_type=AutoAgentType.DEBUGGER, triggered=False)

        print(f"\n\033[35m  [Auto-Debug: {len(self.error_history)} errors]\033[0m")
        result = self._run_agent(
            llm=llm,
            cwd=cwd,
            prompt=self.get_debug_prompt(),
            agent_type=AutoAgentType.DEBUGGER,
            system_prompt=DEBUGGER_SYSTEM_PROMPT,
            readonly=False,
        )

        self.error_history.clear()
        return result

    def run_auto_explore(self, llm, cwd: str, user_query: str) -> AutoAgentResult:
        """ExploreAgent — read-only codebase search."""
        if not self.should_auto_explore(user_query):
            return AutoAgentResult(agent_type=AutoAgentType.EXPLORE, triggered=False)

        return self._run_agent(
            llm=llm,
            cwd=cwd,
            prompt=self.get_explore_prompt(user_query),
            agent_type=AutoAgentType.EXPLORE,
            system_prompt=EXPLORE_SYSTEM_PROMPT,
            readonly=True,
        )

    def run_auto_plan(self, llm, cwd: str, user_query: str) -> AutoAgentResult:
        """PlanAgent — read-only planning agent."""
        if not self.should_auto_plan(user_query):
            return AutoAgentResult(agent_type=AutoAgentType.PLANNER, triggered=False)

        return self._run_agent(
            llm=llm,
            cwd=cwd,
            prompt=self.get_plan_prompt(user_query),
            agent_type=AutoAgentType.PLANNER,
            system_prompt=PLAN_SYSTEM_PROMPT,
            readonly=True,
        )

    def run_auto_verify(self, llm, cwd: str, task: str) -> AutoAgentResult:
        """VerifierAgent — post-task verification."""
        if not self.should_auto_verify(task):
            return AutoAgentResult(agent_type=AutoAgentType.VERIFIER, triggered=False)

        return self._run_agent(
            llm=llm,
            cwd=cwd,
            prompt=self.get_verify_prompt(task),
            agent_type=AutoAgentType.VERIFIER,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            readonly=False,
        )

    def reset(self) -> None:
        self.modified_files.clear()
        self.error_history.clear()
        self._review_pending = False


# ---------------------------------------------------------------------------
# Plan Consensus
# ---------------------------------------------------------------------------

_CONSENSUS_PLANNER_SYSTEM = (
    "You are a Plan Agent. Read-only mode — do NOT modify any files. "
    "Analyze the codebase and produce a numbered, actionable implementation plan "
    "with file references. If feedback is provided, revise the plan accordingly."
)

_CONSENSUS_ARCHITECT_SYSTEM = (
    "You are an Architect Agent. Read-only mode — do NOT modify any files. "
    "Review the proposed implementation plan for architectural soundness. "
    "Check: layer violations, coupling, missing error handling, scalability concerns. "
    "Provide specific improvement suggestions referencing file:line where possible."
)

_CONSENSUS_CRITIC_SYSTEM = (
    "You are a Critic Agent. Evaluate the quality of this implementation plan. "
    "Approve only if: 80%+ of steps cite file:line references, all steps are testable, "
    "no vague 'implement X' steps without specifics. "
    "Respond with a JSON object: "
    '{"approved": true/false, "score": 0-100, "feedback": "..."}. '
    "No other text."
)


def run_plan_consensus(
    llm,
    cwd: str,
    task: str,
    max_rounds: int = 3,
) -> str:
    """Planner → Architect → Critic consensus loop.

    1. Planner: generate implementation plan
    2. Architect: architecture review + improvement suggestions
    3. Critic: quality evaluation (80%+ file:line citations, testable criteria)
    4. If not approved, Planner incorporates feedback → repeat
    """
    import json as _json

    from .loop import AgentLoop
    from .permissions import PermissionMode
    from .tools import create_default_tools

    def _run(system: str, prompt: str, readonly: bool, max_turns: int = 10) -> str:
        all_tools = create_default_tools(cwd=cwd)
        tools = _filter_readonly_tools(all_tools) if readonly else all_tools
        agent = AgentLoop(
            llm=llm,
            tools=tools,
            cwd=cwd,
            permission_mode=PermissionMode.YOLO,
            system_prompt=system,
        )
        agent.MAX_TURNS = max_turns
        agent.streaming = False
        return agent.run(prompt)

    previous_feedback = ""
    best_plan = ""

    for round_num in range(1, max_rounds + 1):
        print(f"\n\033[35m  [Consensus round {round_num}/{max_rounds}]\033[0m")

        # 1. Planner
        print("\033[35m  [Consensus] Planner drafting...\033[0m")
        planner_prompt = f"Task: {task}"
        if previous_feedback:
            planner_prompt += f"\n\nPrevious critic feedback to address:\n{previous_feedback}"
        plan = _run(_CONSENSUS_PLANNER_SYSTEM, planner_prompt, readonly=True)
        best_plan = plan

        # 2. Architect review
        print("\033[35m  [Consensus] Architect reviewing...\033[0m")
        architect_prompt = (
            f"Review this implementation plan for the task: {task}\n\n"
            f"Plan:\n{plan}"
        )
        review = _run(_CONSENSUS_ARCHITECT_SYSTEM, architect_prompt, readonly=True)

        # 3. Critic evaluation
        print("\033[35m  [Consensus] Critic evaluating...\033[0m")
        critic_prompt = (
            f"Evaluate this implementation plan.\n\n"
            f"Task: {task}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Architect review:\n{review}"
        )
        critique_raw = _run(_CONSENSUS_CRITIC_SYSTEM, critic_prompt, readonly=True, max_turns=5)

        # Parse critique JSON
        try:
            # Extract JSON from response (may have surrounding text)
            import re as _re
            json_match = _re.search(r'\{[^{}]*"approved"[^{}]*\}', critique_raw, _re.DOTALL)
            if json_match:
                critique = _json.loads(json_match.group())
            else:
                critique = _json.loads(critique_raw.strip())
        except Exception:
            critique = {"approved": False, "score": 0, "feedback": critique_raw[:500]}

        score = critique.get("score", 0)
        approved = critique.get("approved", False)
        feedback = critique.get("feedback", "")

        print(f"\033[35m  [Consensus] Score: {score}/100 | Approved: {approved}\033[0m")

        if approved:
            print("\033[32m  [Consensus] Consensus reached!\033[0m")
            return _format_consensus_result(plan, review, round_num, score, approved=True)

        previous_feedback = feedback

    # Max rounds reached — return best effort
    print("\033[33m  [Consensus] Max rounds reached. Returning best plan.\033[0m")
    return _format_consensus_result(best_plan, "", max_rounds, score=0, approved=False)


def _format_consensus_result(
    plan: str,
    review: str,
    rounds: int,
    score: int,
    approved: bool,
) -> str:
    status = "APPROVED" if approved else "BEST EFFORT"
    header = f"[Plan Consensus — {status} after {rounds} round(s), score: {score}/100]\n"
    lines = [header, plan]
    if review:
        lines.append(f"\n[Architect Notes]\n{review}")
    return "\n".join(lines)
