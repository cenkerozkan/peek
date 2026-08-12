# 007 — `peek db list` command

## Goal

`peek db list` shows all configured database aliases and their dialects,
without exposing connection strings.

## Context

Task 005 created the `db` Click group in `src/peek/cli/db.py`. This task
adds a `list` subcommand. It reads the TOML file and displays a table of
aliases — no connection is opened, no engine is built.

The `DatabaseEntry` model has `url` (SecretStr), `dialect` (optional str),
and `exclude_tables` (list). The `list` command shows alias and dialect
only — never the URL.

Line length 79. `typing` library. All CLI output to stderr.

## Files

You may create or modify only these:

- `src/peek/cli/db.py` — modify: add `list` subcommand (name it `list_`
  or use `@db.command("list")` to avoid shadowing the builtin)
- `tests/cli/test_db_list.py` — new

## Specification

### `list` subcommand in `src/peek/cli/db.py`

1. Resolve the config path using `resolve_config_path()`.
2. If the file does not exist, print `"No config file found. Run
   'peek init' first."` to stderr and exit with code 1.
3. Load entries using `load_registry(path)`.
4. For each alias, print a line to stderr showing the alias and the
   dialect (if configured, otherwise show `"auto"`). Format as a simple
   aligned table with a header row and a separator line.
5. If the registry is empty (which `load_registry` rejects), handle the
   `ConfigError` and print `"No databases configured. Run 'peek db add'."`

All output uses `click.echo(..., err=True)`.

### Tests

`tests/cli/test_db_list.py` — use `click.testing.CliRunner`:

1. `test_list_shows_aliases` — set up a TOML with two entries (one with
   dialect, one without). Verify both aliases appear in stderr output.
2. `test_list_shows_dialect` — entry with `dialect = "postgres"`. Verify
   `"postgres"` appears in output.
3. `test_list_auto_dialect` — entry without dialect field. Verify `"auto"`
   appears in output.
4. `test_list_no_config_file` — no TOML file. Command exits with code 1.
5. `test_list_no_urls_in_output` — set up entries with known URLs. Verify
   no URL substring appears anywhere in stdout or stderr.

## Constraints

- All output to stderr.
- **Credential isolation**: never print URLs. This is the most important
  constraint. The test `test_list_no_urls_in_output` must verify this.
- No connection is opened — this is a file-read-only operation.
- Do not modify `load_registry` or any other existing function.

## Acceptance check

```bash
python -m pytest tests/cli/test_db_list.py -v
```

All tests pass.

## Out of scope

- Connection validation or engine building.
- Rich/colored output — plain text is fine for now.
- Changes to existing functions.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
