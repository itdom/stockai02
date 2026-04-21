from __future__ import annotations

from pathlib import Path

from data.providers.csv_provider import CsvProvider


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_csv_provider_reads_instruments() -> None:
    provider = CsvProvider(instruments_path=FIXTURES / "instruments.csv")

    assert provider.fetch_instruments() == [{"symbol": "000001.SZ", "name": "平安银行"}]


def test_csv_provider_filters_market_rows() -> None:
    provider = CsvProvider(daily_bars_path=FIXTURES / "daily_bars.csv")

    assert provider.fetch_daily_bars("000001.SZ", "20260101", "20260131") == [
        {
            "symbol": "000001.SZ",
            "trade_date": "20260102",
            "open": "9.90",
            "high": "10.20",
            "low": "9.80",
            "close": "10.00",
            "pre_close": "9.90",
            "change": "0.10",
            "pct_chg": "1.01",
            "volume": "1000",
            "amount": "10000",
        }
    ]


def test_csv_provider_filters_weekly_rows_without_requiring_symbol() -> None:
    provider = CsvProvider(weekly_bars_path=FIXTURES / "weekly_bars.csv")

    rows = provider.fetch_weekly_bars(None, "20260101", "20260131")

    assert [row["symbol"] for row in rows] == ["000001.SZ", "000002.SZ"]
