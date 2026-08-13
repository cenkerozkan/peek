# 017 — db commands must check for initialization before running

## Goal

All three `peek db` subcommands (`add`, `remove`, `list`) exit early with
a clear message when no config file exists, instead of falling through to
confusing errors.

## Context

`remove` and `list` already have this check: they call `resolve_config_path()`,
test `path.is_file()`, and print "No config file found. Run 'peek init' first."
before exiting with code 1.

`add` has no such check. If the `.peek/` directory doesn't exist, `add`
prompts the user for all four fields, tries to validate the connection,
and then fails with a `RegistryError` about not being able to connect.
The real problem is that peek isn't initialized, but the error message
says nothing about that.

The fix is straightforward: `add` should check for the config file the
same way `remove` and `list` do, before prompting for any input.

## Files

You may create or modify only these:

- `src/peek/cli/db.py` — modify: add init check to `add`
- `tests/cli/test_db_add.py` — modify: add test for the missing-config case

## Specification

### 1. Add init check to `add`

At the top of the `add` function, before the example preamble and before
any `click.prompt` calls, resolve the config path and check that the
file exists. If it does not, print a message to stderr and exit with
code 1.

The message and exit pattern should match what `remove` and `list`
already do:

```
No config file found. Run 'peek init' first.
```

Exit code 1, output to stderr (`err=True`).

Do this by calling `resolve_config_path()` and checking `.is_file()` on
the result, the same way `remove` does it. The import of
`resolve_config_path` is already used later in `add`; move it to the
top of the function body.

### 2. Add a test

Add a test to `tests/cli/test_db_add.py` that verifies the behavior
when no config file exists:

- Use `tmp_path` and `monkeypatch.chdir` to a directory with no `.peek/`
- Invoke `peek db add` with no input
- Assert exit code is 1
- Assert stderr contains "peek init"

Name the test `test_add_requires_init`.

## Constraints

- Do not change `remove` or `list`. They already work correctly.
- Do not change the check logic in `remove` or `list` to "share" a
  helper. The duplication is three lines; an abstraction is not worth it.
- The error message must go to stderr (`err=True`), consistent with all
  other CLI output.
- Do not prompt for any input before the check. The user should not be
  asked for alias, URL, etc. only to be told peek isn't initialized.

## Acceptance check

```bash
uv run pytest tests/cli/test_db_add.py -q
```

All tests pass, including the new `test_add_requires_init`.

## Out of scope

- Changing `resolve_config_path` itself.
- Adding auto-init behavior (running `peek init` automatically).
- Modifying `init_cmd.py`.
- Changes to `remove` or `list`.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
