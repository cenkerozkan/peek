"""``peek init`` — bootstrap a project-local peek config directory."""

from pathlib import Path

import click

_DATABASES_TEMPLATE = """# Database configuration for peek.
#
# Copy the example below and fill in your own connection URL.
# The URL is the only required field; the rest are optional.
#
# [databases]
#   [databases.my_db]
#   # url = "postgresql://user:pass@localhost/dbname"
#   # dialect = "postgresql"
#   # exclude_tables = ["internal_logs", "audit_trail"]
"""

_GITIGNORE_ENTRY = "\n# peek — contains database credentials\n.peek/\n"


def _write_gitignore(cwd: Path) -> None:
    """Ensure .peek/ is listed in .gitignore.

    If the file does not exist, create it with the entry.
    If it exists, append the entry only when not already present.
    """
    gitignore = cwd / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(_GITIGNORE_ENTRY)
        return

    existing = gitignore.read_text()
    if ".peek/" not in existing:
        with gitignore.open("a") as fh:
            fh.write(_GITIGNORE_ENTRY)


@click.command()
def init() -> None:
    """Create a .peek/ config directory with a databases.toml template.

    After init, run 'peek db add' to register your first database.
    """
    cwd = Path.cwd()
    peek_dir = cwd / ".peek"

    if peek_dir.exists():
        click.echo("Already initialized: .peek/ directory exists.", err=True)
        raise SystemExit(1)

    peek_dir.mkdir()

    databases_toml = peek_dir / "databases.toml"
    databases_toml.write_text(_DATABASES_TEMPLATE)

    _write_gitignore(cwd)

    abs_path = cwd.resolve()
    click.echo(
        f"Created {abs_path}/.peek/databases.toml\n"
        f"Next: run `peek db add` to register a database.",
        err=True,
    )
