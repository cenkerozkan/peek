"""Pydantic models describing the on-disk connection registry."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class DatabaseEntry(BaseModel):
    """A single database registration read from the config file.

    Attributes:
        url: The SQLAlchemy connection string, held as a ``SecretStr`` so it
            never appears in a ``repr()``, log line, or serialized dump.
        dialect: Optional ``sqlglot`` dialect override, used when the
            SQLAlchemy dialect name doesn't match a ``sqlglot`` dialect.
        exclude_tables: A denylist of tables that must never reach any LLM's
            context. Bare names match that table in any schema; a
            ``schema.table`` name matches only that schema's table. Matching
            is case-insensitive. An empty list excludes nothing.
    """

    model_config = ConfigDict(extra="forbid")

    url: SecretStr
    dialect: Optional[str] = None
    exclude_tables: List[str] = Field(default_factory=list)
