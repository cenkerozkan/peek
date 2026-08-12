# 003 — CLI config-path resolver

## Goal

A helper function that CLI commands use to find the `databases.toml` file,
with a search order tailored to project-local usage.

## Context

The MCP server uses `AppConfig.resolved_config_file()` which checks the
`PEEK_CONFIG_FILE` env var, then falls back to the platform config dir
(`platformdirs.user_config_dir("peek")`). The CLI needs a different search
order that also checks the project-local `.peek/` directory — the location
`peek init` creates (a later task).

Search order for CLI commands:
1. `PEEK_CONFIG_FILE` env var (consistent with server).
2. `.peek/databases.toml` in cwd (project-local).
3. Platform config dir (`platformdirs.user_config_dir("peek") / "databases.toml"`).

Return the first path that exists. If none exist, return the cwd-local path
(`.peek/databases.toml`) so error messages point the user at `peek init`.

Line length 79. `typing` library, not PEP 604 pipes.

## Files

You may create or modify only these:

- `src/peek/cli/__init__.py` — modify: add `resolve_config_path` function
- `tests/cli/__init__.py` — new (empty, makes it a package)
- `tests/cli/test_resolve_config.py` — new

## Specification

### `resolve_config_path() -> Path`

Add this function to `src/peek/cli/__init__.py`. It returns a `Path` and
takes no arguments. The search order:

1. Check the `PEEK_CONFIG_FILE` environment variable. If set and the path
   exists, return it.
2. Check for `.peek/databases.toml` relative to the current working directory.
   If it exists, return it.
3. Check the platform config directory (via `platformdirs.user_config_dir("peek")`)
   for `databases.toml`. If it exists, return it.
4. If nothing exists, return the cwd-local path from step 2 as the default
   (so error messages point the user toward `peek init`).

### Tests

`tests/cli/test_resolve_config.py`:

1. `test_env_var_takes_priority` — set `PEEK_CONFIG_FILE` to a tmp file,
   also create `.peek/databases.toml` in a tmp cwd. Env var wins.
2. `test_local_peek_dir` — no env var, create `.peek/databases.toml` in
   tmp cwd. Returns the local path.
3. `test_platform_fallback` — no env var, no `.peek/` in cwd, create the
   file in the platform dir (mock `user_config_dir`). Returns platform path.
4. `test_nothing_exists_returns_local` — nothing exists anywhere. Returns
   `cwd / ".peek" / "databases.toml"`.

Use `monkeypatch.chdir(tmp_path)` to control cwd. Use `monkeypatch.setenv` /
`monkeypatch.delenv` for `PEEK_CONFIG_FILE`.

## Constraints

- Do not modify `AppConfig` or `src/peek/config.py` — the server's resolution
  is unchanged. This is CLI-only logic.
- Do not use hardcoded `~/.config` — use `platformdirs`.
- Use `pathlib.Path` throughout.

## Acceptance check

```bash
python -m pytest tests/cli/test_resolve_config.py -v
```

All tests pass.

## Out of scope

- The `peek init` command (next task).
- The `peek db` commands (later tasks).
- Any changes to how the MCP server finds its config.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:** done

**Files changed:**
- `src/peek/cli/__init__.py` (modified — added `resolve_config_path` function and imports)
- `tests/cli/__init__.py` (new, empty)
- `tests/cli/test_resolve_config.py` (new — 4 tests)

**Acceptance check:** passed — `python -m pytest tests/cli/test_resolve_config.py -v` → 4 passed in 0.03s

**Deviations:** none

**Problems:** None. Pre-existing `ty` errors in `tests/infra/test_config_file.py` are unrelated to this task.
