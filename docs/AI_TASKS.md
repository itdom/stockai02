# AI3 执行计划 TASKS

> 读者：AI Agent。人类入口请先看 `README.md` 和 `docs/README.md`。

> 目标：先完成 A 股原始基础数据的标准化存储，再完成 X/Twitter 数据获取链路，最后用多类验证规则确认基础数据准确性和可复现性。

## 0. 执行原则

- 所有外部数据只允许从 `data.providers` 进入系统。
- 所有原始数据必须先通过 `data.normalizers` 转换为 AI3 标准 contract，再写入 storage/repository。
- `features`、`strategy`、`backtest` 不直接调用 Tushare、akshare、X/Twitter API。
- 任务层只做编排：解析参数、选择 provider、抓取、标准化、写入、验证、输出日志。
- 密钥只从环境变量读取：`TUSHARE_TOKEN`、`X_API_KEY`、`MYSQL_*`。

## 1. 参考范围

参考仓库：https://github.com/itdom/stockai01.git

可借鉴内容：

- `TUSHARE_TOKEN` 环境变量模式。
- 先获取股票列表、交易日历，再按交易日抓取全市场日线数据的流程。
- 日线数据字段映射思路：`ts_code`、`trade_date`、`open`、`high`、`low`、`close`、`pct_chg`、`vol`、`amount`。
- 运行产物思路：数据库落库、运行摘要、输出日志、可重复运行。
- 样本数据 provider 思路，可用于本地测试和 CI。

不能直接照搬内容：

- stockai01 的数据、清洗、排名、存储比较集中，AI3 必须拆成 provider、normalizer、storage、repository、service。
- stockai01 使用 SQLite 动态建表，AI3 存储层需要按 contract 和表注册显式控制表结构、主键、唯一键和 upsert。
- stockai01 未形成独立 X/Twitter 数据链路，AI3 需要新增 `SocialDataProvider`、`social_normalizer`、`social_repo` 和验证规则。

X/Twitter 获取方案参考：

- 首选实现为 `TwitterApiIoProvider`，外层文件仍命名为 `src/data/providers/x_provider.py`。
- API key 使用 `X_API_KEY`，请求头使用 `x-api-key`。
- 搜索接口使用 `GET /twitter/tweet/advanced_search`。
- 查询时间过滤使用 `since_time:<unix_ts>` 和 `until_time:<unix_ts>`，不要使用已退化的 `since:YYYY-MM-DD` / `until:YYYY-MM-DD`。
- 分页使用 `cursor`，单页最多约 20 条结果。
- 免费限速按 1 request / 5 seconds 设计；付费账号按配置的 QPS 限制节流。

## 2. 里程碑

### M1. 项目基础骨架

状态：已完成基础骨架

交付文件：

- `src/common/config.py`
- `src/common/logger.py`
- `src/common/timeutils.py`
- `src/data/contracts/enums.py`
- `src/data/contracts/market.py`
- `src/data/contracts/instrument.py`
- `src/data/contracts/social.py`
- `src/data/providers/base.py`
- `src/data/storage/db.py`
- `src/data/storage/table_registry.py`
- `src/data/storage/sinks.py`

任务：

- 定义统一配置读取方式，集中读取环境变量，不硬编码 token、密码、cookie。
- 定义统一 logger，所有 task 必须输出开始、参数、抓取数量、标准化数量、写入数量、失败数量。
- 定义日期工具：`YYYYMMDD`、ISO datetime、Unix timestamp、周一归一、交易日区间。
- 定义基础枚举：`DataSource`、`Frequency`、`Market`、`AssetType`、`EntityType`。
- 定义行情、股票、舆情帖子 contract 字段和字段顺序。
- 定义 provider 抽象接口：`MarketDataProvider`、`SocialDataProvider`。
- 定义表注册：物理表名、主键、唯一键、字段列表、日期分区或逻辑分区规则。

验收标准：

- `python -m pytest src/tests/contracts src/tests/common` 可运行。
- 任何配置缺失都给出明确错误信息，不输出密钥值。
- contract 字段在测试中固定，后续新增字段必须显式改测试。

### M2. 原始股票列表存储

状态：进行中，已完成 CSV provider、Tushare/Akshare provider 适配器、instrument normalizer、instrument repository、MySQL writer 骨架和 CSV ingest task

交付文件：

