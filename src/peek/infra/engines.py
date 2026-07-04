"""Builds SQLAlchemy engines from registry entries.

This is the only module allowed to unwrap a :class:`SecretStr` connection
string. The resulting URL must never be logged or included in an exception
message.
"""

from sqlalchemy import Engine, create_engine

from src.peek.errors import RegistryError
from src.peek.models.config import DatabaseEntry


def build_engine(entry: DatabaseEntry) -> Engine:
    """Create a pooled SQLAlchemy engine for a registry entry.

    Args:
        entry: The database entry whose ``url`` should be connected to.

    Returns:
        A SQLAlchemy ``Engine`` with connection pre-ping enabled.

    Raises:
        RegistryError: If engine creation fails. The message does not
            include the connection string, since SQLAlchemy errors can echo
            it back.
    """
    try:
        return create_engine(entry.url.get_secret_value(), pool_pre_ping=True)
    except Exception as error:
        raise RegistryError(
            "Could not build a database engine from the configured "
            "connection string."
        ) from error
