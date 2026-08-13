# 009a — Fix ty type errors in config file tests

## Goal

The four `ty` type errors in `tests/infra/test_config_file.py` are resolved
so that `uv run ty check src tests` passes with zero diagnostics.

## Context

`DatabaseEntry.url` is typed as `SecretStr` (from pydantic). Four test
functions pass raw string literals instead of wrapping them in
`SecretStr(...)`. Pydantic coerces the strings at runtime so the tests
pass, but `ty` correctly flags the type mismatch at static analysis time.

The fix is to wrap each raw string in `SecretStr(...)` at the call site.
The `SecretStr` import already exists in the file (it is used elsewhere).
If not, add it from `pydantic`.

The four call sites are on lines 78, 91, 103, and 114 — each is a
`DatabaseEntry(url="...")` call where the string literal must become
`SecretStr("...")`.

## Files

You may create or modify only these:

- `tests/infra/test_config_file.py` — modify: wrap four raw URL strings
  in `SecretStr(...)`

## Specification

In each of the four `DatabaseEntry(url=...)` calls flagged by `ty`, change
the bare string literal to `SecretStr(<same string>)`. If `SecretStr` is
not already imported in the file, add `from pydantic import SecretStr` to
the imports.

Do not change anything else in these tests — no logic changes, no
renames, no reformatting of surrounding code.

## Constraints

- Only change the four flagged lines (plus an import if needed).
- Do not modify any production code.
- Do not modify any other test files.

## Acceptance check

```bash
uv run ty check src tests
```

Must produce zero diagnostics.

## Out of scope

- Any production code changes.
- Any other test files.
- Refactoring or reformatting beyond the four fixes.

---

## Outcome

**Status:** done

**Files changed:**
- `tests/infra/test_config_file.py` (modified)

**Acceptance check:** passed

**Deviations:** none

**Problems:** none
