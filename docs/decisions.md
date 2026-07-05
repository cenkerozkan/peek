# Decision Log

Lightweight ADR-style log: **what** we chose, **why**, and the alternatives we
rejected. `architecture.md` describes the current design; this file records the
reasoning so we (and future agents) don't re-litigate settled tradeoffs. Newest
context at the bottom of each entry.

Every decision header carries its **current status and the date** that status was
set — e.g. `— Superseded (2026-07-01)`. When a decision's status changes, update
the header (status + new date), don't just append a note in the body.

Status legend: **Accepted** · **Provisional** (may change) · **Superseded**

---

## 1. LangGraph for the query pipeline — Superseded (2026-07-01)

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

## 2. Safety: read-only DB role + client-side parse check — Accepted (2026-07-01)

Two independent layers; both required.

- **Layer 1:** connect with a read-only DB role/grants (SELECT-only).
- **Layer 2:** client-side SQL parse check (e.g. `sqlglot`) rejecting any
  non-SELECT statement before execution.
- **Why:** it's a company tool; a single control is not enough. Defense-in-depth so
  a bypass of one layer is still caught by the other. The parse check lives in
  `sql_service` so every execution path passes it (see decision 8).

## 3. Schema context: full dump, retrieval past a threshold — Superseded (2026-07-01)

Originally: dump the full schema into the internal prompt; switch to
embedding-based retrieval of top-k relevant tables past ~100 tables.

