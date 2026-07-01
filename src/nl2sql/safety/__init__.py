"""Safety layer: the single read-only SQL chokepoint."""

from src.nl2sql.safety.guard import UnsafeSQLError, ensure_read_only

__all__ = ["UnsafeSQLError", "ensure_read_only"]
