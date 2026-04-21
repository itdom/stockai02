"""Compatibility wrapper for the pipeline-layer daily refresh task.

The production orchestration lives in `pipelines.tasks.run_daily_refresh_pipeline`.
This module is kept so older CSV acceptance commands continue to work without
putting provider selection or ingestion orchestration in the strategy layer.
"""

from __future__ import annotations

from pipelines.tasks.run_daily_refresh_pipeline import (
    DailyRefreshPipelineResult,
    PipelineRepositories,
    WeeklyKdjBacktestPipelineResult,
    build_parser,
    build_providers,
    build_repositories,
    main,
    run,
)


__all__ = [
    "DailyRefreshPipelineResult",
    "PipelineRepositories",
    "WeeklyKdjBacktestPipelineResult",
    "build_parser",
    "build_providers",
    "build_repositories",
    "main",
    "run",
]


if __name__ == "__main__":
    raise SystemExit(main())
