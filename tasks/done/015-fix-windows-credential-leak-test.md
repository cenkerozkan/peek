# 015 — Fix Windows CI failure in test_add_hides_connection_url_in_error_message

## Goal

Make `test_add_hides_connection_url_in_error_message` pass on Windows CI
runners where Click's `CliRunner` concatenates all stderr output into a
single line.

## Context

Task 014 added prompt hints that include example URLs containing
"postgresql" (e.g. `postgresql+psycopg://user:pass@host/db`). The test
at `tests/cli/test_db_add.py:147` checks that the error line containing
"Could not connect to database" does not contain "postgresql" or the
password from the test input — verifying that credentials are not leaked
in error messages.

On Linux/macOS, `result.stderr.splitlines()` yields separate lines for
each prompt and the final error, so the assertion only inspects the error
line itself. On Windows, Click's `CliRunner` (without `mix_stderr`, which
the installed Click version does not support) concatenates all stderr
output into one blob. `splitlines()` still returns only one entry that
contains both the prompt hints and the error. The assertion then trips on
"postgresql" from the example URL in the prompt hint, not from a real
credential leak.

This is the same class of Windows/CliRunner issue that tasks 012 and 013
fixed.

## Files

You may create or modify only these:

- `tests/cli/test_db_add.py` — modify the
  `test_add_hides_connection_url_in_error_message` test

## Specification

The test must verify that the **error message itself** (the string
produced by the `RegistryError`) does not contain the connection URL or
password, without being tripped up by prompt hint text that happens to
share substrings.

The fix should extract just the error message portion from stderr rather
than scanning full lines. Two viable approaches (implementer's choice):

1. **Split on the known error prefix.** The error message always starts
   with "Could not connect to database". Take the substring from that
   prefix to the end (or to the next newline). Assert against that
   substring only.

2. **Match the error message with a regex.** Use a pattern like
   `r"Could not connect to database: \w+"` and assert against the
   matched text.

Either way, the assertions must still verify:
- The error message contains the alias (`mydb`).
- The error message does not contain `postgresql`.
- The error message does not contain the password (`p@ssw0rd`).
- The error message does not contain the full URL.

## Constraints

- Do not change the CLI code — the fix is in the test only.
- Do not skip the test on Windows.
- Do not add new dependencies.
- The test must still verify credential isolation (the original intent).

## Acceptance check

```bash
uv run pytest tests/cli/test_db_add.py::test_add_hides_connection_url_in_error_message -q
```

Should print `1 passed`.

## Out of scope

- Changing the prompt hint text from task 014.
- Upgrading Click to a version that supports `mix_stderr`.
- Other test fixes unrelated to this specific failure.

---

## Outcome

**Status:** done

**Files changed:**
- tests/cli/test_db_add.py (modified — test_add_hides_connection_url_in_error_message)

**Acceptance check:** passed — `uv run pytest tests/cli/test_db_add.py::test_add_hides_connection_url_in_error_message -q` prints `1 passed`

**Deviations:** none

**Problems:** none