- `src/data/providers/tushare_provider.py`
- `src/data/providers/akshare_provider.py`
- `src/data/providers/csv_provider.py`
- `src/data/normalizers/instrument_normalizer.py`
- `src/data/repositories/instrument_repo.py`
- `src/data/tasks/ingest_stock_list.py`
- `src/tests/data/normalizers/test_instrument_normalizer.py`
- `src/tests/data/tasks/test_ingest_stock_list.py`

标准表：

- `instrument`
- 可选：`instrument_alias`

标准字段：

```text
symbol, name, market, exchange, asset_type, list_status, list_date,
delist_date, industry, source, ingested_at
```

任务：

- Tushare provider 实现 `fetch_instruments()`，调用 `stock_basic` 获取 A 股列表。
- akshare provider 实现股票列表备用接口。
- csv provider 支持从本地 CSV 导入股票列表，便于测试和补数。
- normalizer 统一代码格式为 `000001.SZ`、`600000.SH`。
- repository 实现幂等写入，唯一键建议为 `symbol`。
- task 支持参数：`provider`、`mode`、`overwrite`、`limit`。

验收标准：

- 股票代码格式全部符合 `^\d{6}\.(SZ|SH|BJ)$`。
- `symbol` 不为空、不重复。
- `list_date` 统一为 `YYYYMMDD` 或空值。
- 单个 provider 失败时 task 输出错误日志并返回非零退出码。

### M3. 原始日线行情存储

状态：进行中，已完成 market normalizer、market repository 和 CSV daily ingest task

交付文件：

- `src/data/normalizers/market_normalizer.py`
- `src/data/repositories/market_repo.py`
- `src/data/tasks/ingest_market_daily.py`
- `src/tests/data/normalizers/test_market_normalizer.py`
- `src/tests/data/tasks/test_ingest_market_daily.py`

标准表：

- `market_bar_daily`

标准字段：

```text
symbol, trade_date, frequency, open, high, low, close, pre_close,
change, pct_chg, volume, amount, source, ingested_at
```

任务：

- Tushare provider 实现按 `trade_date` 拉取全市场日线，优先减少 API 调用次数。
- Tushare provider 实现按 `symbol + start_date + end_date` 补数。
- akshare provider 作为备用数据源。
- normalizer 负责字段映射：`ts_code -> symbol`、`vol -> volume`，日期统一为 `YYYYMMDD`。
- storage/sink 写入前必须字段对齐，`NaN` 转 `None`。
- repository 实现 `save_daily_bars()`、`load_daily_bars()`、`get_max_trade_date()`。
- task 支持：`range`、`date`、`increment`、`all`、`sample`。
- 全市场循环中，单日无数据跳过，单标的失败记录失败清单并继续。

验收标准：

- 唯一键建议为 `(symbol, trade_date, frequency, source)`。
- 重复执行同一日期不产生重复行。
- `high >= max(open, close)`，`low <= min(open, close)`。
- `volume`、`amount` 非负。
- `pct_chg` 与 `pre_close`、`close` 的偏差在容忍范围内。

### M4. 原始周线行情存储

状态：已完成基础实现（外部周线接入 + 标准日线聚合周线）

交付文件：

- `src/data/tasks/ingest_market_weekly.py`
- `src/data/tasks/build_weekly_bars.py`
- `src/tests/data/tasks/test_ingest_market_weekly.py`
- `src/tests/data/tasks/test_build_weekly_bars.py`

标准表：

- `market_bar_weekly`

任务：

- 优先支持从 Tushare 直接抓取周线。
- 必须支持从标准日线行情聚合周线，作为主验证和补数路径。
- 周线 `trade_date` 统一归一到该周周一。
- 聚合规则：
  - `open` = 本周第一根日线 open。
  - `high` = 本周最高 high。
  - `low` = 本周最低 low。
  - `close` = 本周最后一根日线 close。
  - `volume` = 本周成交量合计。
  - `amount` = 本周成交额合计。
  - `pre_close` = 上一周 close。

验收标准：

- 所有周线 `trade_date` 都是周一。
- 同一 `symbol + trade_date + frequency + source` 不重复。
- 从日线聚合的周线和外部周线可做差异报告。
- 最近未完结周要有明确策略：默认只构建已完结周，除非参数 `include_incomplete_week=true`。

### M5. X/Twitter 原始帖子获取和存储

状态：已完成基础实现（`raw_social_query_run` 断点记录待后续扩展）

交付文件：

- `src/data/providers/x_provider.py`
- `src/data/normalizers/social_normalizer.py`
- `src/data/repositories/social_repo.py`
- `src/data/tasks/ingest_x_posts.py`
- `src/tests/data/providers/test_x_provider.py`
- `src/tests/data/normalizers/test_social_normalizer.py`
- `src/tests/data/tasks/test_ingest_x_posts.py`