- **⚠️ SUPERSEDED (2026-07-01):** this existed to bound an *internal* LLM's prompt,
  which no longer exists (see #1). In v1, `get_schema` just returns schema with plain
  pagination/filter params; the outer agent manages its own context. No embeddings,
  no vector store, no threshold. Suspended; see `backlog.md`.

## 4. MCP server first; interactive TUI later — Accepted (2026-07-01)

Ship the MCP server first. Add a human-facing interface later.

- **Later interface:** an interactive, Claude-Code-style conversational TUI — *not*
  a one-shot CLI. Framework TBD (Textual / prompt_toolkit).
- **Why:** the MCP-as-a-tool-for-other-agents use case is the central/novel one for
  this project. Originally planned CLI-first; user flipped it to MCP-first.

## 5. Fine-grained MCP tools only (no coarse `ask_database`) — Accepted (2026-07-01)

- **Tools:** `list_databases`, `list_tables`, `get_schema`, `validate_sql`,
  `run_sql`. All read-only; each takes a DB alias.
- **Why:** originally we planned a coarse `ask_database` alongside these, but that
  required an internal LLM pipeline (removed in #1). With no internal LLM, the outer
  agent composes the fine-grained tools itself. Revised 2026-07-01 (dropped the
  coarse tool).

## 6. Multi-database, one DB per request — Accepted (2026-07-01)

The server connects to multiple databases at once, each addressed by alias. Every
tool takes a DB target param.

- **Scope:** one database per request. Cross-database joins are **out of scope** —
  SQLAlchemy can't join across separate engines without a federation layer.
- **Why:** a single project commonly spans multiple DBs. Aliases keep callers away
  from raw connection strings. Cross-DB joins are genuinely hard and unproven-needed;
  revisit only if a real requirement appears.

## 7. Connection registry: config-driven at startup, not a runtime tool — Accepted (2026-07-01)

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
- **Management:** hand-edit the config file, or use a planned **admin CLI**
  (`peek db add/remove/list`) — see the sub-decision below. Registration/removal
  logic lives behind the `connection_registry` interface so the CLI is a thin
  consumer of it. Structure kept changeable.
- **Alternatives rejected:** (a) TinyDB store + `register`/`remove` MCP tools —
  redundant once the user maintains a config file, and giving the model registration
  power is a privilege it shouldn't have; (b) full connection strings in the MCP
  launch `env` — risks credential commit.
- **Why:** registration is a human/admin action, not something the model should do.
  A user-maintained config file is the persistence; a path handed in at launch keeps
  credentials out of both version control and the model's reach.

  Supersedes the earlier plan (dynamic TinyDB registry managed via MCP tools).

### 7a. Admin CLI for database management (`peek db …`) — Accepted (2026-07-05)

A human-facing CLI to add/remove/list database aliases, so users don't have to
hand-edit the config file. Confirmed as the intended management path; scoped tightly
for v1.

- **Human tool, never a model tool.** `peek db add/remove/list` is invoked by a
  person in their terminal. It is **not** registered on the FastMCP server and shares
  no surface with the MCP tools — the hard rule that the model cannot add/remove
  connections (only `list_databases`, read-only) is untouched. Nobody may later wire
  these up as MCP tools.
- **Credential isolation still applies.** The CLI writes connection strings **only**
  to the local registry config file (the existing source of truth) — never to the
  repo or the `.mcp.json` launch config. It should take the password interactively /
  via env rather than a shell arg (keeps it out of shell history).
- **Value over hand-editing:** validate the connection (attempt to connect) before
  persisting the entry.
- **Not live — restart required.** The registry is built once at startup (see
  `architecture.md` → Server lifecycle); there is **no dynamic runtime
  registration**. `peek db add/remove` edits the config file, and the user must
  **restart the MCP server** for changes to take effect. Live/hot-reload is
  explicitly deferred — a running stdio subprocess is owned by the IDE and restarts
  are cheap, so an IPC/reload path isn't worth its complexity in v1.
- **Scope / timing:** its own later phase (see `roadmap.md` → Later/deferred), after
  the `connection_registry` interface has solidified — the CLI is a consumer of it.
- **Revisit condition for live support:** reconsider hot-reload after the core
  project is complete, if restart-to-apply proves too coarse in practice.

## 8. Layered architecture — Accepted (2026-07-01)

`MCP tools (thin) -> service layer -> infrastructure`.

- **Why:** keeps SQL execution/validation/safety written and secured in **one**
  place. Key invariant: the read-only check lives in `sql_service` (calling
  `safety/guard.py`), so no path can execute SQL without passing it.
- **Analogy:** mirrors FastAPI `router -> service -> repository`; MCP tools are the
  router layer and stay thin.
- **Note:** originally this layering also justified sharing services between the
  tools and the LangGraph pipeline's nodes. The pipeline is gone (#1), but the
  layering stands on its own for keeping the safety chokepoint single.

## 9. Transport: local stdio — Accepted (2026-07-01; Provisional for remote)

Start with local stdio: the consuming agent launches the server as a subprocess.

- **Why:** simplest, no network/auth, standard for a dev-facing MCP tool. Nothing in
  the core is coupled to stdio, so an HTTP transport (with auth) can be added later
  if a shared/remote deployment is needed.

## 10. Credential isolation — Accepted (2026-07-01; hard rule)

No tool return value or error message may ever contain a connection string; the LLM
sees only aliases.

- **Why:** the real leak vector is **tool output**, not storage. An MCP client
  forwards tool returns/errors to the remote model API as context. The local
  registry file never leaves the machine; a connection string echoed in a result
  does. So: `list_databases` returns aliases only, SQLAlchemy errors are scrubbed of
  URLs, and credentials never go in a (committable) MCP launch config.

## 11. FastMCP as the MCP framework — Accepted (2026-07-01)

- **Why:** batteries-included MCP server framework; reference docs vendored at
  `../llm_friendly_docs/fastmcp.txt`. Long-lived resources (the SQLAlchemy engines)
  are built once via its lifespan/context and injected, never per-call.

## 12. Cross-platform: pathlib + platformdirs — Accepted (2026-07-01)

All code must run on Windows and macOS (the company's actual platforms; Linux is
rare).

- **Why / how:** use `pathlib.Path` for all path work (no string concatenation or
  hardcoded separators); resolve user directories via `platformdirs`
  (`user_config_dir("peek")`) rather than a hardcoded `~/.config`, which is
  Linux-only.

## 13. Database drivers as optional extras — Accepted (2026-07-01)

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

## 14. Distribution: console entry point, `uvx`-first, pipx supported — Accepted (2026-07-05)

peek is an **application, not a library** — nobody `import`s it; an outer agent
launches it as a subprocess. That's the exact shape isolated-app installers
(`uvx`, `pipx`) exist for: the app and its deps (fastmcp, sqlalchemy, drivers)
live in their own environment and never collide with anything else on the machine.

- **Prerequisite:** a console entry point — `[project.scripts] peek =
  "peek.server:main"` — plus `python -m peek`. This one addition unblocks `uvx`,
  `pipx`, and `python -m` simultaneously. (Tracked in the roadmap; ties to the
  Phase 7 entry-point work.)
- **Primary path — `uvx`:** we already use uv (`uv.lock` in the tree) and the MCP
  ecosystem has standardized on `uvx` for launch configs. The MCP client config
  becomes `{"command": "uvx", "args": ["peek"]}`. `uvx` runs the published version
  in an ephemeral env — no explicit install/upgrade step, always current — which
  fits the "outer agent spawns the server" model better than a persistent install.
- **Supported alternative — pipx:** for users who want a persistent install
  (`pipx install peek`). Costs nothing extra once the entry point exists, so we
  document it as the secondary option rather than the lead.
- **Driver extras are chosen at install/launch time** (see #13), same syntax for
  both: `uvx --from 'peek[postgres]' peek` / `pipx install 'peek[postgres,mysql]'`.
  Because drivers are opt-in, this must be documented prominently either way.
- **Alternatives rejected:** (a) library-style `pip install peek` into a shared
  environment — dependency collisions for what is an application, not a library;
  (b) leading with pipx — an extra install/upgrade step versus `uvx`'s ephemeral,
  always-latest run that matches our uv tooling and the ecosystem norm.

## 15. `get_schema` output: structured columns, selector + pagination — Accepted (2026-07-05)

`get_schema` returns **structured columns** (Pydantic), not DDL text: per column
a name, dialect-native type string, nullability, default, and a primary-key flag,
plus each table's primary key and foreign keys. Callers scope large databases
with an explicit `tables=[...]` selector or, failing that, `limit`/`offset`
pagination; `list_tables` is the cheap names-only call an agent makes first.
Introspection covers **views** (each tagged by `kind`) and takes an optional
`schema=` namespace, defaulting to the database's default schema.

- **Alternatives rejected:** (a) raw DDL text — harder for the agent to parse and
  not uniformly reconstructable across dialects via SQLAlchemy's inspector;
  (b) columns-only with no keys — leaves the agent guessing at JOINs;
  (c) indexes in the payload — deferred as noise the outer agent rarely needs;
  (d) embedding-based schema retrieval — killed with the internal LLM (see #3).
- **Why:** structured columns give the outer agent a uniform, machine-readable
  shape across every backend; PK/FK are the minimum needed to write correct
  JOINs; a selector plus pagination lets the agent manage its own context without
  the server guessing relevance. Built on SQLAlchemy's `inspect()`; no SQL is
  executed, so it does not route through the safety guard, but returns and errors
  stay credential-free.

## 16. Table exclusion: per-alias denylist, exact case-insensitive match — Accepted (2026-07-05)

Each database alias may declare `exclude_tables` in the registry TOML — a
denylist of tables that must never reach any LLM's context, orthogonal to the
read-only guard. Matching is **exact and case-insensitive**: a bare name
(`secrets`) excludes that table in any schema; a qualified name
(`billing.invoices`) excludes only that schema's table. No glob/wildcard
patterns in v1. A single `is_excluded(alias, table)` accessor on the connection
registry is the one source of truth. An excluded table's **name is never
model-facing**: it is omitted from `list_tables`, rejected by `get_schema` as if
nonexistent, scrubbed from other tables' foreign keys, and (from Phase 5)
rejected at execution; excluded names never appear in `describe`/`list_metadata`
either. The **fact** that tables were withheld is disclosed, though —
`list_tables`/`get_schema` carry a `hidden_count` (a count, never names) — so the
agent can tell a user that relevant data is out of reach and a human may need to
grant access, rather than answering confidently from a partial schema.

- **Alternatives rejected:** (a) glob/wildcard patterns — deferred; a broad
  pattern can hide more than intended, and exact names are predictable and
  simpler to test (revive if real denylists prove verbose); (b) case-sensitive
  matching — SQL identifiers are usually case-insensitive, so a case-sensitive
  denylist would silently miss `Secrets` vs `secrets` and leak (matching is
  comparison-only; real names are always returned in their true casing);
  (c) disclosing excluded *names* to the agent — would defeat hiding a table
  whose very existence is confidential; (d) hiding the count too (total silence)
  — leaves the agent unable to tell it is working from a partial picture, so it
  may answer wrongly instead of flagging the gap; (e) hiding only from
  `list_tables` — an excluded name would still leak via another table's foreign
  key or an explicit `get_schema`/query, so exclusion is enforced at every read
  surface.
- **Why:** environments (prod/uat/dev) contain tables that must stay invisible
  regardless of read-only access; a config-driven denylist with one accessor
  keeps every service consistent and makes "the name is invisible" a structural
  property. Disclosing only a count threads the needle: the identity stays secret
  while the agent still knows to ask a human when a question may need withheld
  data.

---

## Still open

Open/unsettled questions live in `../BRAINSTORM.md` (the scratchpad). When one is
settled it graduates into a numbered decision here.
