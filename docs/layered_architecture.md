# AI3 Layered Architecture

This document is the executable architecture contract for code layout and
batch execution.

## Layers

AI3 code should stay in these layers:

```text
data
  -> features / strategy
  -> backtest
  -> report
```

`common` is shared infrastructure and must not contain business logic.

## Data Layer

Package: `src/data/`

Responsibilities:

- external ingestion through `data.providers`
- raw-to-contract conversion through `data.normalizers`
- storage primitives through `data.storage`
- stable table access through `data.repositories`
- read-oriented business data access through `data.services`
- ingestion and validation tasks under `data.tasks`

Rules:

- `data.providers` may call external APIs.
- `data.providers` must not write database records.
- `data.normalizers` must not call external APIs or read databases.
- `data.repositories` must not call providers.
- `data.services` must not call providers.
- non-data layers must not import `data.providers`.

## Feature And Strategy Layer

Packages: `src/features/`, `src/strategy/`

Responsibilities:

- `features` computes indicators, derived features, and reusable signals from
  standardized data.
- `strategy` combines existing features and signals into strategy-specific
  decisions.

Rules:

- features and strategy read standardized data through repositories/services.
- features and strategy do not fetch external data.
- strategy should not calculate raw indicators that belong in `features`.
- strategy should not calculate returns that belong in `backtest`.

## Backtest Layer

Package: `src/backtest/`

Responsibilities:

- load strategy signals and standardized market data
- calculate holding-period returns and other backtest result records
- write backtest result tables

Rules:

- backtest does not call providers.
- backtest does not generate presentation reports.
- backtest stores raw result records; aggregation and presentation belong to
  `report`.

## Report Layer

Package: `src/report/`

Responsibilities:

- read completed data, feature, signal, or backtest result records
- aggregate statistics for human consumption
- render Markdown, JSON, CSV, or other report outputs

Rules:

- report tasks do not fetch external data.
- report tasks do not calculate strategy signals.
- report tasks do not mutate backtest result records.

Current report task:

```powershell
python -m report.tasks.summarize_holding_return --start-date 20260105 --end-date 20260421 --source tushare --write-db --output-path docs\reports\holding_return_20260105_20260421.md
```

The legacy entry point below is kept only for compatibility:

```powershell
python -m backtest.tasks.summarize_holding_return
```

New callers should use `report.tasks.summarize_holding_return`.

## Pipeline Layer

Package: `src/pipelines/`

Responsibilities:

- production batch orchestration
- provider selection at the outer boundary
- sequencing data, feature, signal, backtest, and report tasks

Rules:

- pipelines may call `data.tasks`, `features.tasks`, `backtest.tasks`, and
  `report.tasks`.
- pipelines may select providers because they are execution entry points.
- strategy, backtest, and report modules must not select providers directly.

Current production entry point:

```powershell
python -m pipelines.tasks.run_daily_refresh_pipeline --provider tushare --start-date 20260105 --end-date 20260421 --fetch-mode daily --write-db --overwrite --validate-data --report-output-path docs\reports\holding_return_20260105_20260421.md
```

When repositories are built by this task, every run is recorded in
`pipeline_run_batch` with the run id, parameters JSON, metrics JSON, status,
elapsed time, and any failed ingest dates. Status values are:

- `running`: the batch has started.
- `success`: all pipeline steps completed and no per-date ingest failures were reported.
- `partial_success`: pipeline steps completed, but daily range ingest reported failed dates.
- `failed`: an exception stopped the pipeline, including failed `validate_data` checks.

The daily ingest window is controlled by `--start-date` and `--end-date`.
Derived weekly/KDJ/signal/backtest stages expand that window by
`--derived-lookback-days` so a single-day refresh does not overwrite weekly bars
or KDJ values with a partial one-day calculation.

Recent runs can be checked with:

```powershell
python -m pipelines.tasks.summarize_pipeline_runs --write-db --limit 10
```

## Execution Order

Daily refresh should run as orchestration, not as strategy logic:

```text
1. data.tasks.ingest_stock_list
2. data.tasks.ingest_market_daily
3. data.tasks.build_weekly_bars
4. data.tasks.validate_data --domain instrument/market_daily/market_weekly
5. features.tasks.build_weekly_kdj
6. features.tasks.build_weekly_kdj_cross --overwrite
7. backtest.tasks.run_holding_return --overwrite
8. report.tasks.summarize_holding_return
```

For Tushare full-market history, prefer the formal daily range fetch mode to
avoid provider row limits:

```powershell
python -m data.tasks.ingest_market_daily --provider tushare --mode range --start-date 20260105 --end-date 20260421 --fetch-mode daily --write-db
```

## Compatibility Entry Point

`strategy.tasks.run_weekly_kdj_backtest_pipeline` is now only a compatibility
wrapper around `pipelines.tasks.run_daily_refresh_pipeline`. New production
execution behavior must be added to `pipelines`, not `strategy`.
