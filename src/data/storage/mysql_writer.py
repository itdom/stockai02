"""MySQL writer for standardized repository records."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any, Protocol

from common.config import DatabaseConfig
from data.storage.table_registry import TableSpec, get_table_spec


class Cursor(Protocol):
    description: Sequence[Sequence[Any]] | None

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        ...

    def executemany(self, sql: str, params: Sequence[Sequence[Any]]) -> Any:
        ...

    def fetchall(self) -> Sequence[Sequence[Any]]:
        ...

    def close(self) -> Any:
        ...


class Connection(Protocol):
    def cursor(self) -> Cursor:
        ...

    def commit(self) -> Any:
        ...


class MySqlRecordWriter:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def upsert(self, table: TableSpec, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        sql = build_upsert_sql(table)
        params = [tuple(record[field] for field in table.fields) for record in records]
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, params)
            self.connection.commit()
        finally:
            cursor.close()
        return len(records)

    def delete_where(
        self,
        table: TableSpec,
        *,
        equals: Mapping[str, Any] | None = None,
        ranges: Mapping[str, tuple[Any | None, Any | None]] | None = None,
    ) -> int:
        sql, params = build_delete_where_sql(table, equals=equals, ranges=ranges)
        cursor = self.connection.cursor()
        try:
            result = cursor.execute(sql, params)
            self.connection.commit()
        finally:
            cursor.close()
        return int(result or 0)

    def all_records(self, table_name: str) -> list[dict[str, Any]]:
        table = get_table_spec(table_name)
        return self.all_records_for_table(table)

    def all_records_for_table(self, table: TableSpec) -> list[dict[str, Any]]:
        fields = ", ".join(_quote_identifier(field) for field in table.fields)
        sql = f"SELECT {fields} FROM {_quote_identifier(table.name)}"
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description or []]
        finally:
            cursor.close()
        return [dict(zip(columns, row)) for row in rows]


def build_upsert_sql(table: TableSpec) -> str:
    fields = ", ".join(_quote_identifier(field) for field in table.fields)
    placeholders = ", ".join(["%s"] * len(table.fields))
    update_fields = [field for field in table.fields if field not in table.primary_key]
    updates = ", ".join(
        f"{_quote_identifier(field)} = VALUES({_quote_identifier(field)})"
        for field in update_fields
    )
    return (
        f"INSERT INTO {_quote_identifier(table.name)} ({fields}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )


def build_delete_where_sql(
    table: TableSpec,
    *,
    equals: Mapping[str, Any] | None = None,
    ranges: Mapping[str, tuple[Any | None, Any | None]] | None = None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    params: list[Any] = []
    valid_fields = set(table.fields)

    for field, value in (equals or {}).items():
        _ensure_table_field(table, field, valid_fields)
        clauses.append(f"{_quote_identifier(field)} = %s")
        params.append(value)

    for field, (start, end) in (ranges or {}).items():
        _ensure_table_field(table, field, valid_fields)
        if start is not None:
            clauses.append(f"{_quote_identifier(field)} >= %s")
            params.append(start)
        if end is not None:
            clauses.append(f"{_quote_identifier(field)} <= %s")
            params.append(end)

    if not clauses:
        raise ValueError("delete_where requires at least one filter")

    sql = f"DELETE FROM {_quote_identifier(table.name)} WHERE " + " AND ".join(clauses)
    return sql, tuple(params)


def connect_mysql(config: DatabaseConfig) -> Connection:
    try:
        import pymysql  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pymysql is required for MySQL writes") from exc

    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        autocommit=False,
    )


def _quote_identifier(value: str) -> str:
    if "`" in value:
        raise ValueError(f"Invalid SQL identifier: {value}")
    return f"`{value}`"


def _ensure_table_field(table: TableSpec, field: str, valid_fields: set[str]) -> None:
    if field not in valid_fields:
        raise ValueError(f"Unknown field for {table.name}: {field}")
