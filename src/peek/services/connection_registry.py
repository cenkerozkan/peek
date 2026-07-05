"""Resolves database aliases to validated SQLAlchemy engines.

Built once at startup from the config file (see
`docs/architecture.md` -> "Connection registry"). Callers outside this
module only ever see aliases and safe metadata -- never a connection
string.

``add``/``remove`` exist so a future non-model admin CLI can reuse this
class; they are intentionally not wired to any MCP tool.
"""

from typing import Dict, FrozenSet, List, Optional

from sqlalchemy import Engine

from src.peek.config import AppConfig
from src.peek.errors import RegistryError
from src.peek.infra.config_file import load_registry
from src.peek.infra.engines import build_engine
from src.peek.models.config import DatabaseEntry


class ConnectionRegistry:
    """In-memory map of alias -> validated SQLAlchemy engine."""

    def __init__(self) -> None:
        self._engines: Dict[str, Engine] = {}
        self._exclusions: Dict[str, FrozenSet[str]] = {}

    @classmethod
    def from_config(cls, config: AppConfig) -> "ConnectionRegistry":
        """Build a registry from the config file referenced by ``config``.

        Reads the resolved config file, builds an engine per alias, and
        validates each by opening and closing a connection.

        Args:
            config: Application settings pointing at a registry file.

        Returns:
            A ``ConnectionRegistry`` with one validated engine per alias.

        Raises:
            ConfigError: If the config file is missing or malformed.
            RegistryError: If any configured database fails to connect.
        """
        entries = load_registry(config.resolved_config_file())
        registry = cls()
        for alias, entry in entries.items():
            registry.add(alias, entry)
        return registry

    def add(self, alias: str, entry: DatabaseEntry) -> None:
        """Build, validate, and register an engine for ``alias``.

        Args:
            alias: The friendly name callers will use to address this
                database.
            entry: The connection details to build an engine from.

        Raises:
            RegistryError: If the engine cannot be built or a validation
                connection cannot be opened.
        """
        engine: Optional[Engine] = None
        try:
            engine = build_engine(entry)
            with engine.connect():
                pass
        except Exception as error:
            if engine is not None:
                engine.dispose()
            raise RegistryError(
                f"Could not connect to database: {alias}"
            ) from error
        self._engines[alias] = engine
        self._exclusions[alias] = frozenset(
            name.strip().lower()
            for name in entry.exclude_tables
            if name.strip()
        )

    def remove(self, alias: str) -> None:
        """Dispose of and forget the engine registered for ``alias``.

        Args:
            alias: The alias to remove.

        Raises:
            RegistryError: If ``alias`` is not registered.
        """
        engine = self._engines.pop(alias, None)
        if engine is None:
            raise RegistryError(f"Unknown database alias: {alias}")
        self._exclusions.pop(alias, None)
        engine.dispose()

    def aliases(self) -> List[str]:
        """Return the aliases of all registered databases."""
        return list(self._engines)

    def get_engine(self, alias: str) -> Engine:
        """Return the engine registered for ``alias``.

        Args:
            alias: The database alias to resolve.

        Returns:
            The validated engine for ``alias``.

        Raises:
            RegistryError: If ``alias`` is not registered.
        """
        try:
            return self._engines[alias]
        except KeyError as error:
            raise RegistryError(f"Unknown database alias: {alias}") from error

    def is_excluded(
        self, alias: str, table: str, schema: Optional[str] = None
    ) -> bool:
        """Return whether ``table`` is on ``alias``'s denylist.

        Matching is case-insensitive. A bare denylist name matches ``table``
        in any schema; a ``schema.table`` denylist name matches only when
        ``schema`` is supplied and equal. This is the single source of truth
        the schema and SQL services consult, so an excluded table is never
        revealed or queried.

        Args:
            alias: The database alias whose denylist to consult.
            table: The unqualified table name to test.
            schema: The namespace ``table`` lives in, if any.

        Returns:
            ``True`` if the table is excluded, ``False`` otherwise (including
            for an unregistered alias, which is rejected earlier by
            ``get_engine``).
        """
        patterns = self._exclusions.get(alias, frozenset())
        if not patterns:
            return False
        candidates = {table.lower()}
        if schema is not None:
            candidates.add(f"{schema.lower()}.{table.lower()}")
        return bool(candidates & patterns)

    def describe(self, alias: str) -> Dict[str, str]:
        """Return safe, credential-free metadata for ``alias``.

        Args:
            alias: The database alias to describe.

        Returns:
            A mapping with ``alias`` and ``dialect`` keys. Never includes a
            connection string.

        Raises:
            RegistryError: If ``alias`` is not registered.
        """
        engine = self.get_engine(alias)
        return {"alias": alias, "dialect": engine.dialect.name}

    def list_metadata(self) -> List[Dict[str, str]]:
        """Return safe metadata for every registered database."""
        return [self.describe(alias) for alias in self.aliases()]

    def dispose(self) -> None:
        """Dispose of every registered engine (server shutdown)."""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()
        self._exclusions.clear()
