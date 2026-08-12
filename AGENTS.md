<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

## What this project is

A safe, multi-database, **read-only** MCP server. An outer agent (Claude Code, Copilot) writes the SQL; `peek` enforces safety and delivers results. **No internal LLM.** See `CLAUDE.md` for hard rules and `docs/` for settled architecture.

## Developer commands

```sh
uv sync                          # install package + dev deps
uv run pytest                    # run the suite (uses SQLite in-memory)
uv run peek                      # start the MCP server on stdio (waits silently — healthy)
uv run pre-commit install        # install pre-commit hooks in venv
uv run pre-commit run --all-files  # run all checks manually
```

Pre-commit runs in this **exact order**: `isort` → `ruff check --fix` → `ruff format` → `ty`. Do not commit around the hooks.

## Architecture invariants (don't violate)

- **Imports point downward only:** `tools/ → services/ → backends/ → infra/`. `backends/ → safety/`. Never reverse.
- **`services/sql_service.py` is the single safety chokepoint.** Every SQL path goes through it, which calls `safety/guard.py` before execution. Never execute SQL from a tool or anywhere else bypassing it.
- **Credential isolation.** Connection URLs are `SecretStr` (never leaks in repr/logs). FastMCP is built with `mask_error_details=True` to catch leaks. No tool return value or error message may contain a connection string. `list_databases` returns aliases only.
- **Every tool takes a `db` alias param.** No hardcoded connections. One DB per request.
- **Use `pathlib.Path`, not `platformdirs`.** Resolve user config dirs via `user_config_dir("peek")`, never hardcoded paths like `~/.config`.

## Style quirks (differ from defaults)

- **Line length: 79** (strict PEP8, not the common 88).
- **Use the `typing` library — NOT PEP 604 pipe unions.** Write `Optional[int]`, not `int | None`. Ruff's `UP` rules are deliberately disabled.
- **No comment lines.** Code must explain itself. Ruff `ERA` rejects commented-out code.
- **MCP tool docstrings are required** — they're the agent-facing contract.
- Docstrings: optional (Google style) except on MCP tools where they're mandatory.

## Testing

- `tests/` mirrors `src/peek/` structure.
- Tests import `peek` (not `src.peek`) — pytest gets the package root via `pythonpath = ["src"]` in `pyproject.toml`.
- Tests run against temporary SQLite databases (no external services needed).
- The safety chokepoint (`safety/guard.py` and `sql_service`) must have tests proving non-SELECT / mutating statements are rejected.

## Configuration

- Databases registered via `databases.toml` in the user config directory (or pointed at by `PEEK_CONFIG_FILE`).
- `PEEK_MAX_ROWS` sets the row cap for `run_sql` (default: 1000).
- The file is the only place credentials live — never in the repo or MCP launch config.

## PyPI distribution

Distribution name is `peek-db` (import package and console command are both `peek`). Database drivers are optional extras (e.g., `peek-db[postgres]`).

## Documentation map

| Topic | File |
| --- | --- |
| Architecture, safety, layers | `docs/architecture.md` |
| Package structure, import rules | `docs/structure.md` |
| Decision log (what + why) | `docs/decisions.md` |
| Killed/suspended ideas | `docs/backlog.md` |
| Code conventions, toolchain | `docs/conventions.md` |
| Implementation phases | `docs/roadmap.md` |

`CLAUDE.md` is the entry point. `docs/` = settled truth. `BRAINSTORM.md` = thinking-in-progress (unreliable).
