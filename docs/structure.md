# Repo / Package Structure

`src`-layout package, hatchling build (uv is the intended package manager; the
current `.venv` was bootstrapped with `python3.13 -m venv` + pip). The directory
layout enforces the layered architecture in `architecture.md`: MCP tools stay thin,
all logic lives in shared services, and every SQL path funnels through one safety
chokepoint. v1 has **no internal LLM** — no pipeline, no LLM/embedding services.

Status markers: **✓** exists · **(planned)** not written yet.

```
peek/
├── pyproject.toml              ✓ deps + build config (hatchling)
├── README.md                   ✓
├── CLAUDE.md · BRAINSTORM.md · docs/ · llm_friendly_docs/   ✓
├── src/
│   └── peek/
│       ├── __init__.py         ✓
│       ├── config.py           ✓ AppConfig (pydantic-settings, PEEK_* env);
│       │                       #   resolves config-file path via platformdirs; max_rows cap
│       ├── errors.py           ✓ exception hierarchy (PeekError base: ConfigError,
│       │                       #   RegistryError, …); messages never carry credentials
│       ├── server.py           (planned) FastMCP entry: lifespan, wires tools → services
│       │
│       ├── tools/              # ── MCP TOOL LAYER (thin, agent-facing) ──
│       │   ├── schema.py       (planned) list_tables, get_schema
│       │   ├── sql.py          (planned) run_sql, validate_sql
│       │   └── databases.py    (planned) list_databases (read-only; NO register/remove)
│       │
│       ├── services/           # ── SERVICE LAYER (all business logic) ──
│       │   ├── connection_registry.py   (planned) load/validate connections at startup;
│       │   │                            #   add/remove logic behind iface for future CLI
│       │   ├── schema_service.py        (planned) introspection: list tables, get schema
│       │   └── sql_service.py  (planned) validate (read-only check) + execute ← chokepoint
│       │
│       ├── safety/
│       │   └── guard.py        ✓ sqlglot read-only parse check: ensure_read_only()
│       │                       #   raises UnsafeSQLError; used by sql_service
│       │
│       ├── infra/              # ── INFRASTRUCTURE (long-lived resources) ──
│       │   ├── config_file.py  ✓ read/parse the user's alias → conn-string TOML file
│       │   └── engines.py      (planned) build/cache SQLAlchemy engines from conn strings
│       │
│       └── models/             #    Pydantic schemas
│           └── config.py       ✓ DatabaseEntry (url as SecretStr — never leaks in repr/logs)
└── tests/                      #    mirrors src/peek/
    └── safety/
        └── test_guard.py       ✓ proves non-SELECT / mutating statements are rejected
```

Deferred modules (would return with the suspended internal pipeline — see
`backlog.md`): `pipeline/`, `services/llm_service.py`, `services/embedding_service.py`,
`infra/llm.py`, `infra/vectorstore.py`, and the coarse `tools/query.py`
(`ask_database`).

**Concrete choices locked in by the first modules:**
- Connection-registry file is **TOML** (`databases.toml`), shaped as
  `[databases.<alias>]` with `url` (+ optional `dialect`). Resolves the earlier
  TOML-vs-JSON open question.
- **Pydantic / pydantic-settings** for config + models; connection URLs are held as
  **`SecretStr`** so they never appear in a `repr()`, log, or dump — a concrete
  enforcement of credential isolation.
- `run_sql` row cap lives in `AppConfig.max_rows`.

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
