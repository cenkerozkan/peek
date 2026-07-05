# Architecture

Settled architecture for the NL-to-SQL MCP server. For unsettled ideas and open
questions, see `../BRAINSTORM.md`. For the *why* behind choices, see `decisions.md`.
For removed/deferred ideas, see `backlog.md`.

## Overview

A **safe, multi-database, read-only SQL MCP server**. It exposes database
introspection and query-execution tools over any SQLAlchemy-supported database. The
consuming agent (Claude Code, Copilot) does the NL→SQL reasoning itself; this server
gives it a clean, safe way to explore schemas and run the resulting SQL.

**v1 has no internal LLM.** The stack is `SQLAlchemy` + `FastMCP` + `sqlglot`. (An
in-server NL→SQL pipeline was considered and suspended — running an LLM agent inside
a tool already driven by an agent is wasteful. See `backlog.md`.)

The server connects to **multiple databases at once**, addressed by alias. All query
execution is **read-only**.

Transport: **local stdio** to start (the consuming agent launches the server as a
subprocess). No network/auth layer yet — but nothing in the core is coupled to
stdio, so an HTTP transport can be added later.

## MCP tools

All tools are read-only and take a DB alias param (multi-database):

- `list_databases()` — discover configured aliases (+ safe metadata like dialect).
- `list_tables(db)` — list tables in a database.
- `get_schema(db, ...)` — return structured columns (plus primary/foreign keys)
  for tables; scope large schemas with an explicit table selector or
  `limit`/`offset` pagination.
- `validate_sql(db, sql)` — parse-check a statement (is it a safe, read-only SELECT?)
  without running it.
- `run_sql(db, sql)` — validate then execute a read-only query; return rows (capped).

There is intentionally **no coarse `ask_database` tool** in v1 — that required an
internal LLM. The outer agent composes the tools above itself.

## Layered architecture

Classic layered structure (analogous to FastAPI `router -> service -> repository`).
Tools stay thin; all logic lives in shared services.

