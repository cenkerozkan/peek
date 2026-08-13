# 015a — Update README to reflect CLI commands and new docs

## Goal

Bring `../../README.md` up to date with the CLI that shipped in Phases 7–8 and
the new `../../docs/testing-installation.md` guide.

## Context

The README was written before the CLI existed. It tells users to create
`databases.toml` by hand in a platform-specific config directory. The
project now has `peek init` and `peek db add/remove/list`, which are the
intended way to set up and manage databases. The README should lead with
the CLI workflow and keep manual TOML editing as a secondary alternative.

Additionally, `../../docs/testing-installation.md` was added recently but is
not listed in the Documentation table at the bottom of the README.

## Files

You may create or modify only this:

- `../../README.md`

## Specification

### 1. Add a "Quick start" or "Getting started" section

After the Install section (and its Database drivers subsection), add a
short section that walks through the CLI-based setup flow:

```
## Quick start

peek init
peek db add
```

Show the `peek init` command, then `peek db add` (which prompts
interactively). Mention that `peek db list` shows what's registered and
`peek db remove` removes an entry.

Keep it short — three or four commands with one-line explanations.

### 2. Update "Configure your databases"

The current section tells users to manually create `databases.toml` in
a platform-specific directory. Rewrite it so the primary path is:

1. `peek init` (creates `.peek/databases.toml` in the current project), or
2. `peek db add` (interactive prompts, validates the connection).

Mention that `peek init` creates a `.peek/` directory in the current
project with a `databases.toml` template inside it, and that `.peek/`
is automatically added to `../../.gitignore` (since it holds credentials).
This is the project-local config path — distinct from the platform
config directory (`~/.config/peek/`, `~/Library/Application Support/peek/`,
etc.), which is also supported.

Then keep the manual TOML editing as a secondary option for users who
prefer it or need to script setup. The existing TOML example and field
documentation (`url`, `exclude_tables`, `dialect`) should remain — just
reframe it as "you can also edit `.peek/databases.toml` directly".

The platform-specific paths table and `PEEK_CONFIG_FILE` info should
stay, but move after the CLI-first explanation. Clarify the lookup
order: `PEEK_CONFIG_FILE` env var first, then `.peek/databases.toml`
in the current directory, then the platform config directory.

### 3. Update the Documentation table

Add a row for `../../docs/testing-installation.md`:

```
| Testing & installation from TestPyPI    | `docs/testing-installation.md` |
```

### 4. Add a CLI reference section (optional, lightweight)

If it fits naturally, add a small section or subsection listing the
available CLI commands:

```
| Command          | What it does                                |
| ---------------- | ------------------------------------------- |
| `peek`           | Start the MCP stdio server                  |
| `peek --version` | Show the installed version                  |
| `peek init`      | Create a .peek/ config directory            |
| `peek db add`    | Add a database connection interactively     |
| `peek db remove` | Remove a database connection                |
| `peek db list`   | List configured databases and their dialects|
```

This is optional — if the quick start section already covers it
adequately, skip the table.

## Constraints

- Do not change any code files.
- Do not remove existing content — update it. The TOML example, field
  docs, editor configs, tools table, settings table, and safety model
  section must all remain.
- Keep the README's existing tone and structure. It reads well — the
  changes are additive/reframing, not a rewrite.
- Do not add badges, screenshots, or external links beyond what already
  exists.

## Acceptance check

```bash
python -c "
content = open('README.md').read()
assert 'peek init' in content, 'README should mention peek init'
assert 'peek db add' in content, 'README should mention peek db add'
assert 'peek db remove' in content, 'README should mention peek db remove'
assert 'peek db list' in content, 'README should mention peek db list'
assert 'testing-installation' in content, 'README should link testing-installation.md'
print('All checks passed')
"
```

## Out of scope

- Changes to any Python code or test files.
- Adding a CHANGELOG or release notes.
- Restructuring the docs/ directory.

---

## Outcome

**Status:** done

**Files changed:**
- README.md (modified — added Quick start, CLI reference, updated Configure your databases, added testing-installation.md to docs table)

**Acceptance check:** passed — `python -c "..."` prints `All checks passed`

**Deviations:** none

**Problems:** none
