from __future__ import annotations

from data.storage.mysql_writer import MySqlRecordWriter, build_delete_where_sql, build_upsert_sql
from data.storage.table_registry import get_table_spec


class FakeCursor:
    def __init__(self) -> None:
        self.calls = []
        self.closed = False
        self.description = (("symbol",), ("name",))
        self.rows = (("000001.SZ", "Ping An"),)

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return 1

    def executemany(self, sql, params):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


def test_build_upsert_sql_quotes_identifiers() -> None:
    table = get_table_spec("instrument")

    sql = build_upsert_sql(table)

    assert sql.startswith("INSERT INTO `instrument`")
    assert "`symbol`" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "`name` = VALUES(`name`)" in sql
    assert "`symbol` = VALUES(`symbol`)" not in sql


def test_mysql_writer_executes_batch_and_commits() -> None:
    connection = FakeConnection()
    writer = MySqlRecordWriter(connection)
    table = get_table_spec("instrument")

    saved = writer.upsert(
        table,
        [
            {
                field: "000001.SZ" if field == "symbol" else None
                for field in table.fields
            }
        ],
    )

    assert saved == 1
    assert connection.committed is True
    assert connection.cursor_instance.closed is True
    sql, params = connection.cursor_instance.calls[0]
    assert sql.startswith("INSERT INTO `instrument`")
    assert params == [tuple("000001.SZ" if field == "symbol" else None for field in table.fields)]


def test_mysql_writer_reads_all_records() -> None:
    connection = FakeConnection()
    writer = MySqlRecordWriter(connection)

    records = writer.all_records("instrument")

    assert records == [{"symbol": "000001.SZ", "name": "Ping An"}]
    assert connection.cursor_instance.closed is True
    sql, params = connection.cursor_instance.calls[0]
    assert sql.startswith("SELECT `symbol`, `name`,")
    assert params is None


def test_mysql_writer_reads_all_records_for_custom_table_spec() -> None:
    connection = FakeConnection()
    writer = MySqlRecordWriter(connection)
    table = get_table_spec("instrument")

    records = writer.all_records_for_table(table)

    assert records == [{"symbol": "000001.SZ", "name": "Ping An"}]
    sql, params = connection.cursor_instance.calls[0]
    assert sql.startswith("SELECT `symbol`, `name`,")
    assert params is None


def test_build_delete_where_sql_requires_filters_and_quotes_fields() -> None:
    table = get_table_spec("signal_kdj_cross")

    sql, params = build_delete_where_sql(
        table,
        equals={"frequency": "1w", "symbol": "000001.SZ"},
        ranges={"trade_date": ("20260101", "20260131")},
    )

    assert sql == (
        "DELETE FROM `signal_kdj_cross` WHERE "
        "`frequency` = %s AND `symbol` = %s AND `trade_date` >= %s AND `trade_date` <= %s"
    )
    assert params == ("1w", "000001.SZ", "20260101", "20260131")


def test_mysql_writer_delete_where_executes_and_commits() -> None:
    connection = FakeConnection()
    writer = MySqlRecordWriter(connection)
    table = get_table_spec("backtest_holding_return")

    deleted = writer.delete_where(
        table,
        ranges={"signal_date": ("20260101", "20260131")},
    )

    assert deleted == 1
    assert connection.committed is True
    assert connection.cursor_instance.closed is True
    sql, params = connection.cursor_instance.calls[0]
    assert sql == "DELETE FROM `backtest_holding_return` WHERE `signal_date` >= %s AND `signal_date` <= %s"
    assert params == ("20260101", "20260131")