标准表：

- `raw_social_post`
- 可选：`raw_social_query_run`

标准字段：

```text
post_id, author_id, author_username, created_at, text, lang,
like_count, repost_count, reply_count, quote_count, view_count,
query, query_type, source, raw_json, ingested_at
```

任务：

- `XProvider` 只负责抓取原始帖子和公开互动指标，不识别股票、不判断热度、不生成信号。
- 支持查询参数：`query`、`start_time`、`end_time`、`query_type`、`cursor`、`limit`、`sleep`。
- 时间入参统一转换为 Unix timestamp，并拼入 `since_time` / `until_time`。
- 支持分页 cursor，写入 query run 记录，便于断点续抓。
- 支持限速配置：免费默认 `sleep=5` 秒，付费账号按 `X_QPS_LIMIT` 控制。
- normalizer 统一时间为 UTC ISO 或项目约定时区，保留 `raw_json`。
- repository 幂等写入，唯一键建议为 `(post_id, source)`。

验收标准：

- 缺失 `X_API_KEY` 时 provider 给出明确错误，不发起请求。
- 同一 query 重复抓取不产生重复帖子。
- 每条帖子保留完整原始 JSON。
- `created_at` 必须落在任务的 `[start_time, end_time)` 范围内，允许配置边界容忍。
- X 数据只进入 social/raw 表，不写行情表，不触发策略。

### M6. 基础数据验证任务

状态：进行中（已完成 instrument / market_daily / market_weekly / social 基础规则）

交付文件：

- `src/data/tasks/validate_data.py`
- `src/data/services/trading_calendar.py`
- `src/tests/data/tasks/test_validate_data.py`
- `docs/data_validation_rules.md`

验证域：

- `instrument`
- `market_daily`
- `market_weekly`
- `social`
- `cross_source`
- `pipeline`

任务：

- 实现统一验证入口：`python -m data.tasks.validate_data --domain market_daily --start_date 20240101 --end_date 20240401`。
- 每条规则输出：规则 ID、严重级别、检查范围、通过数量、失败数量、样例失败行、建议处理方式。
- 验证结果写入 `data_validation_result`，同时输出 JSON/CSV 报告。
- 严重级别分为：`error`、`warning`、`info`。
- CI 中默认运行 sample 数据验证；真实 API 验证标记为 integration。

验收标准：

- error 规则失败时任务返回非零退出码。
- warning 规则失败时任务返回零退出码但报告必须展示。
- 验证报告可按运行批次追溯。

## 3. 数据验证规则清单

### 3.1 股票列表规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| INS-001 | error | `symbol` 非空且唯一 |
| INS-002 | error | `symbol` 符合 `000001.SZ`、`600000.SH`、`430000.BJ` 格式 |
| INS-003 | warning | `name` 非空 |
| INS-004 | warning | `list_date` 不晚于当前日期 |
| INS-005 | warning | `delist_date` 不早于 `list_date` |
| INS-006 | info | 按交易所统计股票数量，与上一次运行差异超过阈值则提示 |

### 3.2 日线行情规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| DLY-001 | error | `(symbol, trade_date, frequency, source)` 唯一 |
| DLY-002 | error | `trade_date` 符合 `YYYYMMDD` |
| DLY-003 | error | `open/high/low/close` 全部大于 0 |
| DLY-004 | error | `high >= open`、`high >= close`、`low <= open`、`low <= close` |
| DLY-005 | error | `volume >= 0`、`amount >= 0` |
| DLY-006 | warning | `pct_chg` 与 `(close - pre_close) / pre_close * 100` 的差异不超过容忍阈值 |
| DLY-007 | warning | 同一交易日全市场行数低于最近 20 个交易日均值的 80% 时报警 |
| DLY-008 | warning | 单只股票交易日断档超过阈值时报警 |
| DLY-009 | info | 涨跌幅超过 20% 的记录输出样例，供人工检查科创板、创业板、北交所规则 |

### 3.3 周线行情规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| WKY-001 | error | 周线 `trade_date` 必须是周一 |
| WKY-002 | error | `(symbol, trade_date, frequency, source)` 唯一 |
| WKY-003 | error | OHLC 关系合法 |
| WKY-004 | warning | 周线 volume、amount 与日线聚合结果差异超过容忍阈值 |
| WKY-005 | warning | 周线 close 与该周最后一个日线 close 不一致 |
| WKY-006 | warning | 当前周未完结数据必须带有明确标记或默认不入库 |

