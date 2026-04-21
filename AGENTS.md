# AGENTS.md
> 本文件供 OpenAI Codex 及其他 AI 编程 Agent 自动读取，请勿删除。

---

## 项目定位

AI3 是 A 股全市场量化回测系统。

核心目标：

- 扫描沪深两市所有股票的周线 KDJ 金叉信号。
- 模拟信号出现后买入。
- 统计持仓 5 / 10 / 20 / 60 个交易日后的收益表现。
- 后续从 X/Twitter 等舆情数据构建热度特征，识别热门板块和热门股票。
- 后续允许接入更多数据源，例如 Tushare、akshare、X/Twitter、CSV、本地数据库、交易软件导出数据。

---

## 总体原则

### 1. 数据模块是底座

`data` 是底层数据模块，不属于某个策略。

任何策略、指标、回测、UI 都不能直接调用 Tushare、akshare、X/Twitter 等外部 API。它们只能读取 `data` 模块已经标准化后的数据。

### 2. 模块单向依赖

依赖方向必须保持单向：

```text
外部 API
  -> data.providers
  -> data.normalizers
  -> data.storage
  -> data.repositories / data.services
  -> features / strategy / backtest / ui
```

禁止反向依赖：

- `data` 不能 import `strategy`。
- `data` 不能 import `backtest`。
- `data.providers` 不能 import `data.storage`。
- `features` 不能调用外部 API。
- `strategy` 不能知道数据来自 Tushare、akshare 还是 X。

### 3. Provider 插件化

每一种外部数据源都是一个 provider 插件：

```text
TushareProvider
AkshareProvider
XProvider
CsvProvider
Mt5Provider
```

新增数据源时，只新增 provider 和对应 normalizer，不修改策略、不修改回测、不修改指标计算。

### 4. 数据契约优先

所有数据源必须先转换为项目内部统一数据契约，再进入存储层。

例如 A 股日线行情统一为：

```text
symbol, trade_date, open, high, low, close, pre_close, change, pct_chg, volume, amount, source
```

不同数据源字段差异只能在 `data.normalizers` 中处理。

---

## 推荐目录结构

所有 Python 代码和测试代码都从 `src/` 作为一级目录开始；根目录只保留项目入口文档、配置文件和工具配置。

```text
src/common/
  config.py                 # 环境变量、路径、通用配置
  logger.py                 # 统一日志
  timeutils.py              # 日期、交易日工具

src/data/
  contracts/
    market.py               # 行情数据契约
    instrument.py           # 股票/指数/标的信息契约
    sector.py               # 板块/行业/概念及成分契约
    social.py               # X/Twitter 等舆情数据契约
    enums.py                # 数据频率、市场、来源枚举

  providers/
    base.py                 # provider 抽象接口
    tushare_provider.py     # Tushare Pro 实现
    akshare_provider.py     # akshare 实现
    x_provider.py           # X/Twitter 实现，后期扩展
    csv_provider.py         # 本地 CSV 实现，测试和补数使用

  normalizers/
    market_normalizer.py    # 行情字段标准化
    instrument_normalizer.py
    social_normalizer.py

  storage/
    db.py                   # DB client 或连接池
    table_registry.py       # 物理表名、字段、分区规则
    sinks.py                # 批量写入、upsert、分区写入
    migrations/             # 建表 SQL 或迁移脚本

  repositories/
    market_repo.py          # 读取/写入标准行情
    instrument_repo.py      # 读取/写入股票列表
    sector_repo.py          # 读取/写入板块、行业、概念、成分关系
    social_repo.py          # 读取/写入外部舆情

  services/
    market_data_service.py  # 给策略/回测读取标准数据
    social_data_service.py  # 给 feature/strategy 读取标准舆情与热度特征
    trading_calendar.py     # 交易日历服务

  tasks/
    ingest_stock_list.py    # 更新股票列表
    ingest_market_daily.py  # 抓取日线行情
    ingest_market_weekly.py # 抓取或生成周线行情
    ingest_x_posts.py       # 后期 X 数据抓取任务
    build_weekly_bars.py    # 日线聚合周线
    validate_data.py        # 数据质量检查

src/features/
  indicators/
    kdj.py                  # KDJ 计算，只接收标准 DataFrame
    ema.py
  social/
    entity_linking.py       # 文本中股票、板块、主题实体识别
    heat_score.py           # 舆情热度分数计算
    ranking.py              # 热门板块、热门股票排序
  signals/
    kdj_cross.py            # 金叉信号识别
    hot_rank.py             # 热门板块/股票信号

src/backtest/
  holding_return.py         # 5/10/20/60 日收益统计
  engine.py

src/strategy/
  weekly_kdj_strategy.py    # 组合 data service + signal + backtest

docs/
  data_architecture.md      # 人工阅读的数据架构说明

src/tests/
```

