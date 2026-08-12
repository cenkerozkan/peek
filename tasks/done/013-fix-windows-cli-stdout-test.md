# 013 — Fix `test_add_output_goes_to_stderr` on Windows

## Goal

The test `test_add_output_goes_to_stderr` passes on Windows CI. It
currently fails because Click's `CliRunner` echoes user input to stdout
on Windows, even when the prompts themselves use `err=True`.

## Context

`peek db add` sends all its output to stderr via `click.echo(..., err=True)`
and `click.prompt(..., err=True)`. On Linux/macOS, `CliRunner` keeps
stdout completely empty. On Windows, the echoed input (what the user
"typed" at each prompt) appears in `result.stdout` — this is a Click
platform behavior, not a peek bug.

The test currently asserts `result.stdout == ""`, which fails on Windows
because stdout contains the echoed input values (`mydb`, `sqlite://`,
two blank lines).

The fix is to relax the stdout assertion: instead of requiring stdout to
be completely empty, assert that no peek-generated output appears in
stdout. The peek-generated messages are things like "Database 'mydb'
added" and "Restart the MCP server". The echoed input values are not
peek output — they come from Click's prompt echo.

## Files

You may create or modify only these:

- `tests/cli/test_db_add.py` — modify: change the stdout assertion in
  `test_add_output_goes_to_stderr`

## Specification

In `test_add_output_goes_to_stderr`, replace the assertion
`assert result.stdout == ""` with assertions that no peek-generated
output strings appear in stdout. Check that the following strings are
absent from `result.stdout`:

- `"added"` (from the success message)
- `"Restart"` (from the restart reminder)
- `"Alias"` (from prompt labels)
- `"Connection URL"` (from prompt labels)

Keep the existing assertion that `"mydb" in result.stderr` — that
confirms peek's own output goes to stderr.

Do not change any other tests in the file.

## Constraints

- Only modify the one assertion in the one test function.
- Do not change any production code.
- Do not change any other test files or test functions.
- The fix must work on Linux, macOS, and Windows.

## Acceptance check

```bash
uv run pytest tests/cli/test_db_add.py::test_add_output_goes_to_stderr -q
```

Must pass.

## Out of scope

- Production code changes.
- Other test files or test functions.
- Changes to how `peek db add` handles stdout/stderr.

---

## Outcome

**Status:** done

**Files changed:**
- tests/cli/test_db_add.py (modified)

**Acceptance check:** passed — `uv run pytest tests/cli/test_db_add.py::test_add_output_goes_to_stderr -q` passed (140 tests total)

**Deviations:** none

**Problems:** none