```
┌─────────────────────────────────────────────────────────────┐
│ MCP tool layer (FastMCP)                                     │
│   thin, agent-facing. Validates params, calls a service,     │
│   shapes the response. Docstrings ARE the interface contract.│
│   list_databases · list_tables · get_schema ·                │
│   validate_sql · run_sql                                     │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Service layer                                                │
│   connection_registry  alias -> engine                       │
│   schema_service       introspection (list tables, schema)   │
│   sql_service          validate (read-only check) + execute  │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Infrastructure                                               │
│   SQLAlchemy engines · config-file reader                    │
└─────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

- **MCP tool layer** — thin, like FastAPI routers. No business logic in tool bodies.
  Each tool: validate/normalize params, call a service, format the result for the
  agent (including structured, actionable errors — never raw exceptions). Every tool
  takes a DB alias param. Tool docstrings are a first-class design artifact: the
  agent chooses tools by reading them.
- **Service layer** — all business logic. `sql_service` and `schema_service` are the
  workhorses; `connection_registry` resolves aliases to engines.
- **Infrastructure** — long-lived resources: SQLAlchemy engines, the config-file
  reader.

### Key invariant: safety lives in the service layer

The read-only enforcement (SQL parse check rejecting non-SELECT) lives inside
`sql_service`, which calls `safety/guard.py`. **Every path that executes SQL goes
through `sql_service`.** It is impossible to execute SQL without passing the check.
Combined with a read-only DB role, that's the two-layer safety model.

### Table exclusion (third safety layer)

Each alias may declare a per-database `exclude_tables` denylist (see decision
#16). It is **not model-facing**: `is_excluded(alias, table)` on the connection
registry is the single source of truth both `schema_service` and `sql_service`
consult. Excluded tables are omitted from `list_tables`, rejected by `get_schema`
(as if they do not exist), scrubbed from other tables' foreign keys, and rejected
at execution — so an excluded table's very existence never reaches the model.

## Multi-database

- Connections configured via **connection strings** (SQLAlchemy URLs), loaded as
  `{alias -> engine}` into the `connection_registry` at startup.
- Every tool takes a DB alias param. `list_databases` lets a caller discover aliases.
- Current scope: **one database per request** (pick which DB). Cross-database joins
  are out of scope — SQLAlchemy can't join across separate engines without a
  federation layer. Revisit if a real need appears.

### Connection registry (config-driven, startup)

- Databases are addressed by a friendly alias (like `psql`'s `.pg_service.conf` or
  DBeaver's saved connections). Callers never handle raw connection strings.
- **Source of truth:** a user-maintained **config file** mapping
  `alias -> connection string` (e.g. TOML/JSON). Hand-maintained for now.
  Machine-local and **never** committed to the repo.
- **Config file path** is supplied via the **MCP launch config** in the IDE (arg or
  env, e.g. `.mcp.json`). Only the *path* goes there — never the connection strings
  themselves (they would risk being committed; see Credential isolation).
- **Startup flow:** on boot the server reads the config file, validates each
  connection, and builds the in-memory `connection_registry`. No dynamic runtime
  registration.
- **Registration is NOT a model-facing tool.** The agent must not add/remove
  connections. `register_database` / `remove_database` are not MCP tools. The only
  registry tool exposed is **`list_databases`** (read-only).
- **Future-proofing:** add/remove logic lives in `services/connection_registry.py`
  behind a clean interface, so a later non-model **admin CLI**
  (`peek db add/remove/list`) can reuse it. The CLI is a human tool (never an MCP
  tool), writes credentials only to the local config file, and requires an MCP-server
  **restart to take effect** — no live reload in v1. Not built now. See
  `decisions.md` #7a.
- **Cross-platform paths:** any default/derived config location is resolved with
  `platformdirs` (`user_config_dir("peek")`) — OS-correct on Windows/macOS/Linux —
  and all path handling uses `pathlib.Path`. (Most users are on Windows/macOS.)

## Credential isolation (hard rule)

Connection strings contain passwords. The one boundary that actually prevents a
credential leak to a remote model provider is **tool output**, not storage.

Why: an MCP client (Claude Code, Copilot) sends whatever a tool **returns** —
including error messages — back to the LLM as context, which travels to the model
API. The local config file never leaves the machine; a connection string echoed in a
tool result does.

Rules — do not violate:

- **No tool return value or error message may ever contain a connection string.**
  Callers see only aliases. Connection strings live solely inside the server process,
  used to build SQLAlchemy engines.
- **`list_databases` returns aliases only** (plus safe metadata like dialect).
- **Scrub errors before returning them.** SQLAlchemy exceptions can echo the
  connection URL (it masks the password as `***` by default, but sanitize anyway) —
  strip any URL/credential material from anything returned to the caller.
- **Never place credentials in the MCP launch config** (`.mcp.json` `env` block, etc.)
  if that file could be committed to git. Credentials live only in the local config
  file, which stays out of the repo.

## Large schemas

`get_schema` supports plain pagination/filter params so an agent can pull only the
tables it needs. There is **no embedding-based retrieval** in v1 — that existed to
bound an internal LLM's prompt, which no longer exists. The outer agent manages its
own context. (Suspended; see `backlog.md`.)

## Server lifecycle

Long-lived resources — the connection registry (engines) — are built **once at
startup** via FastMCP's lifespan/context and injected into tools and services. Never
created per-call (engines are expensive and pooled).

## Interfaces

- **MCP server (FastMCP)** — built first. Reference docs vendored in
  `../llm_friendly_docs/fastmcp.txt`.
- **Interactive TUI** — later, on top of the same core (Claude-Code-style
  conversational terminal, not a one-shot CLI). This *would* reintroduce an internal
  NL→SQL brain (see `backlog.md`). Framework TBD.

## Tech stack

- **MCP:** FastMCP
- **DB access:** SQLAlchemy (dialect-agnostic), connection strings
- **DB drivers:** DBAPI drivers are **optional extras** (SQLAlchemy ships dialects,
  not drivers). Supported v1 backends: PostgreSQL (`postgres` → `psycopg[binary]`),
  MySQL/MariaDB (`mysql` → `pymysql`), SQL Server (`mssql` → `pyodbc`), Oracle
  (`oracle` → `oracledb`); SQLite needs no install (stdlib). See `decisions.md` #13.
- **Safety:** read-only DB role + client-side parse check (`sqlglot`)
- **Paths/config:** `pathlib` + `platformdirs`
- **Config/models:** `pydantic` + `pydantic-settings` (connection URLs as `SecretStr`)
- **No** LangChain / LangGraph / embeddings / vector store in v1 (see `backlog.md`)
