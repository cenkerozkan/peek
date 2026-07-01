# Repo / Package Structure

`src`-layout package managed with **uv**. The directory layout enforces the layered
architecture in `architecture.md`: MCP tools stay thin, all logic lives in shared
services, and every SQL path funnels through one safety chokepoint. v1 has **no
internal LLM** — no pipeline, no LLM/embedding services.

```
generic-nl-2-sql/
├── pyproject.toml              # deps + build config (uv)
├── uv.lock
├── README.md
├── CLAUDE.md · BRAINSTORM.md · docs/ · llm_friendly_docs/   (existing)
├── src/
│   └── nl2sql/
│       ├── __init__.py
│       ├── server.py           # FastMCP entry: lifespan, wires tools → services
│       ├── config.py           # settings + config-file path resolution (platformdirs)
│       │
│       ├── tools/              # ── MCP TOOL LAYER (thin, agent-facing) ──
│       │   ├── schema.py       #    list_tables, get_schema
│       │   ├── sql.py          #    run_sql, validate_sql
│       │   └── databases.py    #    list_databases  (read-only; NO register/remove)
│       │
│       ├── services/           # ── SERVICE LAYER (all business logic) ──
│       │   ├── connection_registry.py   # load/validate connections at startup;
│       │   │                            #   add/remove logic behind iface for future CLI
│       │   ├── schema_service.py        # introspection: list tables, get schema
│       │   └── sql_service.py  #    validate (read-only check) + execute ← safety chokepoint
│       │
│       ├── safety/
│       │   └── guard.py        #    sqlglot read-only parse check (used by sql_service)
│       │
│       ├── infra/              # ── INFRASTRUCTURE (long-lived resources) ──
│       │   ├── engines.py      #    build/cache SQLAlchemy engines from conn strings
│       │   └── config_file.py  #    read/parse the user's alias → conn-string file
│       │
│       └── models/             #    Pydantic schemas for tool I/O
│           └── ...
└── tests/                      #    mirrors src/nl2sql/ (services/, tools/, safety/, …)
```

Deferred modules (would return with the suspended internal pipeline — see
`backlog.md`): `pipeline/`, `services/llm_service.py`, `services/embedding_service.py`,
`infra/llm.py`, `infra/vectorstore.py`, and the coarse `tools/query.py`
(`ask_database`).

## How the layout enforces the architecture

- **`tools/` is thin.** One function per MCP tool: validate params, call a service,
  shape the return. No business logic. `databases.py` exposes **only**
  `list_databases` — registration is a startup/admin concern, never a model tool.
- **`services/` holds all logic.** `tools/` never reaches into `infra/` or the DB
  directly — always through a service.
- **`sql_service.py` is the single safety chokepoint.** It calls `safety/guard.py`
  before executing, so every SQL path (any tool) passes the read-only check. The
  layout makes bypass structurally hard.
- **`infra/` isolates long-lived resources** (engines, config-file reader) that
  `server.py`'s FastMCP lifespan builds once and injects.
- **`connection_registry` keeps add/remove behind an interface** even though only
  startup loading is wired now — so a future non-model admin CLI can reuse it.

## Import direction (dependencies point downward only)

```
tools/ ─▶ services/ ─▶ infra/
              └─▶ safety/
```

Never the reverse: `services/` must not import `tools/`; `infra/` must not import
`services/`.
