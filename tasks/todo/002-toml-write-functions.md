# 002 — Add TOML write and remove functions

## Goal

`config_file.py` gains `save_entry` and `remove_entry` functions so the CLI
can persist database additions and removals to the TOML registry file.

## Context

`src/peek/infra/config_file.py` currently has `load_registry(path)` which reads
the TOML file via pydantic-settings. There is no write path. The admin CLI
(later tasks) needs to add/remove entries and write them back.

The registry file uses TOML with a top-level `[databases]` table. Each
sub-table is named by alias and has a required `url` key, an optional
`dialect` key, and an optional `exclude_tables` key (list of strings).

The `DatabaseEntry` model in `src/peek/models/config.py` has `url`
(SecretStr, required), `dialect` (Optional str, defaults to None), and
`exclude_tables` (list of strings, defaults to empty).

**Credential isolation applies.** These functions write `url` to disk (that is
their job), but they must never log/print it. Error messages must name only
the alias and the file path, never the URL.

Line length 79. Use `typing` library, not PEP 604 pipes. Google-style
docstrings optional but encouraged.

## Files

You may create or modify only these:

- `src/peek/infra/config_file.py` — modify: add `save_entry`, `remove_entry`
- `tests/infra/test_config_file.py` — modify: add tests for both functions

## Specification

### `save_entry(path: Path, alias: str, entry: DatabaseEntry) -> None`

1. If `path` exists, open and parse it with tomlkit to preserve formatting.
2. If `path` does not exist, create a new tomlkit document with an empty
   `databases` table.
3. Build the entry as a dict with the URL extracted from the SecretStr via
   `get_secret_value()`. Include `dialect` only if it is not None. Include
   `exclude_tables` only if the list is non-empty.
4. Set the alias key under `databases` in the document.
5. Create parent directories if they do not exist.
6. Write the document back to the file with tomlkit.

Raises `ConfigError` if the existing file cannot be parsed.

### `remove_entry(path: Path, alias: str) -> None`

1. If `path` does not exist, raise `ConfigError`.
2. Parse with `tomlkit.load()`.
3. If `alias` is not in `doc["databases"]`, raise `ConfigError` with message
   `"No database with alias '{alias}' in {path}"`.
4. Delete `doc["databases"][alias]`.
5. Write back with `tomlkit.dump(doc, f)`.

Raises `ConfigError` for missing file, parse errors, or unknown alias.

### Tests

Add to `tests/infra/test_config_file.py`:

1. `test_save_entry_creates_new_file` — path does not exist, after call the
   file exists and `load_registry` can read the entry back.
2. `test_save_entry_appends_to_existing` — file has one entry, save a second,
   both are present.
3. `test_save_entry_overwrites_existing_alias` — save an entry with the same
   alias, new URL wins.
4. `test_save_entry_omits_defaults` — entry with no dialect and empty
   exclude_tables: the TOML should not contain those keys.
5. `test_remove_entry_removes_alias` — remove one of two entries, only the
   other remains.
6. `test_remove_entry_unknown_alias` — raises `ConfigError`.
7. `test_remove_entry_missing_file` — raises `ConfigError`.

All tests use `tmp_path` for the file. Use `load_registry` to verify
round-trips (do not re-parse TOML manually).

## Constraints

- Use `tomlkit` (not `tomli_w`) for format-preserving round-trips.
- `save_entry` must not destroy comments or formatting in existing files.
- Error messages must contain only alias and file path, never URLs.
- Do not import or use `ConnectionRegistry` — these are pure file I/O
  functions, no engine building or connection validation.

## Acceptance check

```bash
python -m pytest tests/infra/test_config_file.py -v
```

All tests pass, including the new ones.

## Out of scope

- Connection validation (the CLI command does that before calling these).
- CLI commands themselves (later tasks).
- Changes to `load_registry` or `DatabaseEntry`.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
