"""Preflight checks for ``peek db`` commands.

Each db subcommand should call ``require_config()`` at the top of its
function body, before any prompts, file reads, or other logic.
"""

from pathlib import Path

import click

NOT_INITIALIZED_MSG = "peek is not initialized. Run 'peek init' first."
NO_CONFIG_FILE_MSG = "No config file found. Run 'peek init' first."


def require_config() -> Path:
    """Ensure peek is initialized and a config file exists.

    Checks the parent directory of the resolved path (the ``.peek/``
    directory for the local config case) and the config file itself.

    Returns:
        The resolved config path when both checks pass.

    Raises:
        SystemExit: Code 1 with a message to stderr when either check fails.
    """
    from peek.config import resolve_config_path

    path = resolve_config_path()

    if not path.parent.is_dir():
        click.echo(NOT_INITIALIZED_MSG, err=True)
        raise SystemExit(1) from None

    if not path.is_file():
        click.echo(NO_CONFIG_FILE_MSG, err=True)
        raise SystemExit(1) from None

    return path
