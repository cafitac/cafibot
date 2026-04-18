"""Autopilot — Full autonomous pipeline.

OMC autopilot pattern: idea → spec → plan → implementation → QA → verification.
Combines deep-interview + plan consensus + ralph + ultraqa.

Phase 0: Spec expansion (interview or LLM expansion)
Phase 1: Planning (consensus planning)
Phase 2: Implementation (ralph persistence loop)
Phase 3: QA cycling (ultraqa)
Phase 4: Final verification
Phase 5: Cleanup
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .llm_client import LLMClientBase
from .permissions import PermissionMode


class AutopilotPhase(Enum):
    SPEC = "spec"          # Phase 0
    PLAN = "plan"          # Phase 1
    EXECUTE = "execute"    # Phase 2
    QA = "qa"              # Phase 3
    VERIFY = "verify"      # Phase 4
    CLEANUP = "cleanup"    # Phase 5
    DONE = "done"


STATE_DIR = os.path.expanduser("~/.hermit/state")


@dataclass
class AutopilotState:
    task_id: str
    description: str
    phase: AutopilotPhase = AutopilotPhase.SPEC
    status: str = "running"  # running/completed/failed/cancelled
    spec: str = ""
    plan: str = ""
    ralph_task_id: str = ""
    ultraqa_task_id: str = ""
    verification_result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    phase_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "phase": self.phase.value,
            "status": self.status,
            "spec": self.spec,
            "plan": self.plan,
            "ralph_task_id": self.ralph_task_id,
            "ultraqa_task_id": self.ultraqa_task_id,
            "verification_result": self.verification_result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "phase_log": self.phase_log,
        }

    @staticmethod
    def from_dict(d: dict) -> AutopilotState:
        s = AutopilotState(
            task_id=d["task_id"],
            description=d["description"],
        )
        s.phase = AutopilotPhase(d.get("phase", "spec"))
        s.status = d.get("status", "running")
        s.spec = d.get("spec", "")
        s.plan = d.get("plan", "")
        s.ralph_task_id = d.get("ralph_task_id", "")
        s.ultraqa_task_id = d.get("ultraqa_task_id", "")
        s.verification_result = d.get("verification_result", "")
        s.started_at = d.get("started_at", 0)
        s.completed_at = d.get("completed_at", 0)
        s.phase_log = d.get("phase_log", [])
        return s


def _save(state: AutopilotState):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, f"autopilot-{state.task_id}.json"), "w") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)


def _load(task_id: str) -> AutopilotState | None:
    path = os.path.join(STATE_DIR, f"autopilot-{task_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return AutopilotState.from_dict(json.load(f))


def find_active_autopilot() -> AutopilotState | None:
    if not os.path.exists(STATE_DIR):
        return None
    for f in sorted(os.listdir(STATE_DIR), reverse=True):
        if f.startswith("autopilot-") and f.endswith(".json"):
            try:
                with open(os.path.join(STATE_DIR, f)) as fh:
                    s = AutopilotState.from_dict(json.load(fh))
                if s.status == "running":
                    return s
            except Exception:
                continue
    return None


class Autopilot:
    """Full autonomous execution pipeline."""

    def __init__(self, llm: LLMClientBase, cwd: str = ".", emitter=None):
        self.llm = llm
        self.cwd = cwd
        if emitter is None:
            from .events import AgentEventEmitter
            emitter = AgentEventEmitter()
        self.emitter = emitter

    def start(self, description: str) -> AutopilotState:
        state = AutopilotState(
            task_id=uuid.uuid4().hex[:12],
            description=description,
            started_at=time.time(),
        )
        _save(state)
        return state

    def run(self, state: AutopilotState) -> str:
        """Run the full pipeline."""
        try:
            # Phase 0: Spec expansion
            if state.phase == AutopilotPhase.SPEC:
                self._phase_spec(state)

            # Phase 1: Planning
            if state.phase == AutopilotPhase.PLAN:
                self._phase_plan(state)

            # Phase 2: Implementation (Ralph)
            if state.phase == AutopilotPhase.EXECUTE:
                self._phase_execute(state)

            # Phase 3: QA (UltraQA)
            if state.phase == AutopilotPhase.QA:
                self._phase_qa(state)

            # Phase 4: Final verification
            if state.phase == AutopilotPhase.VERIFY:
                self._phase_verify(state)

            # Phase 5: Cleanup
            state.phase = AutopilotPhase.DONE
            state.status = "completed"
            state.completed_at = time.time()
            _save(state)

            elapsed = state.completed_at - state.started_at
            return (
                f"Autopilot completed in {elapsed:.0f}s.\n"
                f"Phases: {' → '.join(state.phase_log)}\n"
                f"Task: {state.description}"
            )

        except Exception as e:
            state.status = "failed"
            state.phase_log.append(f"FAILED at {state.phase.value}: {e}")
            _save(state)
            return f"Autopilot failed at phase {state.phase.value}: {e}"

    def _phase_spec(self, state: AutopilotState):
        """Phase 0: Expand idea into a detailed spec using LLM."""
        self.emitter.progress("[Autopilot Phase 0: Spec Expansion]")
        state.phase_log.append("spec")

        response = self.llm.chat(
            messages=[{"role": "user", "content": (
                f"Expand this idea into a detailed specification:\n\n{state.description}\n\n"
                "Include:\n1. Goal (one clear sentence)\n2. Acceptance criteria (3-7 testable items)\n"
                "3. Technical approach\n4. Files to create/modify\n5. Non-goals"
            )}],
            system="You are a software architect. Write a concise, actionable specification.",
        )
        state.spec = response.content or state.description
        state.phase = AutopilotPhase.PLAN
        _save(state)

    def _phase_plan(self, state: AutopilotState):
        """Phase 1: Consensus planning (Planner→Architect→Critic)."""
        self.emitter.progress("[Autopilot Phase 1: Consensus Planning]")
        state.phase_log.append("plan")

        from .auto_agents import run_plan_consensus
        plan = run_plan_consensus(self.llm, self.cwd, state.spec)
        state.plan = plan
        state.phase = AutopilotPhase.EXECUTE
        _save(state)

    def _phase_execute(self, state: AutopilotState):
        """Phase 2: Implement using Ralph persistence loop."""
        self.emitter.progress("[Autopilot Phase 2: Execution (Ralph)]")
        state.phase_log.append("execute")

        from .ralph import Ralph
        from .tools import create_default_tools

        tools = create_default_tools(cwd=self.cwd, llm_client=self.llm)
        ralph = Ralph(self.llm, tools, self.cwd, emitter=self.emitter)

        task_with_plan = f"{state.description}\n\nPlan:\n{state.plan[:3000]}"
        ralph_state = ralph.start(task_with_plan)
        state.ralph_task_id = ralph_state.task_id

        ralph.run_loop(ralph_state)
        state.phase = AutopilotPhase.QA
        _save(state)

    def _phase_qa(self, state: AutopilotState):
        """Phase 3: Test cycling with UltraQA."""
        self.emitter.progress("[Autopilot Phase 3: QA Cycling (UltraQA)]")
        state.phase_log.append("qa")

        from .ultraqa import UltraQA
        from .tools import create_default_tools

        tools = create_default_tools(cwd=self.cwd, llm_client=self.llm)
        qa = UltraQA(self.llm, tools, self.cwd, emitter=self.emitter)

        qa_state = qa.start()
        state.ultraqa_task_id = qa_state.task_id

        qa.run_loop(qa_state)
        state.phase = AutopilotPhase.VERIFY
        _save(state)

    def _phase_verify(self, state: AutopilotState):
        """Phase 4: Final verification."""
        self.emitter.progress("[Autopilot Phase 4: Final Verification]")
        state.phase_log.append("verify")

        from .loop import AgentLoop
        from .tools import create_default_tools

        tools = create_default_tools(cwd=self.cwd)
        agent = AgentLoop(
            llm=self.llm, tools=tools, cwd=self.cwd,
            permission_mode=PermissionMode.YOLO,
        )
        agent.MAX_TURNS = 10
        agent.streaming = False

        result = agent.run(
            f"Verify that this task was completed correctly:\n\n"
            f"Task: {state.description}\n"
            f"Spec: {state.spec[:1000]}\n\n"
            f"Check files, run tests if available, and report PASS or FAIL."
        )
        state.verification_result = result
        _save(state)

    def cancel(self, state: AutopilotState):
        state.status = "cancelled"
        state.phase_log.append(f"cancelled at {state.phase.value}")
        _save(state)
