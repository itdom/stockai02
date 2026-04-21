# AI3

AI3 是 A 股全市场量化回测系统，目标是扫描沪深两市股票的周线 KDJ 金叉信号，并统计信号后 5 / 10 / 20 / 60 个交易日的持仓收益。

## 文档入口

面向人阅读：

- [docs/README.md](docs/README.md)：人工文档索引。
- [docs/data_architecture.md](docs/data_architecture.md)：数据底座架构说明。
- [docs/readmin01.txt](docs/readmin01.txt)：参考项目阅读笔记。

面向 AI Agent 读取：

- [AGENTS.md](AGENTS.md)：项目规则、模块边界和编码约束。
- [docs/AI_TASKS.md](docs/AI_TASKS.md)：AI 执行计划和里程碑任务。

## 当前阶段

当前仓库已完成 `src/` 下的 M1 基础代码骨架，并跑通 M2 股票列表 CSV 接入链路、M3 日线行情 CSV 接入链路、M4 外部周线接入与日线聚合周线链路、M5 X/Twitter 原始帖子接入骨架、基础数据验证任务、data services 读取层、周线 KDJ/金叉信号计算、持仓收益基础回测和 CSV 端到端验收 pipeline。接入、特征、信号、验证和回测任务已具备 dry-run 内存写入和 MySQL upsert writer 骨架。

## 代码目录约定

所有 Python 代码和测试代码都从 `src/` 作为一级目录开始：

- `src/common/`：通用配置、日志、日期工具。
- `src/data/`：数据契约、provider、normalizer、storage、repository、service 和 task。
- `src/features/`：指标、信号和舆情特征。
- `src/backtest/`：回测模块。
- `src/strategy/`：策略组合模块。
- `src/tests/`：测试代码。

## 本地验证

运行测试：

```powershell
python -m pytest
```

运行股票列表 CSV dry-run：

```powershell
$env:PYTHONPATH='src'
python -m data.tasks.ingest_stock_list --provider csv --csv-path src\tests\fixtures\instruments.csv --limit 1
```

运行日线行情 CSV dry-run：

```powershell
$env:PYTHONPATH='src'
python -m data.tasks.ingest_market_daily --provider csv --csv-path src\tests\fixtures\daily_bars.csv --start-date 20260101 --end-date 20260131 --symbol 000001.SZ --limit 1
```

运行周线构建 dry-run：

```powershell
$env:PYTHONPATH='src'
python -m data.tasks.build_weekly_bars
```

运行外部周线行情 CSV dry-run：

```powershell
$env:PYTHONPATH='src'
python -m data.tasks.ingest_market_weekly --provider csv --csv-path src\tests\fixtures\weekly_bars.csv --start-date 20260101 --end-date 20260131 --symbol 000001.SZ --limit 1
```

日线和周线行情接入任务支持 `--mode range|date|increment|all|sample`。默认 `range` 与旧命令兼容；`increment` 会从 repository 中已有最大 `trade_date` 的下一天开始。

运行周线 KDJ dry-run：

```powershell
$env:PYTHONPATH='src'
python -m features.tasks.build_weekly_kdj
```

运行周线 KDJ 金叉 dry-run：

```powershell
$env:PYTHONPATH='src'
python -m features.tasks.build_weekly_kdj_cross
```

运行持仓收益回测 dry-run：

```powershell
$env:PYTHONPATH='src'
python -m backtest.tasks.run_holding_return
```

运行基础数据验证：

```powershell
$env:PYTHONPATH='src'
python -m data.tasks.validate_data --domain market_daily --daily-bars-csv-path src\tests\fixtures\daily_bars.csv --start-date 20260101 --end-date 20260131 --symbol 000001.SZ
```

运行 X/Twitter 原始帖子接入：

```powershell
$env:PYTHONPATH='src'
$env:X_API_KEY='your_api_key'
python -m data.tasks.ingest_x_posts --query "AI" --start-time 20260420 --end-time 20260421 --limit 20
```

运行端到端 CSV 验收 pipeline：

```powershell
$env:PYTHONPATH='src'
python -m strategy.tasks.run_weekly_kdj_backtest_pipeline --provider csv --instruments-csv-path src\tests\fixtures\e2e_instruments.csv --daily-bars-csv-path src\tests\fixtures\e2e_daily_bars.csv --start-date 20260101 --end-date 20260131 --symbol 000001.SZ --kdj-n 2 --horizons 1,2
```

写入 MySQL 时显式增加 `--write-db`，并确保根目录 `.env` 或系统环境变量中已经配置 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`。

本地 `.env` 示例：

```text
TUSHARE_TOKEN=your_tushare_token
X_API_KEY=your_x_api_key
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ai3
```

配置读取优先级：系统环境变量优先，缺失时读取项目根目录 `.env`。`.env` 已被 `.gitignore` 忽略，不要提交真实密钥。

MySQL 建表脚本位于：

- `src/data/storage/migrations/001_create_core_tables.sql`

## Layering Notes

Architecture rules for data / strategy / backtest / report separation are in:

- `docs/layered_architecture.md`

Use the pipeline-layer entry point for production orchestration:

```powershell
$env:PYTHONPATH='src'
python -m pipelines.tasks.run_daily_refresh_pipeline --provider tushare --start-date 20260105 --end-date 20260421 --fetch-mode daily --write-db --overwrite --validate-data --report-output-path docs\reports\holding_return_20260105_20260421.md
```

Check recent pipeline batches:

```powershell
$env:PYTHONPATH='src'
python -m pipelines.tasks.summarize_pipeline_runs --write-db --limit 10
```

Use the report-layer entry point for human-readable summaries:

```powershell
$env:PYTHONPATH='src'
python -m report.tasks.summarize_holding_return --start-date 20260105 --end-date 20260421 --source tushare --write-db --output-path docs\reports\holding_return_20260105_20260421.md
```

`backtest.tasks.summarize_holding_return` is kept only as a compatibility wrapper.
