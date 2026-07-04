# Development Conventions

Rules for writing code in this repo. Two zones:

- **A. Firm rules** — follow directly from settled architecture (`architecture.md`,
  `structure.md`, `decisions.md`). Don't violate without a decision change.
- **B. Tooling & style** — the confirmed toolchain and code style, enforced by
  pre-commit where possible.

---

## A. Firm rules (from settled architecture)

### Layering & imports
- Dependencies point **downward only**: `tools/ → services/ → infra/`, and
  `services/ → safety/`. Never the reverse. `services/` must not import `tools/`;
  `infra/` must not import `services/`.
- **Tools stay thin.** A tool body only: validate/normalize params, call a service,
  shape the return. No business logic, no direct DB/engine access — always through a
  service.

### Safety (non-negotiable)
- **All SQL execution goes through `sql_service`**, which calls `safety/guard.py`
  first. Never execute SQL from a tool, or anywhere else, bypassing it.
- The parse check rejects anything that isn't a read-only SELECT. Do not add a code
  path that runs unvalidated SQL.

### Credential isolation (non-negotiable)
- **Never** put a connection string in a tool return value, an error message, a log
  line, or an exception that propagates to a caller. Callers see only aliases.
- Sanitize DB errors before returning them — strip any URL/credential material.
- `list_databases` returns aliases (+ safe metadata like dialect) only.
- Connection strings live only in the user's local config file and in-process
  engines — never in the repo or the MCP launch config.

### Multi-database
- Every tool takes a DB alias param. No hardcoded single connection.
- One database per request (no cross-DB joins).

### Cross-platform paths
- Use `pathlib.Path` for all path work — no string concatenation, no hardcoded
  `/` or `\`.
- Resolve user/config dirs via `platformdirs` (`user_config_dir("peek")`) — never
  a hardcoded `~/.config`. Target Windows/macOS (Linux rare).

### No internal LLM (v1)
- Don't add an in-server LLM/agent/pipeline, or `langchain`/`langgraph` deps. (See
  `backlog.md` for the suspended pipeline and its revival condition.)

---

## B. Tooling & style

### Project & environment
- **Python 3.13+** (do **not** target 3.12). The venv is built on `python3.13`.
- **`src`-layout**, `pyproject.toml` at repo root. (`uv` is the intended package
  manager; the current venv was bootstrapped with `python3.13 -m venv`.)

### Quality toolchain (enforced via pre-commit)
Configured in `.pre-commit-config.yaml`, pinned versions, run in this order:
1. **isort** (8.0.1) — import sorting (`profile = "black"`, line length 79).
2. **ruff check --fix** (0.15.20) — lint (PEP8 + pyflakes + bugbear + docstrings +
   commented-out-code) with autofix.
3. **ruff format** (0.15.20) — formatting.
4. **ty** (0.0.56) — static type checking (Astral).

Install for a fresh clone: `pre-commit install` (inside the venv). Do not commit
around the hooks.

### PEP8 & line length
- **Strictly follow PEP8.** Enforced by ruff `E`/`W`. Line length **79**
  (strict PEP8). _Bump only by team decision; update `pyproject.toml` if so._

### Typing
- **Type hints everywhere**, checked by `ty`.
- **Use the `typing` library — NOT PEP 604 pipe unions.** Write `Optional[int]` /
  `Union[A, B]`, not `int | None`. Ruff's pyupgrade (`UP`) rules are deliberately
  disabled so nothing auto-rewrites to pipes.
- **Pydantic** models for tool inputs/outputs (`models/`) so the MCP schema and
  validation come from one source.

### Comments & docstrings
- **No comment lines.** Code must explain itself through naming and structure.
  Comments only for genuinely niche cases (a non-obvious workaround, a gotcha).
  Commented-out code is rejected by ruff `ERA`.
- **Docstrings are allowed, Google style** (ruff pydocstyle `convention = "google"`).
  They are *optional* on most code (missing-docstring rules `D1xx` are ignored) and
  enforced for *style* when present.
- **MCP tool docstrings are required** and are an interface contract — the agent
  picks tools by reading them. Each tool: what it does, params (incl. the DB alias),
  and return shape.

### Errors
- Tools return **structured, actionable errors**, never raw exceptions/tracebacks.
- Error text must be safe to send to a model (see credential isolation in Zone A).

### Testing
- **pytest** (9.1.1). `tests/` mirrors `src/peek/` (see `structure.md`).
- Required coverage for the safety chokepoint: `safety/guard.py` and `sql_service`
  must have tests proving non-SELECT / mutating statements are rejected.

### Logging
- stdlib `logging`, structured; **never** log connection strings or SQL params that
  could contain secrets (see credential isolation).
