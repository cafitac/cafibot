"""FastAPI entrypoint for the benchmark starter.

Two endpoints only — the benchmark TASK asks the agent to add more.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import STORE, Todo

app = FastAPI(title="Todo API — Hermit benchmark starter")


class TodoCreate(BaseModel):
    title: str


class TodoOut(BaseModel):
    id: int
    title: str
    completed: bool

    @classmethod
    def from_model(cls, todo: Todo) -> "TodoOut":
        return cls(id=todo.id, title=todo.title, completed=todo.completed)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/todos", status_code=201, response_model=TodoOut)
def create_todo(payload: TodoCreate) -> TodoOut:
    todo = STORE.create(payload.title)
    return TodoOut.from_model(todo)


@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int) -> TodoOut:
    todo = STORE.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return TodoOut.from_model(todo)
