# CLAUDE.md

Entry point for AI agents working in this repo. Read this first, then open the
doc under `docs/` that matches your task. Keep this file short — it's loaded into
every session's context.

## What this project is

A **safe, multi-database, read-only SQL MCP server**: it exposes database
introspection and query-execution tools over any SQLAlchemy-supported database, so
an outer agent (Claude Code, Copilot) can do NL→SQL itself and run the result
safely. **v1 has no internal LLM** — the server is `SQLAlchemy` + `FastMCP` +
`sqlglot`. A human-facing interactive TUI (which *would* need its own NL→SQL brain)
may come later. See `docs/backlog.md` for the suspended internal-pipeline idea.

Status: **architecture/brainstorming phase** — no application code yet.

## Hard rules (do not violate)

- **Read-only.** Queries must never mutate data. Enforced two ways: a read-only DB
  role/grants, and a client-side SQL parse check that rejects any non-SELECT
  statement before execution. Never weaken or bypass either layer.
- **Multi-database.** The server connects to several databases at once, addressed by
  alias. Every tool takes a DB target param — don't hardcode a single connection.
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
  user directories via `platformdirs` (e.g. `user_config_dir("nl2sql")`), never a
  hardcoded `~/.config`.

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

`BRAINSTORM.md` is a scratchpad — it contains unsettled ideas and open questions.
Treat `docs/` as settled truth; treat `BRAINSTORM.md` as thinking-in-progress.

## Key tech choices

- **MCP framework:** FastMCP (reference docs vendored in `llm_friendly_docs/fastmcp.txt`).
- **DB access:** SQLAlchemy (dialect-agnostic), configured via connection strings.
- **Safety:** `sqlglot` parse check + read-only DB role.
- **No** LangChain/LangGraph in v1 (see `docs/backlog.md`).
