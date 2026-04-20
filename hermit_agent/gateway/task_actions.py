from __future__ import annotations

from .task_store import GatewayTaskState


def is_waiting_for_reply(state: GatewayTaskState) -> bool:
    return state.is_waiting_for_reply()


def enqueue_reply(state: GatewayTaskState, message: str) -> None:
    state.enqueue_reply(message)


def cancel_task_state(state: GatewayTaskState) -> None:
    state.cancel()
