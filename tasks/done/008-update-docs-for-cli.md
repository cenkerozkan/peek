# 008 — Update docs to reflect the shipped admin CLI

## Goal

The roadmap, decisions log, and architecture docs accurately reflect that
the admin CLI (`peek init`, `peek db add/remove/list`) is implemented and
shipped, not deferred.

## Context

Tasks 001–007 implemented the full admin CLI. The docs still describe it as
"Later / deferred (not v1)" in the roadmap and reference it as future work
in several places. This task brings the docs in sync with reality.

The CLI uses Click, adds `tomlkit` for TOML writes, creates a `.peek/`
project directory via `peek init`, and manages database aliases via
`peek db add/remove/list`. All output goes to stderr (stdout is the MCP
channel). Connections are validated before persisting. Passwords are
collected interactively (never as CLI flags).

## Files

You may create or modify only these:

- `docs/roadmap.md` — modify: move the admin CLI item from "Later / deferred"
  into a completed section or mark it done
- `docs/decisions.md` — modify: update decision #7a scope/timing note to
  reflect that it is now implemented
- `docs/architecture.md` — modify: if it references the CLI as planned/future,
  update to reflect it exists
- `docs/structure.md` — modify: add `src/peek/cli/` to the package structure
  listing (it has `__init__.py`, `init_cmd.py`, `db.py`)
- `CLAUDE.md` — modify: update the status line if it says the CLI is not yet
  built. Add `cli/` to the "Where to look" table or key tech choices if
  appropriate (keep it lean — one line max)

## Specification

### `docs/roadmap.md`

Find the admin CLI entry under "Later / deferred (not v1)". Move it to a
completed state. It should reflect: implemented via tasks 001–007, uses
Click, project-local `.peek/` directory, fully interactive prompts,
connection validation before persist, restart required.

### `docs/decisions.md`

Decision #7a has a "Scope / timing" note saying the CLI is deferred until
the connection_registry interface solidifies. Update to note that it has
been implemented. Do not change the decision itself — only the status.

### `docs/architecture.md`

Search for any mention of the CLI as future/planned. If found, update to
reflect it exists. If the credential isolation section mentions the CLI,
verify it accurately describes how the CLI handles credentials (interactive
prompts, never in shell args, writes only to local registry file).

### `docs/structure.md`

Add `cli/` to the `src/peek/` package tree with its three files and a
one-line description of each:
- `__init__.py` — Click group, entry point routing, config path resolver
- `init_cmd.py` — `peek init` command
- `db.py` — `peek db add/remove/list` commands

### `CLAUDE.md`

Update the status line (currently says "Phases 0–8 shipped") to mention the
CLI. Keep it to a few words — e.g. "Phases 0–8 + admin CLI shipped". If the
"Key tech choices" section should mention Click, add one bullet.

## Constraints

- Do not change any code — this is a docs-only task.
- Keep `CLAUDE.md` lean. Push detail into `docs/`.
- Preserve the decision #7a reasoning and constraints — only update the
  implementation status.
- Run a consistency sweep: grep for "admin CLI" and "peek db" across all
  docs to catch any other stale references.

## Acceptance check

```bash
grep -i "later\|deferred" docs/roadmap.md | grep -i "admin cli\|peek db"
```

This should return no results (the CLI is no longer deferred).

## Out of scope

- Code changes of any kind.
- New doc files.
- Backlog updates (nothing was killed or suspended).

---

## Outcome

**Status:** done

**Files changed:**
- docs/roadmap.md (moved Admin CLI entry from "Later / deferred" to its own completed section)
- docs/decisions.md (updated decision #7a header with implementation date; updated scope/timing note)
- docs/architecture.md (removed "Not built now" from CLI reference in connection registry section)
- docs/structure.md (added `cli/` directory with `__init__.py`, `init_cmd.py`, `db.py`)
- CLAUDE.md (updated status line; added Click to Key tech choices)

**Acceptance check:** passed
```
$ grep -i "later\|deferred" docs/roadmap.md | grep -i "admin cli\|peek db"
(no output)
```

**Deviations:** none

**Problems:** none
