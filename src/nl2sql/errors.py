"""Shared exception hierarchy for the nl2sql server.

All project-specific exceptions derive from :class:`Nl2SqlError` so callers
can catch the whole family with one `except` clause. Messages raised from
these exceptions must never contain connection strings or other credential
material — see the credential-isolation rule in `docs/architecture.md`.
"""


class Nl2SqlError(Exception):
    """Base class for all nl2sql exceptions."""


class ConfigError(Nl2SqlError):
    """Raised when the config file or its contents are invalid."""


class RegistryError(Nl2SqlError):
    """Raised when a database cannot be resolved, connected to, or used.

    The message names only the database alias, never the connection string.
    """
