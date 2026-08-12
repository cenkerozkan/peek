# 006 — `peek db remove` command

## Goal

`peek db remove` lets the user remove a database alias from the TOML
registry file.

## Context

Task 002 added `remove_entry` to `config_file.py`. Task 003 added
`resolve_config_path`. Task 005 created the `db` Click group in
`src/peek/cli/db.py`. This task adds a `remove` subcommand to that group.

The command should show the user which aliases exist, let them pick one,
and remove it from the TOML file. No connection is opened — this is a
pure file operation.

Line length 79. `typing` library. All CLI output to stderr.

## Files

You may create or modify only these:

- `src/peek/cli/db.py` — modify: add `remove` subcommand to `db` group
- `tests/cli/test_db_remove.py` — new

## Specification

### `remove` subcommand in `src/peek/cli/db.py`

1. Resolve the config path using `resolve_config_path()`.
2. If the file does not exist, print an error to stderr (`"No config file
   found. Run 'peek init' first."`) and exit with code 1.
3. Load the current entries using `load_registry(path)` to get the alias
   list. Print the available aliases to stderr.
4. Prompt for the alias to remove via `click.prompt`.
5. Call `remove_entry(path, alias)` from `peek.infra.config_file`.
   If it raises `ConfigError` (unknown alias), print the error to stderr
   and exit with code 1.
6. Print a success message to stderr: the alias was removed, restart the
   MCP server for changes to take effect.

All output uses `click.echo(..., err=True)`.

### Tests

`tests/cli/test_db_remove.py` — use `click.testing.CliRunner`:

1. `test_remove_existing_alias` — set up a TOML with two entries. Provide
   input to remove one. Verify only the other remains in the file.
2. `test_remove_unknown_alias` — set up a TOML with one entry. Provide a
   non-existent alias. Command exits with code 1.
3. `test_remove_no_config_file` — no TOML file exists. Command exits with
   code 1 and mentions `peek init`.
4. `test_remove_shows_available_aliases` — verify the stderr output lists
   the available aliases before prompting.

Use `monkeypatch.chdir(tmp_path)` and create `.peek/databases.toml`
manually with known content for setup.

## Constraints

- All output to stderr.
- No connection is opened — this is a file-only operation.
- Credential isolation: never print URLs. Only print aliases.
- Do not modify `remove_entry` or `load_registry`.

## Acceptance check

```bash
python -m pytest tests/cli/test_db_remove.py -v
```

All tests pass.

## Out of scope

- `peek db list` (next task).
- Connection validation.
- Live reload of the MCP server.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to done/ -->

**Status:** done

**Files changed:**
- src/peek/cli/db.py (modified: added `remove` subcommand, added `remove_entry` to imports)
- tests/cli/test_db_remove.py (new)

**Acceptance check:** passed
```
============================= test session starts ==============================
platform linux - Python 3.13.14, pytest-9.1.1, pluggy-1.6.1
rootdir: /home/issola/Desktop/peek
configfile: pyproject.toml
collected 4 items

tests/cli/test_db_remove.py ....                                          [100%]

============================== 4 passed in 0.15s ==============================
```

**Deviations:** none

**Problems:** none
