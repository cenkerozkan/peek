# BRAINSTORM — scratchpad

Unsettled thinking only. **Settled truth lives in `docs/`** (`architecture.md`,
`structure.md`, `decisions.md`, `backlog.md`) — don't duplicate it here. When an
item below is settled, promote it into the right `docs/` file and delete it here.

## Open questions

- **Mongo query wire format** *(blocks roadmap Phase 11 — decide before writing
  code)*. `run_query(db, query)` takes a string for SQL. What does an agent send to
  a Mongo alias?
  - A **JSON string** the server parses (`{"find": "orders", "filter": {...}}`)?
    Keeps the tool signature identical across backends — one `query: str` — but the
    agent is writing JSON inside a string, and we own the parse errors.
  - A **structured argument object** (`collection`, `operation`, `pipeline`)?
    Self-documenting and validated by Pydantic for free, but it splits the tool
    signature per backend, which is exactly what decision #21 chose *against*.
  - Something MongoDB-shell-shaped (`db.orders.find({...})`)? Familiar to humans,
    but now we're writing a parser for a JS-ish dialect — and the shell's syntax
    admits arbitrary JS, which is the thing #22 refuses on purpose.
  - Leaning: JSON string. It preserves the single tool surface, and "the alias tells
    you what language to write" stays a one-sentence rule. But the ergonomics of BSON
    types (`ObjectId`, dates) inside plain JSON need a real answer first.
- **Inferred-schema fidelity for Mongo** — sampling 100 docs (decision #22) will miss
  rare fields in a heterogeneous collection. Is a count of sampled-vs-total docs
  enough for the agent to reason about the gap, or does it need per-field frequency
  ("`email` present in 12% of sampled docs")? Frequency is more honest and more
  tokens.
- **Cross-database questions** — can one request ever need to span multiple DBs?
  (Currently scoped to one DB per request; revisit only if a real need appears.)
  A Mongo alias makes this strictly harder, not easier — there is no federation
  story across a SQLAlchemy engine and a pymongo client.
- **TUI** (deferred) — framework (Textual vs prompt_toolkit), result formatting,
  multi-turn session state. Also revives the suspended NL→SQL brain (`backlog.md`).

## Raw ideas (unfiltered)

_(nothing yet)_
