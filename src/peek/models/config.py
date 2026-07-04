"""Pydantic models describing the on-disk connection registry."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, SecretStr


class DatabaseEntry(BaseModel):
    """A single database registration read from the config file.

    Attributes:
        url: The SQLAlchemy connection string, held as a ``SecretStr`` so it
            never appears in a ``repr()``, log line, or serialized dump.
        dialect: Optional ``sqlglot`` dialect override, used when the
            SQLAlchemy dialect name doesn't match a ``sqlglot`` dialect.
    """

    model_config = ConfigDict(extra="forbid")

    url: SecretStr
    dialect: Optional[str] = None
