# 017 — db commands must check for initialization before running

## Goal

All three `peek db` subcommands (`add`, `remove`, `list`) exit early with
a clear message when peek is not initialized. Two checks are required:
the `.peek/` directory must exist, and `databases.toml` must exist inside
it. The check logic lives in a dedicated module, not inline in each
command.

## Context

If the `.peek/` directory doesn't exist and you run `peek db add`, the
command prompts for all four fields and then fails with a misleading
connection error. The real problem is that peek isn't initialized.

`remove` and `list` have inline checks for the config file, but they
only check the file, not the directory. Both checks matter: the
directory is what `peek init` creates, and the file is what holds the
registry. A missing directory means peek was never initialized. A
missing file inside an existing directory means something got corrupted
or deleted.

Rather than duplicating check logic across three commands, extract it
into `../../src/peek/cli/checks.py`. Each db command calls the check function
at the top of its body. This keeps the commands focused on their own
job.

## Files

You may create or modify only these:

- `../../src/peek/cli/checks.py` — new: preflight check functions
- `../../src/peek/cli/db.py` — modify: use checks from `checks.py` in all
  three commands
- `../../tests/cli/test_db_add.py` — modify: add tests for missing-dir and
  missing-file cases

## Specification

### 1. Create `../../src/peek/cli/checks.py`

Create a module with a function that verifies peek is initialized. The
function should:

- Resolve the config path using `resolve_config_path()` from
  `peek.cli`.
- Check that the parent directory of the resolved path exists (this is
  the `.peek/` directory for the local config case).
- Check that the config file itself exists.
- If either check fails, print a message to stderr and exit with
  code 1.

When the directory does not exist, the message should be:

```
peek is not initialized. Run 'peek init' first.
```

When the directory exists but the file does not, the message should be:

```
No config file found. Run 'peek init' first.
```

Both messages go to stderr (`err=True`), exit code 1.

The function should return the resolved config path on success, so
callers can use it directly without calling `resolve_config_path`
again.

### 2. Update `../../src/peek/cli/db.py`

Replace the inline init/config checks in all three commands with a call
to the check function from `checks.py`:

- `add`: call the check at the top of the function, before the example
  preamble and before any prompts. Use the returned path instead of
  calling `resolve_config_path()` later.
- `remove`: replace the existing `path.is_file()` check and the
  `ConfigError` catch with a call to the check function. Use the
  returned path for the rest of the function.
- `list`: same as `remove`.

After this change, none of the three commands should import or call
`resolve_config_path` directly. That import moves to `checks.py`.

### 3. Add tests

Add two tests to `../../tests/cli/test_db_add.py`:

**`test_add_requires_init_no_dir`**: no `.peek/` directory exists.
Invoke `peek db add` with no input. Assert exit code 1, stderr
contains "peek init".

**`test_add_requires_init_no_file`**: `.peek/` directory exists but
`databases.toml` does not. Invoke `peek db add` with no input. Assert
exit code 1, stderr contains "peek init".

## Constraints

- The check function must be called at the very top of each command's
  function body, before any prompts, file reads, or other logic.
- All CLI output goes to stderr (`err=True`).
- Do not add auto-init behavior. The check exits; it does not offer to
  run `peek init` for you.
- Do not modify `init_cmd.py` or `resolve_config_path`.
- Do not modify `__init__.py` in `cli/` beyond what is needed.

## Acceptance check

```bash
uv run pytest tests/cli/test_db_add.py -q
```

All tests pass, including the two new tests.

## Out of scope

- Changing `resolve_config_path` itself.
- Adding auto-init behavior.
- Modifying `init_cmd.py`.
- Tests for `remove` and `list` preflight (they use the same function;
  testing through `add` is sufficient).

---

## Outcome

**Status:** done

**Files changed:**
- `../../src/peek/cli/checks.py` (new: preflight check function `require_config()`)
- `../../src/peek/cli/db.py` (modified: all three commands use `require_config()`, removed inline checks, removed `resolve_config_path` imports)
- `../../tests/cli/test_db_add.py` (modified: renamed `test_add_requires_init` to `test_add_requires_init_no_dir`, updated assertion for "peek is not initialized", added `test_add_requires_init_no_file`)

**Acceptance check:** passed

```
$ uv run pytest tests/cli/test_db_add.py -q
........                                                                 [100%]
8 passed in 0.15s

$ uv run pytest -q
........................................................................ [ 50%]
......................................................................   [100%]
142 passed in 1.19s
```

**Deviations:** none

**Problems:** The `require_config()` function uses a lazy import of `resolve_config_path` inside the function body to avoid circular import (because `checks.py` is imported by `db.py`, which is imported by `cli/__init__.py`, which defines `resolve_config_path`). This is the minimal fix — a cleaner long-term solution would be to move `resolve_config_path` to a separate module that doesn't depend on `cli/__init__.py`'s import order.
