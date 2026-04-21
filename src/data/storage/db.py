"""Database configuration holder.

Connection pooling will be implemented with the selected MySQL driver in a
later task. This module intentionally avoids importing a driver in M1.
"""

from __future__ import annotations

from common.config import DatabaseConfig


def load_database_config() -> DatabaseConfig:
    return DatabaseConfig.from_env()
