# CLAUDE.md

**Orchestrator of this project.** This file is the central entry point for all AI
agents working in this repo. It sets the hard rules, delegates to specialized
agents, and is loaded into every session's context. Read this first, then open
the doc under `docs/` that matches your task.

## What this project is

A **safe, multi-database, read-only query MCP server**: it exposes database
introspection and query-execution tools over any SQLAlchemy-supported database —
and, from Phase 11, **MongoDB** — so an outer agent (Claude Code, Copilot) can do
NL→query itself and run the result safely. **v1 has no internal LLM** — the server
is `SQLAlchemy` + `FastMCP` + `sqlglot` (+ `pymongo`, planned). A human-facing
interactive TUI (which *would* need its own NL→SQL brain) may come later. See
`docs/backlog.md` for the suspended internal-pipeline idea.

Status: **Phases 0–8 + admin CLI shipped** (SQL backends, all 5 tools, CLI, packaging,
CI). Not yet
published to PyPI. Phases 9–11 (publish, backend refactor, MongoDB) are next — see
`docs/roadmap.md`.

Distribution name: **`peek-db`** on PyPI (`peek` and `peek-mcp` are taken; the
earlier `peek-sql` was dropped when NoSQL landed on the roadmap — decision #19).
The import package and console command are both `peek`.

## Hard rules (do not violate)

- **Read-only.** Queries must never mutate data. Enforced two ways: a read-only DB
  role/grants, and a client-side check that rejects anything non-read-only before
  execution. Never weaken or bypass either layer. **What the client-side check *is*
  differs per backend**: for SQL, a `sqlglot` parse check rejecting any non-SELECT;
  for Mongo, an **operation allowlist** — and note that an aggregation pipeline is
  *not* inherently a read (`$out`/`$merge` write; `$out` replaces a whole
  collection). See `docs/decisions.md` #22.
- **One chokepoint.** Every query path goes through `query_service`, which calls the
  backend's `validate` before its `execute`. Backend-specific knowledge lives *only*
  in `backends/`. If a service needs an `if backend == ...` branch, the `Backend`
  protocol is missing a method — add it there instead.
- **Multi-database.** The server connects to several databases at once, addressed by
  alias. Every tool takes a DB target param — don't hardcode a single connection.
  The alias also selects the **query language** (SQL vs. Mongo), so don't assume SQL.
- **No internal LLM (v1).** The server does not generate SQL or reason with an LLM;
  the outer agent does that. Don't add an in-server LLM/agent/pipeline. (The
  suspended NL→SQL pipeline lives in `docs/backlog.md` with its revival condition.)
- **Credential isolation.** Connection strings hold passwords. No tool return value
  or error message may ever contain one — the LLM (and thus the remote model API)
  sees only DB aliases. Scrub connection URLs from errors before returning them.
  `list_databases` returns aliases only. Credentials live solely in the local
  registry, never in the repo or the MCP launch config.
  See `docs/architecture.md` → Credential isolation.
- **Cross-platform.** Users run Windows and macOS (rarely Linux). Use `pathlib.Path`
  for all path work — never string concatenation or hardcoded `/` or `\`. Resolve
  user directories via `platformdirs` (e.g. `user_config_dir("peek")`), never a
  hardcoded `~/.config`.

## Agent orchestration

The main session (Opus) is the **orchestrator**: it plans, explores, makes
design decisions, and delegates implementation work to specialized agents.
Do not implement code or update docs yourself unless the user explicitly asks.

| Agent                | Role                                      | When to delegate                                    |
| -------------------- | ----------------------------------------- | --------------------------------------------------- |
| `clean-python-writer`| Writes/refactors Python code              | Any new module, function, or refactor in `src/peek/` |
| `doc-updater`        | Keeps docs accurate after code/design changes | After code lands or a design decision is settled    |

**Workflow**: orchestrator explores & plans → user approves → delegate to
`clean-python-writer` for implementation → delegate to `doc-updater` for
docs → orchestrator verifies results and reports back.

**Task protocol:** work is tracked as numbered task files under `tasks/`.
Read `tasks/README.md` for the protocol, `tasks/Orchestrator.md` for the
orchestrator role, and `tasks/TEMPLATE.md` when writing new task specs.

## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the
repo root), reach for it BEFORE grep/find or reading files when you need to
understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions
  in one call — the relevant symbols' verbatim source plus the call paths between
  them, including dynamic-dispatch hops grep can't follow. Name a file or symbol
  in the query to read its current line-numbered source.
- **Shell** (always works): `codegraph explore "<symbol names or question>"`
  prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is
the user's decision.

## Where to look

| Topic                                    | File                      |
| ---------------------------------------- | ------------------------- |
| Architecture: layers, interfaces, safety | `docs/architecture.md`    |
| Repo / package structure & layer rules   | `docs/structure.md`       |
| Decision log (what we chose + why)       | `docs/decisions.md`       |
| Killed / suspended ideas (+ revival)     | `docs/backlog.md`         |
| Code conventions / dev rules             | `docs/conventions.md`     |
| Domain glossary                          | `docs/glossary.md` _(planned)_    |
| Freeform working notes / open questions  | `BRAINSTORM.md`           |
| Vendored FastMCP reference docs          | `llm_friendly_docs/`      |
| Task protocol & templates               | `tasks/`                  |
| Orchestrator role guide                  | `tasks/Orchestrator.md`   |

`BRAINSTORM.md` is a scratchpad — it contains unsettled ideas and open questions.
Treat `docs/` as settled truth; treat `BRAINSTORM.md` as thinking-in-progress.

## Key tech choices

- **CLI:** Click — admin commands (`peek init`, `peek db add/remove/list`).
- **MCP framework:** FastMCP (reference docs vendored in `llm_friendly_docs/fastmcp.txt`).
- **DB access:** SQLAlchemy (dialect-agnostic) for SQL; `pymongo` for Mongo
  (planned). Both sit behind the `Backend` protocol in `backends/` — services never
  touch either directly. Configured via connection strings.
- **Safety:** read-only DB role (always) + a per-backend client-side check —
  `sqlglot` parse check for SQL, operation allowlist for Mongo.
- **No** LangChain/LangGraph in v1 (see `docs/backlog.md`).
