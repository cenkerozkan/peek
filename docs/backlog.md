# Backlog — Killed & Suspended Ideas

Parking lot for ideas we removed or deferred. Keeping the *why* and a *revival
condition* here stops us re-debating settled cuts and preserves the reasoning where
it's findable (unlike a deleted git diff).

Status legend: **Suspended** (deferred, has a revival condition) · **Killed**
(rejected, unlikely to return).

---

## Internal LangGraph NL→SQL pipeline — Suspended (2026-07-01)

An in-server LangGraph agent that turned a natural-language question into SQL:
`parse intent → build schema context → generate SQL → validate → execute →
retry-on-error → summarize`, exposed via a coarse `ask_database(question, db)` tool.

- **Why removed:** the MCP server is driven *by another agent* (Claude Code,
  Copilot). Running our own LLM agent inside a tool the outer agent already
  reasons with means two stacked LLM loops — extra latency, ~doubled token cost,
  less predictable. The outer agent can do NL→SQL itself using the fine-grained
  tools (`get_schema`, `validate_sql`, `run_sql`). Don't nest an agent inside an
  agent.
- **Revival condition:** when we build the **human-facing TUI**. There is no outer
  agent there, so the server itself needs a brain to turn NL into SQL. Reassess
  LangGraph vs. a simpler chain at that point.
- **Depends on / drags along:** see the entries below — removing the internal LLM
  also suspends `llm_service`, `embedding_service`, and the schema-retrieval
  threshold.

## Internal LLM service (SQL generation + summarization) — Suspended (2026-07-01)

`llm_service` for generating SQL and summarizing results inside the server.

- **Why removed:** only existed to feed the internal pipeline. With no in-server
  NL→SQL, there's nothing for it to do — the outer agent generates SQL and
  interprets results.
- **Revival condition:** same as the LangGraph pipeline (TUI).

## Embedding-based schema retrieval + 100-table threshold — Suspended (2026-07-01)

`embedding_service` + vector store to retrieve the top-k relevant tables once a DB
exceeds ~100 tables, to keep the *internal* prompt small.

- **Why removed:** it existed to bound the internal LLM's prompt size. Without an
  internal LLM, the outer agent manages its own context; `get_schema` just returns
  schema (with plain pagination/filter params if it gets large), no embeddings.
- **Revival condition:** if the TUI's internal brain returns, or if `get_schema`
  output proves too large to hand to outer agents in practice.

## No CLI argument handling (`peek --help` does nothing useful) — Suspended (2026-07-13)

`peek` currently ignores argv entirely: it boots straight into the MCP stdio
server regardless of what's passed on the command line. `peek --help` does not
print help — it just tries to start the server and fails with a `ConfigError`
if no registry file exists yet.

- **Why deferred rather than fixed now:** discovered during Phase 8 packaging
  verification; it's a UX rough edge, not a safety or correctness gap, and
  wasn't blocking local install verification.
- **Revival condition:** pick up as a follow-up once the packaging/publishing
  work (`roadmap.md` Phase 9) lands — worth a minimal `--help`/`--version` at
  least, since a confusing `ConfigError` on first run is a bad first impression
  for a freshly-installed tool.

---

## Earlier superseded decisions (for reference)

- **CLI-first build order** → flipped to MCP-first. (See `decisions.md` #4.)
- **TinyDB dynamic registry + `register`/`remove` MCP tools** → replaced by a
  user-maintained config file read at startup; registration is not a model tool.
  (See `decisions.md` #7.)
