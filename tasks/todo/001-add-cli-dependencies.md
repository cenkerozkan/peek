# 001 — Add CLI dependencies and update entry point

## Goal

`click` and `tomlkit` are declared as direct dependencies, and the console
entry point routes through a new `cli` module that preserves bare-`peek`
behaviour (MCP stdio server).

## Context

Peek currently has one entry point: `peek = "peek.server:main"`, which calls
`build_server().run(transport="stdio")` with no CLI framework. We are adding
subcommands (`peek init`, `peek db add/remove/list`). `click` is already a
transitive dep of `fastmcp` but must be declared directly since we import it.
`tomlkit` is needed for format-preserving TOML writes (later tasks).

Bare `peek` (no subcommand) **must** keep starting the MCP stdio server —
MCP clients launch `peek` with no args and pipe stdin/stdout.

Line length is 79 (PEP 8 strict). Use `typing` library, not PEP 604 pipes.
Google-style docstrings are optional but encouraged on public functions.

## Files

You may create or modify only these:

- `src/peek/cli/__init__.py` — new
- `src/peek/__main__.py` — modify: change import to `from peek.cli import main`
- `pyproject.toml` — modify: add deps, change entry point

## Specification

### `pyproject.toml`

Add to `dependencies`:
```
"click",
"tomlkit",
```

Change entry point:
```toml
[project.scripts]
peek = "peek.cli:main"
```

### `src/peek/cli/__init__.py`

```python
import click
from peek import __version__

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="peek")
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        from peek.server import build_server
        build_server().run(transport="stdio", show_banner=False)

def main() -> None:
    cli()
```

The lazy import of `peek.server` inside the `if` block is intentional — it
avoids loading SQLAlchemy/FastMCP when the user runs a subcommand like
`peek --version`.

### `src/peek/__main__.py`

Change to:
```python
from peek.cli import main

if __name__ == "__main__":
    main()
```

## Constraints

- `click.group(invoke_without_command=True)` is required so bare `peek`
  works. Do **not** use `standalone_mode=False`.
- The `cli` function must **not** print anything to stdout when invoked
  without a subcommand — stdout is the MCP channel.
- Do not add subcommands yet — later tasks handle that.
- Do not modify `src/peek/server.py`.

## Acceptance check

```bash
python -c "from peek.cli import main; print('import ok')"
python -c "import click; import tomlkit; print('deps ok')"
grep 'peek = "peek.cli:main"' pyproject.toml
```

All three commands must succeed with no errors.

## Out of scope

- Subcommands (`init`, `db`). Those are separate tasks.
- Tests for the CLI group itself (tested indirectly via subcommand tasks).
- Changes to `server.py`.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
