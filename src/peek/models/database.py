"""Pydantic model describing a registered database, credential-free.

This is the I/O type returned by the ``list_databases`` tool. It carries only
an alias and safe metadata -- never a connection string or other credential
material (see `docs/architecture.md` -> "Credential isolation").
"""

from pydantic import BaseModel, ConfigDict


class DatabaseInfo(BaseModel):
    """Safe, credential-free metadata for one registered database.

    Attributes:
        alias: The friendly name callers use to address this database.
        dialect: The database backend's SQLAlchemy dialect name.
    """

    model_config = ConfigDict(extra="forbid")

    alias: str
    dialect: str
