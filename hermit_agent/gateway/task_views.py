from __future__ import annotations

from .task_store import GatewayTaskState


def peek_waiting_prompt(state: GatewayTaskState) -> dict[str, object]:
    return state.peek_waiting_prompt()


def add_waiting_prompt_fields(
    result: dict[str, object],
    state: GatewayTaskState,
    *,
    include_kind: bool,
) -> dict[str, object]:
    return state.add_waiting_prompt_fields(result, include_kind=include_kind)
