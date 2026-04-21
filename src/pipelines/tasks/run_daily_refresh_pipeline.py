"""Production daily refresh pipeline for the weekly KDJ backtest chain.

This module is the orchestration layer. It is allowed to compose data ingestion,
feature building, signal generation, backtesting, and report output without
putting provider knowledge into strategy, backtest, or report modules.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from backtest.repositories.holding_return_repo import HoldingReturnRepository
from backtest.tasks import run_holding_return
from common.logger import configure_logging, get_logger
from common.timeutils import format_yyyymmdd, parse_yyyymmdd, week_monday
from data.providers.akshare_provider import AkshareProvider
from data.providers.base import MarketDataProvider
from data.providers.csv_provider import CsvProvider
from data.providers.tushare_provider import TushareProvider
from data.repositories.base import InMemoryRecordWriter, RecordWriter
from data.repositories.instrument_repo import InstrumentRepository
from data.repositories.market_repo import MarketRepository
from data.storage.db import load_database_config
from data.storage.mysql_writer import MySqlRecordWriter, connect_mysql
from data.tasks import build_weekly_bars, ingest_market_daily, ingest_stock_list
from data.tasks import validate_data as validate_data_task
from features.repositories.kdj_repo import KdjFeatureRepository
from features.repositories.signal_repo import KdjCrossSignalRepository
from features.tasks import build_weekly_kdj, build_weekly_kdj_cross
from pipelines.repositories.run_batch_repo import PipelineRunBatchRepository
from report.tasks import summarize_holding_return


LOGGER = get_logger(__name__)
PIPELINE_NAME = "daily_refresh_pipeline"
DEFAULT_VALIDATION_DOMAINS = ("instrument", "market_daily", "market_weekly")
DEFAULT_DERIVED_LOOKBACK_DAYS = 120


@dataclass(frozen=True)
class DailyRefreshPipelineResult:
    stock_list: ingest_stock_list.IngestStockListResult
    market_daily: ingest_market_daily.IngestMarketDailyResult
    weekly_bars: build_weekly_bars.BuildWeeklyBarsResult
    weekly_kdj: build_weekly_kdj.BuildWeeklyKdjResult
    weekly_kdj_cross: build_weekly_kdj_cross.BuildWeeklyKdjCrossResult
    holding_return: run_holding_return.RunHoldingReturnResult
    holding_return_summary: summarize_holding_return.HoldingReturnSummary | None = None
    validation_summaries: tuple[validate_data_task.ValidationSummary, ...] = ()
    pipeline_run_id: str | None = None


WeeklyKdjBacktestPipelineResult = DailyRefreshPipelineResult


@dataclass(frozen=True)
class PipelineRepositories:
    instrument_repository: InstrumentRepository
    market_repository: MarketRepository
    kdj_repository: KdjFeatureRepository
    signal_repository: KdjCrossSignalRepository
    holding_return_repository: HoldingReturnRepository
    pipeline_run_repository: PipelineRunBatchRepository | None = None


def run(
    *,
    stock_provider: MarketDataProvider,
    market_provider: MarketDataProvider,
    repositories: PipelineRepositories,
    start_date: str,
    end_date: str,
    symbol: str | None = None,
    limit: int | None = None,
    fetch_mode: str = "window",
    kdj_n: int = 9,
    horizons: tuple[int, ...] = run_holding_return.DEFAULT_HORIZONS,
    overwrite: bool = False,
    derived_lookback_days: int = DEFAULT_DERIVED_LOOKBACK_DAYS,
    validate_data: bool = False,
    validation_domains: tuple[str, ...] = DEFAULT_VALIDATION_DOMAINS,
    report_output_path: str | None = None,
    report_output_format: str = "markdown",
) -> DailyRefreshPipelineResult:
    derived_start_date, derived_end_date = _derive_processing_window(
        start_date=start_date,
        end_date=end_date,
        lookback_days=derived_lookback_days,
    )
    LOGGER.info(
        "daily_refresh_pipeline started symbol=%s start_date=%s end_date=%s derived_start_date=%s derived_end_date=%s limit=%s fetch_mode=%s kdj_n=%s horizons=%s overwrite=%s",
        symbol,
        start_date,
        end_date,
        derived_start_date,
        derived_end_date,
        limit,
        fetch_mode,
        kdj_n,
        horizons,
        overwrite,
    )
    batch_handle = None
    failed_dates: tuple[str, ...] = ()
    if repositories.pipeline_run_repository is not None:
        batch_handle = repositories.pipeline_run_repository.start_run(
            pipeline_name=PIPELINE_NAME,
            parameters=_pipeline_parameters(
                stock_provider=stock_provider,
                market_provider=market_provider,
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                limit=limit,
                fetch_mode=fetch_mode,
                kdj_n=kdj_n,
                horizons=horizons,
                overwrite=overwrite,
                derived_lookback_days=derived_lookback_days,
                derived_start_date=derived_start_date,
                derived_end_date=derived_end_date,
                validate_data=validate_data,
                validation_domains=validation_domains,
                report_output_path=report_output_path,
                report_output_format=report_output_format,
            ),
        )

    try:
        stock_list_result = ingest_stock_list.run(
            stock_provider,
            repositories.instrument_repository,
            limit=limit,
        )
        ingest_runner = ingest_market_daily.run_daily_range if fetch_mode == "daily" else ingest_market_daily.run
        market_daily_result = ingest_runner(
            market_provider,
            repositories.market_repository,
            start_date=start_date,
            end_date=end_date,
            symbol=symbol,
            limit=limit,
        )
        failed_dates = market_daily_result.failed_dates
        weekly_bars_result = build_weekly_bars.run(
            repositories.market_repository,
            start_date=derived_start_date,
            end_date=derived_end_date,
            symbol=symbol,
        )
        validation_summaries: tuple[validate_data_task.ValidationSummary, ...] = ()
        if validate_data:
            validation_summaries = _run_validations(
                repositories,
                domains=validation_domains,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                weekly_start_date=derived_start_date,
                weekly_end_date=derived_end_date,
            )
            _raise_for_validation_errors(validation_summaries)
        weekly_kdj_result = build_weekly_kdj.run(
            repositories.market_repository,
            repositories.kdj_repository,
            start_date=derived_start_date,
            end_date=derived_end_date,
            symbol=symbol,
            n=kdj_n,
        )
        weekly_kdj_cross_result = build_weekly_kdj_cross.run(
            repositories.kdj_repository,
            repositories.signal_repository,
            start_date=derived_start_date,
            end_date=derived_end_date,
            symbol=symbol,
            overwrite=overwrite,
        )
        holding_return_result = run_holding_return.run(
            repositories.signal_repository,
            repositories.market_repository,
            repositories.holding_return_repository,
            start_date=derived_start_date,
            end_date=derived_end_date,
            symbol=symbol,
            horizons=horizons,
            overwrite=overwrite,
        )
        holding_return_summary = None
        if report_output_path:
            holding_return_summary = summarize_holding_return.run(
                repositories.holding_return_repository,
                repositories.instrument_repository,
                start_date=start_date,
                end_date=end_date,
                source=market_provider.source_name,
                output_path=report_output_path,
                output_format=report_output_format,
            )
        result = DailyRefreshPipelineResult(
            stock_list=stock_list_result,
            market_daily=market_daily_result,
            weekly_bars=weekly_bars_result,
            weekly_kdj=weekly_kdj_result,
            weekly_kdj_cross=weekly_kdj_cross_result,
            holding_return=holding_return_result,
            holding_return_summary=holding_return_summary,
            validation_summaries=validation_summaries,
            pipeline_run_id=batch_handle.run_id if batch_handle else None,
        )
    except Exception as exc:
        if repositories.pipeline_run_repository is not None and batch_handle is not None:
            repositories.pipeline_run_repository.finish_run(
                batch_handle,
                status="failed",
                failed_dates=failed_dates,
                error_message=str(exc),
            )
        raise

    if repositories.pipeline_run_repository is not None and batch_handle is not None:
        repositories.pipeline_run_repository.finish_run(
            batch_handle,
            status="partial_success" if failed_dates else "success",
            failed_dates=failed_dates,
            metrics=summarize_result(result),
        )
    LOGGER.info(
        "daily_refresh_pipeline finished stocks=%s daily=%s weekly=%s kdj=%s signals=%s returns=%s validations=%s report=%s",
        result.stock_list.saved_count,
        result.market_daily.saved_count,
        result.weekly_bars.saved_count,
        result.weekly_kdj.saved_count,
        result.weekly_kdj_cross.saved_count,
        result.holding_return.saved_count,
        len(result.validation_summaries),
        result.holding_return_summary is not None,
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI3 daily refresh pipeline")
    parser.add_argument("--provider", choices=("csv", "tushare", "akshare"), required=True)
    parser.add_argument("--instruments-csv-path", help="Instrument CSV path used when --provider csv")
    parser.add_argument("--daily-bars-csv-path", help="Daily bar CSV path used when --provider csv")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--fetch-mode",
        choices=("window", "daily"),
        default="window",
        help="Use daily for full-market Tushare history to avoid provider row limits.",
    )
    parser.add_argument("--kdj-n", type=int, default=9)
    parser.add_argument("--horizons", default="5,10,20,60")
    parser.add_argument(
        "--derived-lookback-days",
        type=int,
        default=DEFAULT_DERIVED_LOOKBACK_DAYS,
        help="Expand derived weekly/KDJ/signal/backtest processing before start date.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite signal and backtest result rows in the requested date window.",
    )
    parser.add_argument(
        "--validate-data",
        action="store_true",
        help="Run data.tasks.validate_data after daily and weekly market data are built.",
    )
    parser.add_argument(
        "--validate-domains",
        default="instrument,market_daily,market_weekly",
        help="Comma-separated validate_data domains to run when --validate-data is enabled.",
    )
    parser.add_argument("--report-output-path", default=None)
    parser.add_argument("--report-output-format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Use MySQL. By default the task uses dry-run memory repositories.",
    )
    return parser


def build_providers(args: argparse.Namespace) -> tuple[MarketDataProvider, MarketDataProvider]:
    if args.provider == "csv":
        provider = CsvProvider(
            instruments_path=args.instruments_csv_path,
            daily_bars_path=args.daily_bars_csv_path,
        )
        return provider, provider
    if args.provider == "tushare":
        provider = TushareProvider()
        return provider, provider
    if args.provider == "akshare":
        provider = AkshareProvider()
        return provider, provider
    raise ValueError(f"Unsupported provider: {args.provider}")


def build_repositories(args: argparse.Namespace) -> PipelineRepositories:
    writer: RecordWriter
    if args.write_db:
        config = load_database_config()
        writer = MySqlRecordWriter(connect_mysql(config))
    else:
        writer = InMemoryRecordWriter()

    return PipelineRepositories(
        instrument_repository=InstrumentRepository(writer),
        market_repository=MarketRepository(writer),
        kdj_repository=KdjFeatureRepository(writer),
        signal_repository=KdjCrossSignalRepository(writer),
        holding_return_repository=HoldingReturnRepository(writer),
        pipeline_run_repository=PipelineRunBatchRepository(writer),
    )


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    stock_provider, market_provider = build_providers(args)
    repositories = build_repositories(args)
    result = run(
        stock_provider=stock_provider,
        market_provider=market_provider,
        repositories=repositories,
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=args.symbol,
        limit=args.limit,
        fetch_mode=args.fetch_mode,
        kdj_n=args.kdj_n,
        horizons=run_holding_return.parse_horizons(args.horizons),
        overwrite=args.overwrite,
        derived_lookback_days=args.derived_lookback_days,
        validate_data=args.validate_data,
        validation_domains=parse_validation_domains(args.validate_domains),
        report_output_path=args.report_output_path,
        report_output_format=args.report_output_format,
    )
    LOGGER.info("summary=%s", summarize_result(result))
    return 1 if result.market_daily.failed_dates else 0


def summarize_result(result: DailyRefreshPipelineResult) -> dict[str, object]:
    return {
        "run_id": result.pipeline_run_id,
        "stocks_saved": result.stock_list.saved_count,
        "daily_saved": result.market_daily.saved_count,
        "daily_failed_dates": list(result.market_daily.failed_dates),
        "weekly_saved": result.weekly_bars.saved_count,
        "kdj_saved": result.weekly_kdj.saved_count,
        "signals_saved": result.weekly_kdj_cross.saved_count,
        "holding_returns_saved": result.holding_return.saved_count,
        "validation_errors": {
            summary.domain: summary.error_count
            for summary in result.validation_summaries
        },
        "report_written": result.holding_return_summary is not None,
    }


def parse_validation_domains(value: str) -> tuple[str, ...]:
    domains = tuple(item.strip() for item in value.split(",") if item.strip())
    supported = set(DEFAULT_VALIDATION_DOMAINS)
    unsupported = [domain for domain in domains if domain not in supported]
    if unsupported:
        raise ValueError(f"Unsupported pipeline validation domain(s): {', '.join(unsupported)}")
    return domains


def _run_validations(
    repositories: PipelineRepositories,
    *,
    domains: tuple[str, ...],
    symbol: str | None,
    start_date: str,
    end_date: str,
    weekly_start_date: str,
    weekly_end_date: str,
) -> tuple[validate_data_task.ValidationSummary, ...]:
    summaries: list[validate_data_task.ValidationSummary] = []
    for domain in domains:
        summaries.append(
            validate_data_task.run(
                domain=domain,
                instrument_repository=repositories.instrument_repository,
                market_repository=repositories.market_repository,
                symbol=symbol if domain != "instrument" else None,
                start_date=weekly_start_date if domain == "market_weekly" else start_date,
                end_date=weekly_end_date if domain == "market_weekly" else end_date,
            )
        )
    return tuple(summaries)


def _raise_for_validation_errors(
    summaries: tuple[validate_data_task.ValidationSummary, ...],
) -> None:
    failed_domains = [summary.domain for summary in summaries if not summary.passed]
    if failed_domains:
        raise RuntimeError(f"validate_data failed domain(s): {', '.join(failed_domains)}")


def _pipeline_parameters(
    *,
    stock_provider: MarketDataProvider,
    market_provider: MarketDataProvider,
    start_date: str,
    end_date: str,
    symbol: str | None,
    limit: int | None,
    fetch_mode: str,
    kdj_n: int,
    horizons: tuple[int, ...],
    overwrite: bool,
    derived_lookback_days: int,
    derived_start_date: str,
    derived_end_date: str,
    validate_data: bool,
    validation_domains: tuple[str, ...],
    report_output_path: str | None,
    report_output_format: str,
) -> dict[str, object]:
    return {
        "stock_provider": stock_provider.source_name,
        "market_provider": market_provider.source_name,
        "start_date": start_date,
        "end_date": end_date,
        "symbol": symbol,
        "limit": limit,
        "fetch_mode": fetch_mode,
        "kdj_n": kdj_n,
        "horizons": list(horizons),
        "overwrite": overwrite,
        "derived_lookback_days": derived_lookback_days,
        "derived_start_date": derived_start_date,
        "derived_end_date": derived_end_date,
        "validate_data": validate_data,
        "validation_domains": list(validation_domains),
        "report_output_path": report_output_path,
        "report_output_format": report_output_format,
    }


def _derive_processing_window(
    *,
    start_date: str,
    end_date: str,
    lookback_days: int,
) -> tuple[str, str]:
    if lookback_days < 0:
        raise ValueError("derived_lookback_days must be non-negative")
    start = parse_yyyymmdd(start_date) - timedelta(days=lookback_days)
    end = parse_yyyymmdd(end_date)
    week_end = end + timedelta(days=4 - end.weekday())
    return week_monday(start), format_yyyymmdd(week_end)


if __name__ == "__main__":
    raise SystemExit(main())
