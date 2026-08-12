# 004 — `peek init` command

## Goal

`peek init` creates a `.peek/` project directory with a template
`databases.toml` and adds `.peek/` to `.gitignore`.

## Context

Users need a way to bootstrap their project-local peek config. `peek init`
creates the `.peek/` directory in the current working directory (similar to
`.claude/`, `.vscode/`), writes a template TOML with commented examples,
and ensures `.peek/` is gitignored (the file contains credentials).

Task 001 set up the Click group in `src/peek/cli/__init__.py`. This task
adds the `init` subcommand.

Line length 79. `typing` library. Google-style docstrings optional.

## Files

You may create or modify only these:

- `src/peek/cli/init_cmd.py` — new
- `src/peek/cli/__init__.py` — modify: register the `init` command
- `tests/cli/test_init.py` — new

## Specification

### `src/peek/cli/init_cmd.py`

A Click command named `init` that:

1. Checks if `.peek/` already exists in cwd. If yes, print an "already
   initialized" message to stderr and exit with code 1.
2. Creates the `.peek/` directory.
3. Writes `.peek/databases.toml` with a comment-only template showing an
   example database entry (alias, URL, dialect, exclude_tables) — all
   commented out so it is not a valid config until the user adds a real entry.
4. Handles `.gitignore` in cwd:
   - If `.gitignore` exists, read it. If `.peek/` is not already listed,
     append it with a comment noting it contains database credentials.
   - If `.gitignore` does not exist, create one containing `.peek/`.
5. Prints a confirmation to stderr with the absolute path and a next-step
   hint to run `peek db add`.

All output uses `click.echo(..., err=True)` — stdout is the MCP channel.

### `src/peek/cli/__init__.py`

Import the `init` command from `peek.cli.init_cmd` and register it on the
`cli` group with `add_command`.

### Tests

`tests/cli/test_init.py` — use `click.testing.CliRunner`:

1. `test_init_creates_peek_dir` — run in a tmp dir. `.peek/` and
   `.peek/databases.toml` exist after. File contains `[databases` as
   commented example text.
2. `test_init_creates_gitignore` — no `.gitignore` before. After init,
   `.gitignore` exists and contains `.peek/`.
3. `test_init_appends_to_existing_gitignore` — `.gitignore` exists with
   other content. After init, original content preserved and `.peek/`
   appended.
4. `test_init_skips_gitignore_if_already_listed` — `.gitignore` already
   contains `.peek/`. After init, no duplicate entry.
5. `test_init_refuses_if_already_initialized` — `.peek/` exists. Command
   exits with code 1 and prints "Already initialized".
6. `test_init_output_goes_to_stderr` — `result.output` (stdout) is empty.

Use `CliRunner(mix_stderr=False)` to separate stdout and stderr. Use
the runner's `env` param or `monkeypatch.chdir` for cwd control. Import
the `cli` group from `peek.cli` and invoke it with `["init"]`.

## Constraints

- All output via `click.echo(..., err=True)` — stdout must remain clean.
- Use `pathlib.Path` for all file operations.
- The template file is static text, not generated via tomlkit — it is
  a comment-only example, not a valid config.
- Do not validate any database connection — this just creates files.

## Acceptance check

```bash
python -m pytest tests/cli/test_init.py -v
```

All tests pass.

## Out of scope

- `peek db add/remove/list` commands (later tasks).
- Connection validation or engine building.
- Modifications to the MCP server startup.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
