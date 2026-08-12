# Repo / Package Structure

`src`-layout package, hatchling build (uv is the intended package manager; the
current `.venv` was bootstrapped with `python3.13 -m venv` + pip). The directory
layout enforces the layered architecture in `architecture.md`: MCP tools stay thin,
all logic lives in shared services, and every SQL path funnels through one safety
chokepoint. v1 has **no internal LLM** — no pipeline, no LLM/embedding services.

Status markers: **✓** exists · **(planned)** not written yet.

```
peek/
├── pyproject.toml              ✓ deps + build config (hatchling); console entry point
├── README.md                   ✓
├── CLAUDE.md · BRAINSTORM.md · docs/ · llm_friendly_docs/   ✓
├── .github/workflows/ci.yml    ✓ lint/type/test + wheel build + entry-point smoke test
│                                  #   on ubuntu/windows/macos (decisions.md #18)
├── .github/workflows/publish-testpypi.yml  ✓ push to `testing` -> build/test -> TestPyPI
│                                  #   (trusted publishing/OIDC; decisions.md #23)
├── .github/workflows/publish-pypi.yml      ✓ push to `main` -> build/test -> PyPI
│                                  #   (trusted publishing/OIDC; decisions.md #23)
├── src/
│   └── peek/
│       ├── __init__.py         ✓
│       ├── __main__.py         ✓ `python -m peek` entry
│       ├── config.py           ✓ AppConfig (pydantic-settings, PEEK_* env);
│       │                       #   resolves config-file path via platformdirs; max_rows cap
│       ├── errors.py           ✓ exception hierarchy (PeekError base: ConfigError,
│       │                       #   RegistryError, …); messages never carry credentials
│       ├── server.py           ✓ FastMCP entry: lifespan builds registry + services once,
│       │                       #   yields AppContext, disposes engines on shutdown;
│       │                       #   `main()` runs stdio, `show_banner=False`
│       │
│       ├── cli/                # ── ADMIN CLI (Click) ──
│       │   ├── __init__.py     ✓ Click group, entry-point routing, config path resolver
│       │   ├── init_cmd.py     ✓ `peek init` — scaffold `.peek/` project directory
│       │   └── db.py           ✓ `peek db add/remove/list` — manage DB aliases in registry
│       │
│       ├── tools/              # ── MCP TOOL LAYER (thin, agent-facing) ──
│       │   ├── context.py      ✓ AppContext + app_context() dependency seam
│       │   ├── schema.py       ✓ list_tables, get_schema
│       │   ├── query.py        ✓ run_query, validate_query  (renamed from sql.py
│       │   │                   #   in Phase 10 — decisions.md #21)
│       │   └── databases.py    ✓ list_databases (read-only; NO register/remove)
│       │
│       ├── services/           # ── SERVICE LAYER (backend-agnostic business logic) ──
│       │   ├── connection_registry.py   ✓ load/validate connections at startup;
│       │   │                            #   maps alias → Backend; owns is_excluded();
│       │   │                            #   add/remove logic behind iface for future CLI
│       │   ├── schema_service.py        ✓ introspection: list tables, get schema
│       │   └── query_service.py ✓ validate (read-only check) + execute ← chokepoint
│       │                        #   (renamed from sql_service.py in Phase 10)
│       │
│       ├── backends/           # ── BACKEND LAYER (port/adapter — decisions.md #20) ──
│       │   ├── base.py         (planned) the Backend protocol: list_tables,
│       │   │                   #   get_schema, validate, execute, dispose
│       │   ├── sql.py          (planned) SqlBackend — SQLAlchemy + the sqlglot guard.
│       │   │                   #   Phase 10 MOVES the shipped SQL code here; it is
│       │   │                   #   not a rewrite, and the SQL tests must pass unchanged
│       │   └── mongo.py        (planned) MongoBackend — pymongo + operation-allowlist
│       │                       #   guard; sampled/inferred schema (decisions.md #22)
│       │
│       ├── safety/
│       │   ├── guard.py        ✓ sqlglot read-only parse check: ensure_read_only()
│       │   │                   #   raises UnsafeSQLError; used by SqlBackend
│       │   └── mongo_guard.py  (planned) operation allowlist; rejects $out/$merge
│       │                       #   (aggregation CAN write!), $where/mapReduce/$function
│       │
│       ├── infra/              # ── INFRASTRUCTURE (long-lived resources) ──
│       │   ├── config_file.py  ✓ read/parse the user's alias → conn-string TOML file
│       │   ├── engines.py      ✓ build SQLAlchemy engines from conn strings
│       │   ├── mongo_client.py (planned) build pymongo clients from conn strings
│       │   └── dialects.py     ✓ SQLAlchemy dialect name → sqlglot dialect name
│       │
│       └── models/             #    Pydantic schemas
│           ├── config.py       ✓ DatabaseEntry (url as SecretStr — never leaks in repr/logs)
│           ├── schema.py       ✓ table-list / get_schema I/O types
│           └── query.py        ✓ QueryResult, ValidationResult
└── tests/                      #    mirrors src/peek/; imports `peek` via
                                 #    pytest's `pythonpath = ["src"]`, no `src.` prefix
```

Deferred modules (would return with the suspended internal pipeline — see
`backlog.md`): `pipeline/`, `services/llm_service.py`, `services/embedding_service.py`,
`infra/llm.py`, `infra/vectorstore.py`, and the coarse `tools/ask.py`
(`ask_database`). *(That coarse tool was previously penciled in as `tools/query.py`;
that name now belongs to the real `run_query`/`validate_query` tools.)*

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
- **`services/` holds all logic, and names no backend.** `tools/` never reaches into
  `backends/` or `infra/` directly — always through a service. If a service ever
  needs an `if backend == "mongo"` branch, the `Backend` protocol is missing a
  method; add it there instead.
- **`query_service.py` is the single safety chokepoint.** It calls the backend's
  `validate` before its `execute`, so every query path (any tool, any backend)
  passes a read-only check. The layout makes bypass structurally hard.
- **`backends/` is where backend-specific knowledge is allowed to live** — and the
  only place. Each adapter owns its own guard, because read-only means a parse check
  in SQL and an operation allowlist in Mongo (`decisions.md` #22).
- **`infra/` isolates long-lived resources** (engines, Mongo clients, config-file
  reader) that `server.py`'s FastMCP lifespan builds once and injects.
- **`connection_registry` keeps add/remove behind an interface** even though only
  startup loading is wired now — so a future non-model admin CLI can reuse it. It
  also owns `is_excluded()` (the denylist), deliberately **above** the backend seam,
  so a new backend cannot forget to apply it.

## Import direction (dependencies point downward only)

```
tools/ ─▶ services/ ─▶ backends/ ─▶ infra/
                           └─▶ safety/
```

Never the reverse: `services/` must not import `tools/`; `backends/` must not import
`services/`; `infra/` must not import anything above it.