---

## data 模块分层

### contracts

职责：

- 定义项目内部标准字段。
- 定义频率、市场、资产类型、数据源枚举。
- 不连接外部 API。
- 不访问数据库。

标准行情字段建议：

```text
symbol        # 统一标的代码，例如 000001.SZ
trade_date    # YYYYMMDD，int 或 str，但全项目必须统一
frequency     # 1d / 1w / 1m
open
high
low
close
pre_close
change
pct_chg
volume
amount
source        # tushare / akshare / x / csv
ingested_at
```

标准舆情帖子字段建议：

```text
post_id       # 外部帖子唯一 ID
author_id
created_at    # 标准时间，统一时区
text
lang
like_count
repost_count
reply_count
quote_count
view_count
source        # x / csv / other
raw_json
ingested_at
```

舆情实体识别结果建议：

```text
post_id
entity_type   # stock / sector / index / theme / keyword
entity_id     # symbol 或 sector_code
entity_name
match_text
match_method  # cashtag / alias / keyword / model
confidence
source
created_at
```

板块和成分关系建议：

```text
sector_code
sector_name
taxonomy      # industry / concept / theme / custom
symbol
weight
start_date
end_date
source
```

### providers

职责：

- 只负责调用外部数据源。
- 返回原始 DataFrame 或原始 dict。
- 不写数据库。
- 不计算指标。
- 不做策略判断。

Provider 接口约定：

```python
class MarketDataProvider:
    source_name: str

    def fetch_instruments(self) -> pd.DataFrame:
        ...

    def fetch_daily_bars(self, symbol: str | None, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_weekly_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...
```

X/Twitter 类 provider 不要塞进行情接口，单独定义：

```python
class SocialDataProvider:
    source_name: str

    def fetch_posts(self, query: str, start_time: str, end_time: str) -> pd.DataFrame:
        ...
```

X/Twitter provider 只抓原始帖子和公开互动指标，不做以下事情：

- 不判断股票是否热门。
- 不识别板块。
- 不把文本直接映射成交易信号。
- 不调用行情 repository。

### normalizers

职责：

- 把 provider 返回的原始字段映射为 contracts 标准字段。
- 统一日期、代码、数值类型。
- 去重、排序、空值处理。
- 保留 `source` 字段。

禁止：

- normalizer 不访问数据库。
- normalizer 不调用外部 API。
- normalizer 不计算 KDJ/EMA 等指标。

### storage

职责：

- 管理数据库连接。
- 管理表名、字段、分区规则。
- 提供 upsert、bulk insert、truncate partition 等底层写入能力。

要求：

- 写入前必须字段对齐。
- `np.nan` 必须转为 `None`。
- 默认使用幂等写入，例如 `INSERT ... ON DUPLICATE KEY UPDATE`。
- 清分区只能由 task 层明确调用，不能在单条写入函数里隐式发生。

### repositories

职责：

- 封装某类数据的读写。
- 对上提供稳定方法，不暴露 SQL 细节。
- repository 可以调用 `storage`，但不能调用 provider。

典型接口：

```python
class MarketRepository:
    def save_daily_bars(self, df: pd.DataFrame) -> int:
        ...

    def load_daily_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def save_weekly_bars(self, df: pd.DataFrame) -> int:
        ...

    def load_weekly_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...
```

