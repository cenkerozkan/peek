# Decision Log

Lightweight ADR-style log: **what** we chose, **why**, and the alternatives we
rejected. `architecture.md` describes the current design; this file records the
reasoning so we (and future agents) don't re-litigate settled tradeoffs. Newest
context at the bottom of each entry. All dates below: 2026-07-01.

Status legend: **Accepted** · **Provisional** (may change) · **Superseded**

---

## 1. LangGraph for the query pipeline — Accepted

Generate SQL through an explicit LangGraph graph.

- **Alternatives rejected:** (a) LangChain's prebuilt ReAct SQL agent — too
  autonomous, unpredictable, hard to constrain and secure; (b) a rigid linear chain
  — not self-correcting when SQL fails.
- **Why:** LangGraph gives explicit, inspectable state transitions *and* a
  controlled retry loop (execute error → regenerate with error context), i.e. the
  self-correction benefit without the black-box agent behavior.
- **⚠️ SUPERSEDED (2026-07-01):** the entire internal NL→SQL pipeline was removed
  from v1. When the server is driven by an outer agent (Claude Code/Copilot), an
  in-server LLM agent is a second stacked LLM — wasteful. v1 has no internal LLM; the
  outer agent does NL→SQL via the fine-grained tools. **Suspended, not killed** —
  revives with the human-facing TUI. See `backlog.md`.

## 2. Safety: read-only DB role + client-side parse check — Accepted

Two independent layers; both required.

- **Layer 1:** connect with a read-only DB role/grants (SELECT-only).
- **Layer 2:** client-side SQL parse check (e.g. `sqlglot`) rejecting any
  non-SELECT statement before execution.
- **Why:** it's a company tool; a single control is not enough. Defense-in-depth so
  a bypass of one layer is still caught by the other. The parse check lives in
  `sql_service` so every execution path passes it (see decision 8).

## 3. Schema context: full dump, retrieval past a threshold — Superseded

Originally: dump the full schema into the internal prompt; switch to
embedding-based retrieval of top-k relevant tables past ~100 tables.

