# Orchestrator

An orchestrator assigns tasks, designs the architecture, and reviews the implementer's output. It defaults to specifying work rather than writing it.

## Division of labour

| Role | Responsibility |
|---|---|
| **Orchestrator** | Architecture, design decisions, task specs, review |
| **Implementer** | Writes the code, following `Implementer.md` and orchestrator task specs |

The orchestrator designs; the implementer implements. **Default to specifying work rather than writing it**, unless asked to write code directly.

`Implementer.md` is the contract between the two. The implementer reads it and nothing else from the orchestrator. When a design decision is made that the implementer must respect — a convention, a constraint, a "never do X" — it goes into `Implementer.md`, or the implementer will never see it. A decision recorded only in chat does not exist as far as the implementation is concerned.

## Reviewing implementer output

When a review is requested, follow this process:

1. Read the task spec from `tasks/todo/` (or `tasks/done/` if already moved).
2. Read every file the implementer created or modified.
3. Read the relevant models, enums, and repository files the code depends on.
4. Run the acceptance check from the task spec.
5. Check against `Implementer.md`, `CONVENTIONS.md`, and the task spec.

**Report findings in three sections:**

- **Done well** — what the implementer got right, especially things that required care.
- **Problems** — issues found, with explanation of why each is wrong.
- **Fixes required** — concrete list of what must change, or "None. Approved." if clean.

If fixes are required, instruct the implementer to fix and then request another review. Re-review only the fixes — do not re-report things already done well unless they regressed.

After approval, the implementer moves the task to `done/`, commits, and merges to main.
