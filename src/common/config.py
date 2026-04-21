"""Configuration helpers.

Secrets are read from process environment variables first, then from a local
`.env` file. This module deliberately does not print or expose secret values
in exceptions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


def get_env(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        value = _dotenv_values().get(name)
    if value is None or value == "":
        if required and default is None:
            raise ConfigError(f"Missing required environment variable: {name}")
        return default
    return value


def get_int_env(name: str, default: int | None = None, *, required: bool = False) -> int | None:
    value = get_env(name, None, required=required)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer") from exc


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=get_env("MYSQL_HOST", required=True) or "",
            port=get_int_env("MYSQL_PORT", 3306) or 3306,
            user=get_env("MYSQL_USER", required=True) or "",
            password=get_env("MYSQL_PASSWORD", required=True) or "",
            database=get_env("MYSQL_DATABASE", required=True) or "",
        )


@dataclass(frozen=True)
class ProviderTokens:
    tushare_token: str | None
    x_api_key: str | None

    @classmethod
    def from_env(cls) -> "ProviderTokens":
        return cls(
            tushare_token=get_env("TUSHARE_TOKEN"),
            x_api_key=get_env("X_API_KEY"),
        )


@lru_cache(maxsize=1)
def _dotenv_values() -> dict[str, str]:
    path = _dotenv_path()
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        parsed = _parse_dotenv_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        values[key] = value
    return values


def _dotenv_path() -> Path:
    override = os.getenv("AI3_ENV_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / ".env"


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = _strip_inline_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def _strip_inline_comment(value: str) -> str:
    in_single_quote = False
    in_double_quote = False
    for index, char in enumerate(value):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == "#" and not in_single_quote and not in_double_quote:
            if index == 0 or value[index - 1].isspace():
                return value[:index].strip()
    return value
