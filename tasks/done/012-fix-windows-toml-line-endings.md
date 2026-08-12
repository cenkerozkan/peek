# 012 — Fix Windows line-ending double-conversion in TOML writes

## Goal

`save_entry` and `remove_entry` in `config_file.py` produce valid TOML on
Windows. Currently they corrupt the file on the second write, causing a
parse failure.

## Context

On Windows, `tomlkit.dump()` writes `\n` line endings. Python's text-mode
`open(path, "w")` then converts each `\n` to `\r\n`. On a subsequent
read-modify-write cycle, the existing `\r\n` sequences in the file survive
the read (tomlkit preserves them), and on the next text-mode write each
`\n` is converted again, producing `\r\r\n`. The stdlib TOML parser rejects
this with `"Invalid statement (at line 1, column 1)"`.

The reads (`open(path, "rb")`) are already binary-mode and correct. Only
the two writes need fixing.

This causes five test failures on Windows CI:
- `test_add_appends_to_existing`
- `test_add_output_goes_to_stderr`
- `test_save_entry_appends_to_existing`
- `test_save_entry_overwrites_existing_alias`
- `test_remove_entry_removes_alias`

All pass on Linux/macOS because text mode does not alter `\n` there.

## Files

You may create or modify only these:

- `src/peek/infra/config_file.py` — modify: change the two `open(path, "w")`
  calls to binary mode

## Specification

In `save_entry`, change the write call (currently `open(path, "w")`) to
`open(path, "wb")`. In `remove_entry`, do the same for its write call.

`tomlkit.dump()` accepts a binary-mode file object and writes UTF-8 with
`\n` line endings, which is the correct behavior on all platforms. No
other changes to these functions are needed.

Do not change the reads — they are already `"rb"` and correct.

## Constraints

- Only change the file-open mode on the two write calls. Do not refactor
  or restructure anything else.
- Do not modify any test files.
- The fix must work on Linux, macOS, and Windows.

## Acceptance check

```bash
uv run pytest tests/infra/test_config_file.py tests/cli/test_db_add.py -q
```

All tests must pass. On Linux this confirms no regression; on Windows CI
it confirms the fix.

## Out of scope

- Any test changes.
- Any other file modifications.
- Read-mode changes (already correct).

---

## Outcome

**Status:** done

**Files changed:**
- src/peek/infra/config_file.py (modified)

**Acceptance check:** passed

```
uv run pytest tests/infra/test_config_file.py tests/cli/test_db_add.py -q
..................                                                       [100%]
18 passed in 0.18s
```

**Deviations:** The task specification said to change `open(path, "w")` to `open(path, "wb")` and keep `tomlkit.dump()`. However, `tomlkit.dump()` only accepts a text-mode file object — it calls `fp.write(dumps(data))` which writes a string, not bytes. Using binary mode caused `TypeError: a bytes-like object is required, not 'str'`. The fix instead uses `tomlkit.dumps(doc).encode("utf-8")` to serialize the document to a string, encode it to UTF-8 bytes, and write the bytes directly to the binary file. This produces the same `\n` line endings on all platforms (including Windows), which is exactly what the task goal requires.

**Problems:** The task specification was slightly inaccurate — `tomlkit.dump()` cannot be used with binary-mode file objects. The approach of using `dumps()` + `.encode("utf-8")` achieves the same Windows fix without violating the task constraints (only changed the two write calls, no other refactoring).
