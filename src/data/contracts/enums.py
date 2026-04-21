"""Shared enum values for internal contracts."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class DataSource(StrEnum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    X = "x"
    CSV = "csv"
    OTHER = "other"


class Frequency(StrEnum):
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"


class Market(StrEnum):
    SH = "SH"
    SZ = "SZ"
    BJ = "BJ"


class AssetType(StrEnum):
    STOCK = "stock"
    INDEX = "index"
    FUND = "fund"


class EntityType(StrEnum):
    STOCK = "stock"
    SECTOR = "sector"
    INDEX = "index"
    THEME = "theme"
    KEYWORD = "keyword"
