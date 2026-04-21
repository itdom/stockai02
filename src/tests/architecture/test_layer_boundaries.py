from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PROVIDER_IMPORT_LAYERS = ("strategy", "backtest", "report")
FORBIDDEN_BACKTEST_IMPORT_LAYERS = ("features", "strategy")


def test_strategy_backtest_and_report_do_not_import_data_providers() -> None:
    violations: list[str] = []
    for layer in FORBIDDEN_PROVIDER_IMPORT_LAYERS:
        for path in (SRC_ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("data.providers"):
                    violations.append(f"{path.relative_to(SRC_ROOT)} imports from {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("data.providers"):
                            violations.append(f"{path.relative_to(SRC_ROOT)} imports {alias.name}")

    assert violations == []


def test_features_and_strategy_do_not_import_backtest() -> None:
    violations: list[str] = []
    for layer in FORBIDDEN_BACKTEST_IMPORT_LAYERS:
        for path in (SRC_ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("backtest"):
                    violations.append(f"{path.relative_to(SRC_ROOT)} imports from {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("backtest"):
                            violations.append(f"{path.relative_to(SRC_ROOT)} imports {alias.name}")

    assert violations == []
