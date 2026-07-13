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
      `sys.path`); absolute imports use the `src.` prefix. *(Superseded in
      Phase 7: the `src.` prefix was dropped — see below.)*

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

## Phase 3 — Table exclusion (per-DB denylist) ✅

A third safety layer, orthogonal to read-only: a user-defined **per-alias denylist
of tables that must never reach any LLM's context**, regardless of environment
(prod/uat/dev). Config-driven and **not model-facing** — the model can neither see
nor query an excluded table. Built here so the schema and SQL services below are
exclusion-aware from the start.

- [x] Extend the registry config: per-alias `exclude_tables` (schema-qualifiable
      table names) in the TOML; parse/validate in `models/config.py`
      (`DatabaseEntry.exclude_tables`, default empty). Retained per-alias in
      `connection_registry` but **deliberately not exposed** in `describe`/
      `list_metadata` — surfacing excluded names there would reveal hidden tables
      to the model (see `decisions.md` #16).
- [x] Decide + record matching semantics in `decisions.md` #16: case-insensitive,
      schema-qualification (bare = any schema, `schema.table` = that schema),
      exact names — no glob/wildcard patterns in v1.
- [x] `is_excluded(alias, table, schema=None)` on `connection_registry` — the
      single source of truth both the schema and SQL services consume.
- [x] Tests: exclusions load and validate; the accessor matches per the chosen
      semantics; unknown/empty lists are handled.

## Phase 4 — Schema service (introspection) ✅

- [x] Resolve open question: `get_schema` output shape (structured columns vs DDL)
      and its pagination/filter params. *(Decided: structured columns + PK/FK,
      table selector + `limit`/`offset`, views + optional `schema`; see
      `decisions.md` #15.)*
- [x] `services/schema_service.py` — over a registry engine (SQLAlchemy `inspect`):
      `list_tables(alias)` and `get_schema(alias, ...)` with pagination/filtering.
      No credentials in returns or errors.
- [x] **Honor the denylist (Phase 3):** excluded table *names* are omitted from
      `list_tables`, rejected by `get_schema` (as if nonexistent), and scrubbed
      from other tables' foreign keys; `list_tables`/`get_schema` return a
      `hidden_count` so the agent knows tables were withheld without learning
      their names (decision #16).
- [x] `models/schema.py` — Pydantic I/O types for table lists and schema results.
- [x] Tests against a SQLite fixture with a couple of tables, incl. a case proving
      an excluded table never appears in any output.

## Phase 5 — SQL service (the execution chokepoint) ✅

- [x] Resolve open question: `run_sql` row cap enforcement (`max_rows`), max result
      size, and the result serialization shape. *(Decided: `{alias, columns, rows,
      row_count, truncated}` with positional rows, global `max_rows` only, validate
      raises; see `decisions.md` #17.)* Recorded in `decisions.md`; cleared from
      `BRAINSTORM.md`.
- [x] Dialect mapping — SQLAlchemy dialect name → `sqlglot` dialect
      (`infra/dialects.py`), stored per alias on the registry
      (`sqlglot_dialect(alias)`, honoring the `DatabaseEntry.dialect` override), so
      the guard parses in the right dialect per alias.
- [x] `services/sql_service.py` — `validate(alias, sql)` (calls `safety/guard.py`)
      and `execute(alias, sql)` (validate → run read-only → cap rows → serialize).
      **Every SQL path goes through here.**
- [x] **Enforce the denylist (Phase 3) at execution:** after the read-only check,
      `validate` walks the parsed AST's table references (incl. CTEs/subqueries) and
      rejects any query that touches an excluded table via
      `ExcludedTableError(UnsafeSQLError)` — hiding it from introspection is not
      enough on its own. Rejection message names only "table not permitted", never
      the schema or credentials.
- [x] `models/query.py` — Pydantic `QueryResult`. *(Validation-outcome shaping is
      deferred to the Phase 6 tool layer, since `validate` raises.)*
- [x] Tests proving execution is impossible without passing the guard, that a query
      naming an excluded table is rejected, that the row cap and truncation flag
      work, and that errors are credential-safe.

## Phase 6 — MCP tool layer (thin) ✅

Thin FastMCP tools; docstrings are the agent-facing contract. Tools reach the
services through the `tools/context.py` dependency seam (`AppContext` +
`app_context()`), which the Phase 7 lifespan will populate.

- [x] `tools/databases.py` — `list_databases()` (aliases + safe metadata only; no
      register/remove).
- [x] `tools/schema.py` — `list_tables(db)`, `get_schema(db, ...)`.
- [x] `tools/sql.py` — `validate_sql(db, sql)`, `run_sql(db, sql)`.
- [x] Each tool: validate params, call a service, shape a structured/actionable
      (credential-safe) response. No business logic in tool bodies. `validate_sql`
      returns a `ValidationResult` verdict; the others raise `ToolError` with the
      credential-safe service message.
- [x] Tests asserting the tool contracts and error shaping.

## Phase 7 — Server wiring & lifecycle ✅

- [x] `server.py` — FastMCP entry: lifespan builds the `ConnectionRegistry` and
      services once, yields an `AppContext` under `tools.context.APP_CONTEXT_KEY`
      (the Phase 6 seam), calls `tools.register(mcp)`, disposes on shutdown. Stdio
      transport.
- [x] Construct the server with `FastMCP(..., mask_error_details=True)` so any
      unexpected (non-`ToolError`) exception is masked from the client — the second
      half of the credential-isolation guarantee the Phase 6 tools rely on.
- [x] Console entry point + `python -m` runnability (`src/peek/__main__.py`).
- [x] Reconciled packaging with the `src.` import convention: the `src.` prefix is
      **removed**. Absolute imports are `from peek.x import y`; `src/__init__.py` is
      deleted; pytest gets the package root via `pythonpath = ["src"]` in
      `pyproject.toml` instead of a root `conftest.py` `sys.path` shim. Tests import
      `peek` exactly as an installed wheel does. `docs/conventions.md` and
      `docs/structure.md` never documented the `src.` prefix as a rule, so no
      correction was needed there.
- [x] `tests/test_server.py` (9 tests): lifespan, `AppContext` publication, engine
      disposal on both clean exit and mid-session exception, tool registration, and
      `mask_error_details`.

## Phase 8 — Packaging & distribution ✅ (publishing outstanding — see Phase 9)

Make peek installable as an isolated app. See `decisions.md` #14 (amended
2026-07-13 for the PyPI name conflict).

- [x] `[project.scripts] peek = "peek.server:main"` — console entry point (builds
      on the Phase 7 entry-point work) so `uvx`, `pipx install`, and
      `python -m peek` all resolve to a runnable command.
- [x] **PyPI name conflict discovered and resolved.** `peek` and `peek-mcp` are
      both already taken on PyPI by unrelated packages. The distribution name is
      now `peek-sql`; the import package and console command stay `peek`. See
      `decisions.md` #14.
- [x] `pyproject.toml` PyPI metadata: `name = "peek-sql"`, `license = "MIT"` (+
      license-files), authors, keywords, classifiers, `[project.urls]`.
- [x] `server.py` `main()` pins `run(transport="stdio", show_banner=False)` —
      stdout is the MCP channel, so the transport is explicit and the startup
      banner (which goes to stderr) is suppressed rather than left to a framework
      default.
- [x] Verified locally (not yet published — see Phase 9) that `uv tool install .`,
      `uvx --from . peek`, and `pipx install .` all launch cleanly, including the
      `[postgres]` driver extra (psycopg 3.3.4 resolved into the tool env).
      Confirmed the installed wheel serves all 5 tools over MCP stdio against a
      scratch SQLite DB, and that `import peek` fails outside the tool env (it's an
      isolated app, not an importable library on the path).
- [x] First CI in the repo: `.github/workflows/ci.yml` — matrix over
      ubuntu-latest/windows-latest/macos-latest, running ruff + isort + ty +
      pytest, building the wheel, installing it as an isolated tool, and
      smoke-testing that the `peek` console script boots. This is how the
      Windows/macOS entry-point requirement (decision #12) is verified, since it
      can't be checked on the Linux dev box. See `decisions.md` #18.
- [ ] **Publish `peek-sql` 0.1.0 to PyPI and claim the name.** Not done — folded
      into Phase 9 below. Until this happens, `uvx --from peek-sql peek` does not
      work for anyone but us.

## Phase 9 — End-to-end, publishing & docs ⬜

- [ ] **Publish `peek-sql` 0.1.0 to PyPI**, claiming the distribution name (moved
      up from Phase 8 — local install verification is done, the publish step is
      not).
- [ ] Manual end-to-end: register a real DB alias, drive `list_databases` →
      `list_tables` → `get_schema` → `validate_sql` → `run_sql` from an MCP client.
- [ ] Document the MCP launch config (config-file *path* only — never credentials)
      and a sample `databases.toml`, including a per-alias `exclude_tables` example
      (Phase 3). Lead the install/launch story with
      `uvx --from peek-sql peek`
      (`{"command": "uvx", "args": ["--from", "peek-sql", "peek"]}`); note
      `pipx install peek-sql` as the alternative and the driver-extra syntax (see
      `decisions.md` #14).
- [ ] Read-only DB role guidance (the second, independent safety layer).

---

## Later / deferred (not v1)

Tracked in `backlog.md`; do not start without a decision change.

- [ ] Admin CLI — `peek db add/remove/list` reusing the registry interface. Human
      tool only (never an MCP tool); writes connection strings solely to the local
      config file; validates the connection before persisting; **restart to apply**
      (no live reload in v1). See `decisions.md` #7a.
- [ ] HTTP transport (core is already transport-agnostic).
- [ ] Interactive TUI — reintroduces an internal NL→SQL brain (suspended pipeline).
- [ ] Suspended internal NL→SQL pipeline, embedding-based schema retrieval.
