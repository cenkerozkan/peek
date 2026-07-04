# Roadmap

Ordered implementation plan for the read-only SQL MCP server. We build
**bottom-up**, following the downward import direction from `structure.md`
(`tools/ → services/ → infra/`, `services/ → safety/`): each layer is built and
tested before the layer that depends on it. **One step at a time** — a step is
done only when its code, tests, and the full toolchain (`ruff`, `isort`, `ty`,
`pytest`) are green.

For *what* each piece is and *why*, see `architecture.md`, `structure.md`, and
`decisions.md`. This file is only the order of work.

Legend: `[x]` done · `[~]` in progress · `[ ]` not started.

---

## Phase 0 — Scaffolding & tooling ✅

- [x] Repo, `pyproject.toml`, `src`-layout, venv, pre-commit (ruff/isort/ty).
- [x] Architecture/structure/decisions/conventions docs.
- [x] `README.md`; `src` as a package; root `conftest.py` (repo root on
      `sys.path`); absolute imports use the `src.` prefix.

## Phase 1 — Safety guard ✅

The most safety-critical piece; built first, in isolation.

- [x] `safety/guard.py` — `ensure_read_only(sql, dialect)`: single-statement,
      SELECT-only, full-tree scan rejecting mutations (incl. in CTEs/subqueries),
      unparsed `Command`s, and stacked statements. Returns the parsed expression.
- [x] Tests proving every mutating/stacked/empty case is rejected and that error
      messages never echo the input.

## Phase 2 — Config & connection layer ✅

Get from a config file to validated, alias-addressed engines.

- [x] `errors.py` — `PeekError` base + `ConfigError`, `RegistryError`.
- [x] `models/config.py` — `DatabaseEntry` with a `SecretStr` url (no password in
      repr/logs). *(Decided: config format is **TOML**.)*
- [x] `config.py` — `AppConfig` (pydantic-settings): registry-file path via
      `platformdirs`, `max_rows` default `1000`.
- [x] `infra/config_file.py` — `load_registry(path)` parses the alias→URL TOML;
      errors reference only the file path.
- [x] `infra/engines.py` — `build_engine(entry)`; unwraps the secret only at
      `create_engine`.
- [x] `services/connection_registry.py` — validate each connection at startup;
      expose `aliases()` / `get_engine()` / credential-free metadata; `add`/`remove`
      behind an interface for a future admin CLI.
- [x] Tests (SQLite in-memory) incl. credential-isolation assertions.

---

## Phase 3 — Schema service (introspection) ⬜

- [ ] Resolve open question: `get_schema` output shape (structured columns vs DDL)
      and its pagination/filter params. *(Leaning: structured columns.)* Record the
      decision in `decisions.md` and clear it from `BRAINSTORM.md`.
- [ ] `services/schema_service.py` — over a registry engine (SQLAlchemy `inspect`):
      `list_tables(alias)` and `get_schema(alias, ...)` with pagination/filtering.
      No credentials in returns or errors.
- [ ] `models/` — Pydantic I/O types for table lists and schema results.
- [ ] Tests against a SQLite fixture with a couple of tables.

## Phase 4 — SQL service (the execution chokepoint) ⬜

- [ ] Resolve open question: `run_sql` row cap enforcement (`max_rows`), max result
      size, and the result serialization shape. *(Leaning: `{columns, rows,
      truncated}`.)* Record in `decisions.md`; clear from `BRAINSTORM.md`.
- [ ] Dialect mapping — SQLAlchemy dialect name → `sqlglot` dialect, so the guard
      parses in the right dialect per alias.
- [ ] `services/sql_service.py` — `validate(alias, sql)` (calls `safety/guard.py`)
      and `execute(alias, sql)` (validate → run read-only → cap rows → serialize).
      **Every SQL path goes through here.**
- [ ] `models/` — Pydantic types for query results and validation outcomes.
- [ ] Tests proving execution is impossible without passing the guard, that the row
      cap and truncation flag work, and that errors are credential-safe.

## Phase 5 — MCP tool layer (thin) ⬜

Thin FastMCP tools; docstrings are the agent-facing contract.

- [ ] `tools/databases.py` — `list_databases()` (aliases + safe metadata only; no
      register/remove).
- [ ] `tools/schema.py` — `list_tables(db)`, `get_schema(db, ...)`.
- [ ] `tools/sql.py` — `validate_sql(db, sql)`, `run_sql(db, sql)`.
- [ ] Each tool: validate params, call a service, shape a structured/actionable
      (credential-safe) response. No business logic in tool bodies.
- [ ] Tests asserting the tool contracts and error shaping.

## Phase 6 — Server wiring & lifecycle ⬜

- [ ] `server.py` — FastMCP entry: lifespan builds the `ConnectionRegistry` once,
      injects it into tools/services, disposes on shutdown. Stdio transport.
- [ ] Console entry point + `python -m` runnability.
- [ ] Reconcile packaging with the `src.` import convention (a built wheel exposes
      top-level `peek`, not `src.peek`) — see `[[feedback-src-prefixed-imports]]`.

## Phase 7 — End-to-end & docs ⬜

- [ ] Manual end-to-end: register a real DB alias, drive `list_databases` →
      `list_tables` → `get_schema` → `validate_sql` → `run_sql` from an MCP client.
- [ ] Document the MCP launch config (config-file *path* only — never credentials)
      and a sample `databases.toml`.
- [ ] Read-only DB role guidance (the second, independent safety layer).

---

## Later / deferred (not v1)

Tracked in `backlog.md`; do not start without a decision change.

- [ ] Admin CLI — `peek db add/remove` reusing the registry interface.
- [ ] HTTP transport (core is already transport-agnostic).
- [ ] Interactive TUI — reintroduces an internal NL→SQL brain (suspended pipeline).
- [ ] Suspended internal NL→SQL pipeline, embedding-based schema retrieval.
