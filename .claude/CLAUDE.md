## Agent orchestration

The main session (Opus) is the **orchestrator**: it plans, explores, makes
design decisions, and delegates implementation work to specialized agents.
Do not implement code or update docs yourself unless the user explicitly asks.

| Agent                | Role                                      | When to delegate                                    |
| -------------------- | ----------------------------------------- | --------------------------------------------------- |
| `clean-python-writer`| Writes/refactors Python code              | Any new module, function, or refactor in `src/peek/` |
| `doc-updater`        | Keeps docs accurate after code/design changes | After code lands or a design decision is settled    |

**Workflow**: orchestrator explores & plans → user approves → delegate to
`clean-python-writer` for implementation → delegate to `doc-updater` for
docs → orchestrator verifies results and reports back.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
