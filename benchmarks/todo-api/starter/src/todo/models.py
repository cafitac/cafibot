"""In-memory Todo model. Deliberately simple so the benchmark measures
tool-use overhead, not algorithmic complexity."""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from threading import Lock
from typing import Iterator


@dataclass
class Todo:
    id: int
    title: str
    completed: bool = False


class TodoStore:
    """Thread-safe in-memory todo store."""

    def __init__(self) -> None:
        self._items: dict[int, Todo] = {}
        self._ids: Iterator[int] = count(1)
        self._lock = Lock()

    def create(self, title: str) -> Todo:
        with self._lock:
            todo = Todo(id=next(self._ids), title=title)
            self._items[todo.id] = todo
            return todo

    def get(self, todo_id: int) -> Todo | None:
        return self._items.get(todo_id)

    def list_all(self) -> list[Todo]:
        return list(self._items.values())


STORE = TodoStore()
