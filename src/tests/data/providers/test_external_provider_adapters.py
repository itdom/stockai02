from __future__ import annotations

from data.providers.akshare_provider import AkshareProvider
from data.providers.tushare_provider import TushareProvider


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient):
        assert orient == "records"
        return self.rows


class FakeTushareClient:
    def stock_basic(self, **kwargs):
        return FakeFrame([{"ts_code": "000001.SZ", "name": "平安银行"}])

    def daily(self, **kwargs):
        return FakeFrame([{"ts_code": kwargs["ts_code"], "trade_date": kwargs["start_date"]}])

    def weekly(self, **kwargs):
        return FakeFrame([{"ts_code": kwargs["ts_code"], "trade_date": kwargs["start_date"]}])


class FakeAkshareClient:
    def stock_info_a_code_name(self):
        return FakeFrame([{"code": "000001", "name": "平安银行"}])

    def stock_zh_a_hist(self, **kwargs):
        return FakeFrame([{"symbol": kwargs["symbol"], "period": kwargs["period"]}])


def test_tushare_provider_uses_client_adapter() -> None:
    provider = TushareProvider(client=FakeTushareClient())

    assert provider.fetch_instruments() == [{"ts_code": "000001.SZ", "name": "平安银行"}]
    assert provider.fetch_daily_bars("000001.SZ", "20260101", "20260131") == [
        {"ts_code": "000001.SZ", "trade_date": "20260101"}
    ]


def test_akshare_provider_uses_client_adapter() -> None:
    provider = AkshareProvider(client=FakeAkshareClient())

    assert provider.fetch_instruments() == [{"code": "000001", "name": "平安银行"}]
    assert provider.fetch_weekly_bars("000001.SZ", "20260101", "20260131") == [
        {"symbol": "000001", "period": "weekly"}
    ]
