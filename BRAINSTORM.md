# BRAINSTORM — scratchpad

Unsettled thinking only. **Settled truth lives in `docs/`** (`architecture.md`,
`structure.md`, `decisions.md`, `backlog.md`) — don't duplicate it here. When an
item below is settled, promote it into the right `docs/` file and delete it here.

## Open questions

- **Config file format** for the connection registry — TOML vs JSON?
- **`run_sql` limits** — row cap, max result size, and the result serialization
  shape returned to the agent.
- **`get_schema` output** — shape (DDL text vs structured columns?) and the
  pagination/filter params for large schemas.
- **Cross-database questions** — can one request ever need to span multiple DBs?
  (Currently scoped to one DB per request; revisit only if a real need appears.)
- **TUI** (deferred) — framework (Textual vs prompt_toolkit), result formatting,
  multi-turn session state. Also revives the suspended NL→SQL brain (`backlog.md`).

## Raw ideas (unfiltered)

_(nothing yet)_