- **⚠️ SUPERSEDED (2026-07-01):** this existed to bound an *internal* LLM's prompt,
  which no longer exists (see #1). In v1, `get_schema` just returns schema with plain
  pagination/filter params; the outer agent manages its own context. No embeddings,
  no vector store, no threshold. Suspended; see `backlog.md`.

## 4. MCP server first; interactive TUI later — Accepted

Ship the MCP server first. Add a human-facing interface later.

- **Later interface:** an interactive, Claude-Code-style conversational TUI — *not*
  a one-shot CLI. Framework TBD (Textual / prompt_toolkit).
- **Why:** the MCP-as-a-tool-for-other-agents use case is the central/novel one for
  this project. Originally planned CLI-first; user flipped it to MCP-first.

## 5. Fine-grained MCP tools only (no coarse `ask_database`) — Accepted

- **Tools:** `list_databases`, `list_tables`, `get_schema`, `validate_sql`,
  `run_sql`. All read-only; each takes a DB alias.
- **Why:** originally we planned a coarse `ask_database` alongside these, but that
  required an internal LLM pipeline (removed in #1). With no internal LLM, the outer
  agent composes the fine-grained tools itself. Revised 2026-07-01 (dropped the
  coarse tool).

## 6. Multi-database, one DB per request — Accepted

The server connects to multiple databases at once, each addressed by alias. Every
tool takes a DB target param.

- **Scope:** one database per request. Cross-database joins are **out of scope** —
  SQLAlchemy can't join across separate engines without a federation layer.
- **Why:** a single project commonly spans multiple DBs. Aliases keep callers away
  from raw connection strings. Cross-DB joins are genuinely hard and unproven-needed;
  revisit only if a real requirement appears.

## 7. Connection registry: config-driven at startup, not a runtime tool — Accepted

Databases addressed by alias (like `psql` `.pg_service.conf` / DBeaver saved
connections). The user maintains a **config file** mapping `alias -> connection
string`; the server reads and validates it at startup and builds the in-memory
`connection_registry` (`alias -> engine`).

- **Config file path** is supplied via the **MCP launch config** in the IDE (arg or
  env, e.g. `.mcp.json`). Only the path is in the launch config — never the
  connection strings (would risk being committed).
- **Registration is NOT a model-facing tool.** The LLM must not add/remove
  connections, so `register_database` / `remove_database` are not MCP tools. Only
  `list_databases` (read-only) is exposed to the model.
- **Management for now:** hand-edit the config file. Registration/removal logic
  still lives behind the `connection_registry` interface so a later non-model
  **admin CLI** (`peek db add/remove`) can reuse it. Structure kept changeable.
- **Alternatives rejected:** (a) TinyDB store + `register`/`remove` MCP tools —
  redundant once the user maintains a config file, and giving the model registration
  power is a privilege it shouldn't have; (b) full connection strings in the MCP
  launch `env` — risks credential commit.
- **Why:** registration is a human/admin action, not something the model should do.
  A user-maintained config file is the persistence; a path handed in at launch keeps
  credentials out of both version control and the model's reach.

  Supersedes the earlier plan (dynamic TinyDB registry managed via MCP tools).

## 8. Layered architecture — Accepted

`MCP tools (thin) -> service layer -> infrastructure`.

- **Why:** keeps SQL execution/validation/safety written and secured in **one**
  place. Key invariant: the read-only check lives in `sql_service` (calling
  `safety/guard.py`), so no path can execute SQL without passing it.
- **Analogy:** mirrors FastAPI `router -> service -> repository`; MCP tools are the
  router layer and stay thin.
- **Note:** originally this layering also justified sharing services between the
  tools and the LangGraph pipeline's nodes. The pipeline is gone (#1), but the
  layering stands on its own for keeping the safety chokepoint single.

## 9. Transport: local stdio — Accepted (Provisional for remote)

Start with local stdio: the consuming agent launches the server as a subprocess.

- **Why:** simplest, no network/auth, standard for a dev-facing MCP tool. Nothing in
  the core is coupled to stdio, so an HTTP transport (with auth) can be added later
  if a shared/remote deployment is needed.

## 10. Credential isolation — Accepted (hard rule)

No tool return value or error message may ever contain a connection string; the LLM
sees only aliases.

- **Why:** the real leak vector is **tool output**, not storage. An MCP client
  forwards tool returns/errors to the remote model API as context. The local
  registry file never leaves the machine; a connection string echoed in a result
  does. So: `list_databases` returns aliases only, SQLAlchemy errors are scrubbed of
  URLs, and credentials never go in a (committable) MCP launch config.

## 11. FastMCP as the MCP framework — Accepted

- **Why:** batteries-included MCP server framework; reference docs vendored at
  `../llm_friendly_docs/fastmcp.txt`. Long-lived resources (the SQLAlchemy engines)
  are built once via its lifespan/context and injected, never per-call.

## 12. Cross-platform: pathlib + platformdirs — Accepted

All code must run on Windows and macOS (the company's actual platforms; Linux is
rare).

- **Why / how:** use `pathlib.Path` for all path work (no string concatenation or
  hardcoded separators); resolve user directories via `platformdirs`
  (`user_config_dir("peek")`) rather than a hardcoded `~/.config`, which is
  Linux-only.

## 13. Database drivers as optional extras — Accepted

SQLAlchemy ships dialects (SQL generation) but not DBAPI drivers (the connectors).
Each supported backend needs its driver installed; drivers are exposed as
**optional-dependency extras**, not core deps.

- **Supported backends (v1):** PostgreSQL, MySQL/MariaDB, Microsoft SQL Server,
  Oracle — plus **SQLite**, which needs no install (stdlib `sqlite3`).
- **Extras → drivers:** `postgres` → `psycopg[binary]` (psycopg 3);
  `mysql` → `pymysql` (pure-Python, easiest cross-platform); `mssql` → `pyodbc`;
  `oracle` → `oracledb` (thin mode, no Oracle client needed). `all-drivers`
  installs every one. Install per need, e.g. `pip install peek[postgres,mysql]`.
- **Alternatives rejected:** bundling all drivers into core deps — pulls heavy /
  system-level dependencies (notably `pyodbc` needs a system ODBC driver) onto every
  install, including users who only touch one DB.
- **Why:** keeps the core lean and cross-platform (Windows/macOS). The server can
  *dialect* any SQLAlchemy-supported DB, but only *connects* to backends whose driver
  is present — extras make that explicit. A missing driver surfaces as a clear
  install hint, never a credential leak.
- **Note:** `pyodbc` (mssql) additionally requires the OS-level ODBC driver
  (e.g. Microsoft ODBC Driver for SQL Server); document per-OS setup when needed.

---

## Still open

Open/unsettled questions live in `../BRAINSTORM.md` (the scratchpad). When one is
settled it graduates into a numbered decision here.