### 3.4 X/Twitter 原始帖子规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| SOC-001 | error | `(post_id, source)` 唯一 |
| SOC-002 | error | `created_at` 非空且可解析 |
| SOC-003 | error | `text` 非空 |
| SOC-004 | warning | `created_at` 必须落在查询窗口内 |
| SOC-005 | warning | `like_count/repost_count/reply_count/quote_count/view_count` 不为负 |
| SOC-006 | warning | `lang` 缺失比例超过阈值报警 |
| SOC-007 | warning | 同一 query 返回量突然低于历史均值的 50% 时报警 |
| SOC-008 | info | 输出每个 query 的抓取页数、帖子数、去重数和耗时 |

### 3.5 跨源一致性规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| XSR-001 | warning | Tushare 与 akshare 同一股票同日 close 差异超过阈值 |
| XSR-002 | warning | Tushare 与 akshare 同一交易日全市场股票数差异超过阈值 |
| XSR-003 | info | 周线外部源与日线聚合源差异报告 |
| XSR-004 | info | X query 命中的股票简称必须能在 `instrument` 或 `instrument_alias` 中找到 |

### 3.6 流水线规则

| 规则 ID | 级别 | 规则 |
| --- | --- | --- |
| RUN-001 | error | 每个 task 必须写入运行批次号和运行时间 |
| RUN-002 | error | task 失败必须有错误日志和失败范围 |
| RUN-003 | warning | 全市场任务失败股票数超过阈值报警 |
| RUN-004 | warning | 增量任务起始日期必须大于已入库最大日期 |
| RUN-005 | info | 每次运行输出抓取数量、标准化数量、写入数量、去重数量 |

## 4. 推荐执行顺序

1. 建立基础骨架和 contract。
2. 完成股票列表 provider、normalizer、repository、task。
3. 完成日线行情 provider、normalizer、repository、task。
4. 完成周线外部抓取和日线聚合周线。
5. 完成 X/Twitter provider、social normalizer、social repo、ingest task。
6. 完成基础验证规则和报告。
7. 使用 sample/csv provider 跑通本地闭环。
8. 使用真实 Tushare 小范围验证：1 个交易日、10 只股票。
9. 使用真实 X query 小范围验证：1 个 query、1 小时时间窗、最多 100 条。
10. 扩大到全市场日线和多个 X query，生成完整验证报告。

## 5. MVP 验收清单

- `instrument` 表有 A 股股票列表，代码、名称、上市日期可验证。
- `market_bar_daily` 表有至少一个交易日全市场日线行情。
- `market_bar_weekly` 表可由日线聚合生成，且周一归一正确。
- `raw_social_post` 表可保存 X/Twitter 原始帖子，重复运行可去重。
- `validate_data` 可对股票、日线、周线、X 原始帖子输出验证报告。
- 所有真实 API key 均来自环境变量，仓库内没有密钥。
- provider 不写库，normalizer 不读库，strategy/backtest 不调用外部 API。

## 6. 后续扩展

- 当前已完成 `data.tasks.ingest_market_weekly`，支持 CSV / Tushare / Akshare 周线接入。
- 当前已完成日线 / 周线行情 ingest task 的 `range`、`date`、`increment`、`all`、`sample` 基础 mode 解析。
- 当前已完成 `data.services.market_data_service`、`data.services.social_data_service` 和 `data.services.trading_calendar` 基础读取服务。
- 当前已完成 `data.tasks.validate_data` 的 instrument / market_daily / market_weekly / social 基础规则。
- 当前已完成 `XProvider`、`social_normalizer`、`social_repo` 和 `data.tasks.ingest_x_posts` 的 X 原始帖子接入骨架。
- 后续补齐 `validate_data` 的 social / cross_source / pipeline 规则。
- 当前已完成 `features.indicators.kdj`、`features.tasks.build_weekly_kdj`、`features.tasks.build_weekly_kdj_cross`、`features.signals.kdj_cross` 和 `backtest.tasks.run_holding_return` 的基础实现。
- 当前已完成 MySQL 核心表 migration：`src/data/storage/migrations/001_create_core_tables.sql`。
- 当前已完成 CSV 端到端验收 pipeline：`strategy.tasks.run_weekly_kdj_backtest_pipeline`。
- 在 X 原始帖子稳定后，再实现 `features.tasks.build_social_mentions`、`build_social_heat`、`build_hot_rankings`。
- 在信号表稳定后，再实现 `backtest.tasks.run_holding_return` 统计 5 / 10 / 20 / 60 个交易日收益。