### services

职责：

- 给策略、指标、回测提供稳定读取接口。
- 组合多个 repository。
- 处理交易日、上一有效周期、数据窗口等业务读逻辑。

要求：

- strategy/backtest/ui 只能通过 services 或 repositories 读取数据。
- services 不能调用 provider。

### X 热度与热门板块/股票链路

X/Twitter 热度是独立于行情的舆情特征链路，不能改写行情表，也不能让策略直接读 X provider。

推荐链路：

```text
data.tasks.ingest_x_posts
  -> raw_social_post
  -> features.tasks.build_social_mentions
  -> feature_social_entity_mention
  -> features.tasks.build_social_heat
  -> feature_social_heat_daily / feature_social_heat_weekly
  -> features.tasks.build_hot_rankings
  -> signal_hot_sector / signal_hot_stock
  -> strategy/backtest 按需读取
```

实体映射规则：

- 股票识别优先使用 `symbol`、股票简称、常用别名、英文名、cashtag。
- 板块识别必须依赖 `sector` 和 `sector_member` 标准表，不在策略中硬编码。
- 同一帖子命中多个实体时保留多行 mention，并记录 `confidence`。
- 模糊简称、歧义词、低置信度命中不能直接生成强信号。
- 热门板块优先由成分股热度聚合得到，也允许叠加直接提到板块名称的帖子。

热度分数至少保留可解释字段：

```text
entity_type
entity_id
trade_date
window        # 1d / 3d / 5d / 1w
mention_count
unique_author_count
engagement_score
momentum_score
heat_score
rank
score_version
```

热度计算属于 `features`，热门排序属于 `signals` 或 `features.signals`，回测只读取已落库的特征或信号。

---

## tasks 任务拆分

任务层只做编排，不写复杂业务逻辑。

每个 task 的结构统一为：

```text
解析参数 -> 选择 provider -> 抓取原始数据 -> normalizer 标准化 -> repository/storage 写入 -> validate -> 输出日志
```

### 数据接入任务

```text
data.tasks.ingest_stock_list
```

职责：

- 从 Tushare 或 akshare 获取股票列表。
- 标准化为 instrument contract。
- 写入 instrument 表。

```text
data.tasks.ingest_market_daily
```

职责：

- 抓取 A 股日线 RAW。
- 支持全市场按日期抓取。
- 支持指定股票列表补数。
- 支持 `range/date/increment`。

```text
data.tasks.ingest_market_weekly
```

职责：

- 优先直接抓取外部周线。
- 如果外部周线不可用，则从日线聚合。
- 周线 `trade_date` 必须统一为周一。

```text
data.tasks.ingest_x_posts
```

职责：

- 后期接入 X/Twitter。
- 只写入 social/raw 层。
- 不直接影响行情、指标、策略。

### 数据构建任务

```text
data.tasks.build_weekly_bars
```

职责：

- 从标准日线行情聚合周线。
- 不调用外部 API。
- 不计算策略信号。

```text
features.tasks.build_kdj
```

职责：

- 从 `data.services.market_data_service` 读取标准行情。
- 计算 KDJ。
- 写入 feature/indicator 表。

```text
features.tasks.build_social_mentions
```

职责：

- 从 `data.repositories.social_repo` 读取标准帖子。
- 从 `instrument_repo` / `sector_repo` 读取股票、别名、板块、成分关系。
- 识别帖子中提到的股票、板块、主题或关键词。
- 写入 `feature_social_entity_mention`。
- 不调用 X/Twitter API。

```text
features.tasks.build_social_heat
```

职责：

- 读取 `feature_social_entity_mention` 和标准帖子互动指标。
- 按股票、板块、主题、日期窗口聚合热度。
- 写入 `feature_social_heat_daily` 或 `feature_social_heat_weekly`。
- 保留分数版本，保证历史回测可复现。

```text
features.tasks.build_hot_rankings
```

职责：

