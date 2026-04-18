# Benchmark task — todo-api

Extend the starter with the features below, keeping the existing
`/health`, `POST /todos`, and `GET /todos/{id}` endpoints working.

## Deliverables

1. **List endpoint with filters**
   - `GET /todos?completed=true|false&q=<text>`
   - Both query parameters are optional.
   - `completed` filters by boolean; `q` is a case-insensitive substring
     match against `title`.
   - Returns an array of `TodoOut`.

2. **Update endpoint**
   - `PATCH /todos/{id}`
   - Request body: `{title?: string, completed?: bool}` — either or both.
   - Returns the updated `TodoOut`, `404` if the id is unknown, and
     `422` if the body is empty.

3. **Delete endpoint**
   - `DELETE /todos/{id}`
   - Returns `204` on success, `404` if unknown.

4. **Tests**
   - Add a test file covering:
     - Listing with no filter returns all items.
     - Listing with `completed=true` excludes uncompleted items (and
       vice versa).
     - `q` filter is case-insensitive.
     - `PATCH` updates individual fields without clobbering others.
     - `PATCH` with empty body returns `422`.
     - `DELETE` removes the item; a follow-up `GET` returns `404`.

## Constraints

- Do not change the existing endpoint signatures.
- Do not add new top-level dependencies beyond what is in
  `pyproject.toml` (FastAPI, Pydantic, pytest, httpx).
- Keep the in-memory store — no database, no file I/O.
- Run `pytest` before finishing and make sure everything passes.

## Success criteria

- All original tests still pass.
- The new tests listed under "Tests" above all pass.
- `GET /todos` without filters returns the full list in deterministic
  insertion order.
