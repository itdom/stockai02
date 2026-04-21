from __future__ import annotations

from pathlib import Path

from data.storage.table_registry import TABLES


MIGRATION = Path("src/data/storage/migrations/001_create_core_tables.sql")


def test_core_migration_contains_registered_tables_and_primary_keys() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    for table in TABLES.values():
        assert f"CREATE TABLE IF NOT EXISTS `{table.name}`" in sql
        primary_key = ", ".join(f"`{field}`" for field in table.primary_key)
        assert f"PRIMARY KEY ({primary_key})" in sql


def test_core_migration_contains_pipeline_run_batch_table() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS `pipeline_run_batch`" in sql
    assert "PRIMARY KEY (`run_id`)" in sql
    assert "`parameters_json` JSON NULL" in sql
    assert "`metrics_json` JSON NULL" in sql
    assert "`failed_dates_json` JSON NULL" in sql
