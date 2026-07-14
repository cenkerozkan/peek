"""peek: a safe, multi-database, read-only SQL MCP server."""

from importlib.metadata import PackageNotFoundError, version

_DISTRIBUTION_NAME = "peek-db"
_UNINSTALLED_VERSION = "0.0.0+unknown"

try:
    __version__ = version(_DISTRIBUTION_NAME)
except PackageNotFoundError:
    __version__ = _UNINSTALLED_VERSION

__all__ = ["__version__"]