- 读取热度特征。
- 生成热门板块、热门股票排序。
- 写入 `signal_hot_sector` / `signal_hot_stock`。
- 不抓取外部数据，不直接下交易结论。

```text
features.tasks.build_weekly_kdj_cross
```

职责：

- 读取周线 KDJ。
- 找出 KDJ 金叉。
- 写入 signal 表或返回 DataFrame。

```text
backtest.tasks.run_holding_return
```

职责：

- 读取信号。
- 读取后续交易日行情。
- 计算 5 / 10 / 20 / 60 个交易日收益。
- 输出结果表和报告。

### 任务依赖顺序

全量重算：

```text
1. data.tasks.ingest_stock_list
2. data.tasks.ingest_market_daily
3. data.tasks.build_weekly_bars 或 data.tasks.ingest_market_weekly
4. features.tasks.build_weekly_kdj
5. features.tasks.build_weekly_kdj_cross
6. backtest.tasks.run_holding_return
```

增量更新：

```text
1. data.tasks.ingest_market_daily --mode increment
2. data.tasks.build_weekly_bars --mode increment
3. features.tasks.build_weekly_kdj --mode increment
4. features.tasks.build_weekly_kdj_cross --mode increment
5. backtest.tasks.run_holding_return --mode increment
```

X/Twitter 数据接入：

```text
1. data.tasks.ingest_x_posts
2. data.tasks.validate_data --domain social
3. features.tasks.build_social_mentions
4. features.tasks.build_social_heat
5. features.tasks.build_hot_rankings
6. 后续如果策略需要，再由 strategy/backtest 读取热度特征或热门信号
```

---

## mode 约定

所有批处理任务尽量支持统一 mode：

```text
range      # 指定 start_date/end_date
date       # 指定单日或单周期
increment  # 从已入库最大日期之后继续
all        # 全量
sample     # 小样本调试
```

任务参数统一命名：

```text
provider
symbols
start_date
end_date
mode
overwrite
sleep
limit
```

---

## 数据源扩展规则

新增一个数据源时，只允许新增这些内容：

```text
src/data/providers/new_provider.py
src/data/normalizers/new_normalizer.py
src/data/tasks/ingest_new_data.py
src/tests/data/providers/test_new_provider.py
```

如果因为新增数据源需要修改策略或回测，说明架构边界错误，应先调整 contracts 或 service。

---

## 配置与密钥

- `TUSHARE_TOKEN` 必须从环境变量读取。
- X/Twitter API key 必须从环境变量读取。
- 数据库密码必须从环境变量或本地 `.env` 读取。
- 禁止硬编码任何 token、cookie、账号、密码。
- `.env` 不得提交。

推荐环境变量：

```text
TUSHARE_TOKEN
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DATABASE
X_API_KEY
```

---

## 指标与策略边界

指标层：

- 只接收标准行情 DataFrame。
- 不知道数据来源。
- 不访问外部 API。
- 不负责回测。

策略层：

- 组合信号。
- 不抓数据。
- 不写 RAW 表。

回测层：

- 读取信号和行情。
- 计算收益。
- 不计算原始指标。
- 不调用 provider。

---

## 测试要求

- provider 测试：只验证外部源适配，真实 API 测试标记为 integration。
- normalizer 测试：固定输入，验证标准字段、日期、排序、去重。
- repository 测试：优先使用临时库或 mock，避免污染真实数据库。
- service 测试：验证上一有效交易日、上一有效周、窗口读取。
- feature 测试：固定行情输入，验证 KDJ 和金叉输出。
- backtest 测试：固定信号和行情，验证 5/10/20/60 日收益。

---

## 编程约束

- 不要把所有数据逻辑塞进一个 `data.py` 或一个 `data` 模块。
- 不要跨层调用。
- 不要让 provider 写数据库。
- 不要让 strategy 调 provider。
- 不要让 transform 读数据库。
- 不要让 sink 清分区，除非函数名明确是 `truncate_*` 且由 task 调用。
- 所有任务必须有日志。
- 所有全市场循环必须允许单标的失败后继续。
- 所有日期进入存储前必须统一格式。
