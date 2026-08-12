# Architecture

Settled architecture for the NL-to-SQL MCP server. For unsettled ideas and open
questions, see `../BRAINSTORM.md`. For the *why* behind choices, see `decisions.md`.
For removed/deferred ideas, see `backlog.md`.

## Overview

A **safe, multi-database, read-only query MCP server**. It exposes database
introspection and query-execution tools over any SQLAlchemy-supported database —
and, from Phase 11, over MongoDB. The consuming agent (Claude Code, Copilot) does
the NL→query reasoning itself; this server gives it a clean, safe way to explore
schemas and run the result.

**v1 has no internal LLM.** The stack is `SQLAlchemy` + `FastMCP` + `sqlglot`
(+ `pymongo`, planned). (An in-server NL→SQL pipeline was considered and suspended —
running an LLM agent inside a tool already driven by an agent is wasteful. See
`backlog.md`.)

The server connects to **multiple databases at once**, addressed by alias. All query
execution is **read-only**.

Transport: **local stdio** to start (the consuming agent launches the server as a
subprocess). No network/auth layer yet — but nothing in the core is coupled to
stdio, so an HTTP transport can be added later.

## MCP tools

All tools are read-only and take a DB alias param (multi-database):

- `list_databases()` — discover configured aliases (+ safe metadata: `backend` and
  `dialect`).
- `list_tables(db)` — list tables (SQL) or collections (Mongo) in a database.
- `get_schema(db, ...)` — return structured columns (plus primary/foreign keys)
  for tables; scope large schemas with an explicit table selector or
  `limit`/`offset` pagination. For Mongo the schema is **inferred by sampling**
  documents, and is marked as such (decision #22).
- `validate_query(db, query)` — check a statement is safe and read-only, without
  running it.
- `run_query(db, query)` — validate then execute a read-only query; return rows
  (capped).

**The `query` argument's language is chosen by the alias**, not by the tool: SQL for
a SQL alias, a Mongo query document for a Mongo alias. `list_databases` reports each
alias's `backend` so the agent knows which to write. Writing SQL at a Mongo alias
fails closed, with a rejection message naming the expected language (decision #21).

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
│   validate_query · run_query                                 │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Service layer            (backend-agnostic)                  │
│   connection_registry  alias -> Backend                      │
│   schema_service       introspection (list tables, schema)   │
│   query_service        validate (read-only check) + execute  │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Backend layer (port/adapter)   ← the Backend protocol        │
│   SqlBackend     SQLAlchemy engine + sqlglot guard           │
│   MongoBackend   pymongo + operation-allowlist guard (planned)│
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Infrastructure                                               │
│   SQLAlchemy engines · Mongo clients · config-file reader    │
└─────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

- **MCP tool layer** — thin, like FastAPI routers. No business logic in tool bodies.
  Each tool: validate/normalize params, call a service, format the result for the
  agent (including structured, actionable errors — never raw exceptions). Every tool
  takes a DB alias param. Tool docstrings are a first-class design artifact: the
  agent chooses tools by reading them.
- **Service layer** — all business logic, and **no knowledge of any specific
  backend**. `query_service` and `schema_service` are the workhorses;
  `connection_registry` resolves aliases to backends.
- **Backend layer** — the port/adapter seam (decision #20). One `Backend` protocol —
  `list_tables` · `get_schema` · `validate` · `execute` · `dispose` — with one
  adapter per database family. Each adapter owns its **own** read-only enforcement,
  because "read-only" means something different in each: a SQL parse check for
  `SqlBackend`, an operation allowlist for `MongoBackend`.
- **Infrastructure** — long-lived resources: SQLAlchemy engines, Mongo clients, the
  config-file reader.

### Key invariant: safety lives at the chokepoint

Read-only enforcement lives inside `query_service`, which calls the backend's
`validate` before its `execute`. **Every path that runs a query goes through
`query_service`.** It is impossible to execute anything without passing the check.
Combined with a read-only DB role, that's the two-layer safety model.

The backend seam (decision #20) does not weaken this: it *narrows* it. There is
still exactly one chokepoint in the service layer; what varies per backend is only
*how* `validate` decides, never *whether* it runs. A backend that implements
`execute` without a meaningful `validate` is a bug, not a configuration.

### Read-only means different things per backend

- **SQL** — `sqlglot` parses the statement in the alias's dialect; anything that is
  not a single read-only `SELECT` is refused (mutations in CTEs and subqueries,
  stacked statements, unparsed commands included).
- **Mongo** *(planned — decision #22)* — an **operation allowlist**: `find`,
  `aggregate`, `count_documents`, `distinct`. Everything else is refused. Crucially,
  **`aggregate` is not inherently a read**: the `$out` and `$merge` stages *write*
  (`$out` replaces a whole collection), so every pipeline is walked stage by stage
  and refused if it contains one. Server-side JavaScript (`$where`, `mapReduce`,
  `$function`, `$accumulator`) is refused outright — it is arbitrary code, not a
  query.

### Table exclusion (third safety layer)

Each alias may declare a per-database `exclude_tables` denylist (see decision
#16). `is_excluded(alias, table)` on the connection registry is the single source
of truth every backend consults — it stays at the **registry** level, above the
backend seam, so a new backend cannot forget it. An excluded table's
**name/identity is never model-facing**: it is omitted from `list_tables`,
rejected by `get_schema` (as if it does not exist), scrubbed from other tables'
foreign keys, and rejected at execution. The **fact** that tables were withheld
*is* disclosed, though — `list_tables`/`get_schema` return a `hidden_count` — so
the agent can tell a user that relevant data may be out of reach (and that a
human might need to grant access) instead of silently answering from a partial
picture.

For Mongo the unit is a **collection**, and the denylist must be walked across
every pipeline stage that names one — a `$lookup` or `$unionWith` can otherwise
read a hidden collection through a join, exactly as a SQL subquery could.

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
  behind a clean interface for the admin CLI
  (`peek db add/remove/list`), implemented via tasks 001–007. The CLI is a human
  tool (never an MCP tool), writes credentials only to the local config file, and
  requires an MCP-server **restart to take effect** — no live reload in v1. See
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
- **DB access:** SQLAlchemy (dialect-agnostic) for SQL backends, `pymongo` for Mongo
  (planned) — both behind the `Backend` protocol (decision #20), reached via
  connection strings.
- **DB drivers:** drivers are **optional extras** (SQLAlchemy ships dialects,
  not drivers). Supported SQL backends: PostgreSQL (`postgres` → `psycopg[binary]`),
  MySQL/MariaDB (`mysql` → `pymysql`), SQL Server (`mssql` → `pyodbc`), Oracle
  (`oracle` → `oracledb`); SQLite needs no install (stdlib). MongoDB is the same
  pattern: `mongo` → `pymongo` (planned). See `decisions.md` #13.
- **Safety:** read-only DB role (every backend) + a per-backend client-side check —
  `sqlglot` parse check for SQL, operation allowlist for Mongo (`decisions.md` #22).
- **Paths/config:** `pathlib` + `platformdirs`
- **Config/models:** `pydantic` + `pydantic-settings` (connection URLs as `SecretStr`)
- **No** LangChain / LangGraph / embeddings / vector store in v1 (see `backlog.md`)
