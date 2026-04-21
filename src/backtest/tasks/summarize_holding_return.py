"""Backward-compatible wrapper for the report-layer holding return summary task."""

from __future__ import annotations

from report.tasks.summarize_holding_return import (
    HoldingReturnSummary,
    ReturnStats,
    build_parser,
    build_repositories,
    main,
    render_markdown,
    run,
)


__all__ = [
    "HoldingReturnSummary",
    "ReturnStats",
    "build_parser",
    "build_repositories",
    "main",
    "render_markdown",
    "run",
]


if __name__ == "__main__":
    raise SystemExit(main())
