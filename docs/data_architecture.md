# AI3 数据底座架构说明

> 读者：人类开发者。本文件解释项目架构和模块边界；AI 执行规则见仓库根目录 `AGENTS.md`，执行计划见 `docs/AI_TASKS.md`。

## 1. 为什么不能只有一个 data 模块

如果所有逻辑都放在一个 `data` 模块里，后期一定会出现这些问题：

- Tushare、akshare、X/Twitter、CSV、本地数据库的代码互相掺在一起。
- 策略代码直接调用外部 API，导致回测结果不可复现。
- 换数据源时要改策略、指标、回测。
- 数据字段不统一，后面每个模块都要处理一遍字段差异。
- 全市场任务失败时，很难知道是抓取失败、标准化失败、写库失败，还是指标计算失败。

所以 `data` 必须拆成底层数据架构，而不是一个文件或一个大模块。

核心思想：

```text
数据来源可以变，但内部数据契约不能乱。
策略可以增加，但不能反向影响数据底座。
```

## 2. 总体分层

推荐架构：

```text
外部数据源
  -> providers       # 只负责抓
  -> normalizers     # 只负责转成统一字段
  -> storage         # 只负责底层存储能力
  -> repositories    # 只负责某类数据的读写接口
  -> services        # 给策略/回测使用的数据服务
  -> features        # 指标、信号
  -> backtest        # 回测统计
```

依赖方向只能从上往下走，不能反向。

正确：

```text
strategy -> data.services -> data.repositories -> data.storage
```

错误：

```text
data.providers -> strategy
features.kdj -> tushare_provider
backtest -> akshare_provider
```

## 3. 目录拆分

建议目录：

```text
src/common/
  config.py
  logger.py
  timeutils.py

src/data/
  contracts/
  providers/
  normalizers/
  storage/
  repositories/
  services/
  tasks/

src/features/
  indicators/
  social/
  signals/
  tasks/

src/backtest/
  tasks/

src/strategy/

docs/
src/tests/
```

### common

放通用基础设施：

- 环境变量读取。
- 日志。
- 日期工具。
- 不放业务策略。
- 不放外部数据源实现。

### src/data/contracts

定义内部标准数据格式。

行情数据不管来自 Tushare、akshare 还是 CSV，进入系统后都应该长这样：

```text
symbol
trade_date
frequency
open
high
low
close
pre_close
change
pct_chg
volume
amount
source
ingested_at
```

X/Twitter 这类社交数据也要有独立 contract：

```text
post_id
author_id
created_at
text
lang
like_count
repost_count
reply_count
quote_count
view_count
source
raw_json
ingested_at
```

行情 contract 和社交 contract 不要混在一起。

识别帖子中提到的实体时，不要把结果塞回帖子表，应该单独保存 mention contract：

```text
post_id
entity_type     # stock / sector / index / theme / keyword
entity_id       # symbol、sector_code 或自定义主题 ID
entity_name
match_text
match_method    # cashtag / alias / keyword / model
confidence
source
created_at
```

板块、行业、概念也要作为标准数据管理：

```text
sector_code
sector_name
taxonomy        # industry / concept / theme / custom
symbol
weight
start_date
end_date
source
```

股票别名和板块成分是 X 热度映射的基础数据，不应该写死在策略里。

### src/data/providers

provider 只负责从外部拿原始数据。

示例：

```text
src/data/providers/tushare_provider.py
src/data/providers/akshare_provider.py
src/data/providers/x_provider.py
src/data/providers/csv_provider.py
```

provider 规则：

- 可以调用外部 API。
- 可以处理重试。
- 可以处理 API 限速。
- 不写数据库。
- 不计算指标。
- 不知道策略存在。

X provider 只抓帖子、作者、时间、文本和公开互动指标。它不能判断股票热门，不能识别板块，不能把文本映射为交易信号。

### src/data/normalizers

normalizer 负责把不同来源的数据转成内部 contract。

例子：

```text
Tushare 的 vol -> volume
akshare 的 成交量 -> volume
X 的 created_at -> created_at 标准时间
X 的 public_metrics -> like_count / repost_count / reply_count / quote_count / view_count
```

normalizer 规则：

- 不调用外部 API。
- 不写数据库。
- 不做策略计算。
- 只做字段映射、类型转换、日期标准化、排序、去重、空值处理。

### src/data/storage

storage 是最底层存储能力。

包括：

- 数据库连接。
- 表注册表。
- 批量插入。
- upsert。
- 分区清理。
- 建表迁移。

storage 不应该知道“周线 KDJ 策略”是什么。

### src/data/repositories

repository 是某一类数据的读写接口。

例如：

```python
class MarketRepository:
    def save_daily_bars(self, df): ...
    def load_daily_bars(self, symbol, start_date, end_date): ...
    def save_weekly_bars(self, df): ...
    def load_weekly_bars(self, symbol, start_date, end_date): ...
```

repository 规则：

- 可以调用 storage。
- 不调用 provider。
- 不计算指标。
- 对上隐藏 SQL 和表结构。

X 热度相关 repository 建议：

```python
class SocialRepository:
    def save_posts(self, df): ...
    def load_posts(self, start_time, end_time, query=None): ...

class SectorRepository:
    def save_sectors(self, df): ...
    def save_sector_members(self, df): ...
    def load_sector_members(self, taxonomy=None): ...
    def load_symbol_aliases(self): ...
```

`SocialRepository` 只管理标准舆情数据，`SectorRepository` 只管理板块和成分关系。二者都不调用 X、Tushare 或 akshare。

### src/data/services

service 是给策略和回测使用的数据入口。

例子：

```python
market_data_service.load_weekly_bars(symbol, start_date, end_date)
market_data_service.load_forward_daily_closes(symbol, signal_date, horizons=[5, 10, 20, 60])
trading_calendar.get_next_trade_date(date)
social_data_service.load_hot_stocks(trade_date, window="1d", top_n=50)
social_data_service.load_hot_sectors(trade_date, window="1d", top_n=20)
```

service 规则：

- 可以组合多个 repository。
- 可以处理上一有效交易日、下一交易日、窗口读取。
- 不调用 provider。
- 不做外部抓取。

`social_data_service` 只能读取已经落库的帖子、mention、热度特征或热门信号。它不能直接调用 X provider。

### src/data/tasks

tasks 是数据任务编排层。

task 的标准流程：

```text
解析参数
  -> 选择 provider
  -> provider 抓原始数据
  -> normalizer 标准化
  -> repository 写入
  -> validate 检查
  -> 输出日志
```

task 可以调 provider，因为 task 是边界入口。

但是 strategy、features、backtest 不可以调 provider。

## 4. tasks 怎么分

### 4.1 股票列表任务

任务名：

```text
data.tasks.ingest_stock_list
```

职责：

- 从 Tushare 或 akshare 获取股票列表。
- 标准化字段。
- 写入 instrument 表。

输出：

```text
raw_instrument
```

### 4.2 日线行情任务

任务名：

```text
data.tasks.ingest_market_daily
```

职责：

- 抓取 A 股日线行情。
- 支持全市场按日期抓取。
- 支持指定股票补数。
- 写入标准日线 RAW 表。

输入参数：

```text
provider=tushare
mode=range/date/increment/all
start_date
end_date
symbols
overwrite
```

输出：

```text
raw_market_daily
```

### 4.3 周线行情任务

任务名：

```text
data.tasks.ingest_market_weekly
```

职责：

- 直接抓外部周线，或者从日线聚合周线。
- 周线日期统一归到周一。
- 写入标准周线 RAW 表。

输出：

```text
raw_market_weekly
```

### 4.4 日线转周线任务

任务名：

```text
data.tasks.build_weekly_bars
```

职责：

- 读取标准日线。
- 聚合为周线。
- 不调用外部 API。
- 不计算指标。

### 4.5 X/Twitter 数据任务

任务名：

```text
data.tasks.ingest_x_posts
```

职责：

- 从 X/Twitter 获取帖子、作者、时间、文本、公开互动指标。
- 写入 social raw 表。
- 不影响行情表。
- 不影响 KDJ 策略。

输入参数：

```text
provider=x
mode=range/date/increment/sample
query
start_time
end_time
lang
limit
sleep
```

输出：

```text
raw_social_post
```

不要在这个任务里做热门股票、热门板块判断。

### 4.6 舆情实体识别任务

任务名：

```text
features.tasks.build_social_mentions
```

职责：

- 从 `social_repo` 读取标准帖子。
- 从 `instrument_repo` 和 `sector_repo` 读取股票、别名、板块、成分关系。
- 把文本中的股票、板块、指数、主题、关键词识别为标准实体。
- 写入 `feature_social_entity_mention`。
- 不调用 X/Twitter API。

实体识别建议分层：

```text
1. 精确代码：000001.SZ、600519.SH
2. cashtag 或标签：$KWEICHOWMOUTAI、#AI
3. 股票简称和别名：贵州茅台、茅台
4. 板块和概念词：半导体、机器人、低空经济
5. 可选模型识别：只输出候选和置信度，不直接生成交易信号
```

歧义处理：

- 一个简称可能对应多只股票时，必须降低置信度或结合上下文。
- 常见泛词不能直接映射为板块强信号。
- 同一帖子可以命中多个实体，但必须一行一个 mention。
- 所有 mention 必须保留 `match_method` 和 `confidence`。

### 4.7 舆情热度计算任务

任务名：

```text
features.tasks.build_social_heat
```

职责：

- 读取 `feature_social_entity_mention`。
- 读取标准帖子互动指标。
- 按股票、板块、主题和日期窗口聚合热度。
- 写入 `feature_social_heat_daily` / `feature_social_heat_weekly`。
- 保留 `score_version`，保证回测可复现。

热度表建议字段：

```text
entity_type
entity_id
entity_name
trade_date
window          # 1d / 3d / 5d / 1w
mention_count
unique_author_count
engagement_score
momentum_score
heat_score
rank
score_version
created_at
```

热度分数建议由可解释因子组成：

```text
heat_score =
  log1p(mention_count)
  + author_weight * log1p(unique_author_count)
  + engagement_weight * log1p(like + repost + reply + quote + view_adjusted)
  + momentum_weight * recent_growth
```

具体权重可以后续回测调参，但每次调整必须更新 `score_version`。

板块热度建议两路合成：

```text
板块直接提及热度
  + 成分股热度按权重聚合
  -> 板块总热度
```

### 4.8 热门板块和热门股票排序任务

任务名：

```text
features.tasks.build_hot_rankings
```

职责：

- 读取 `feature_social_heat_daily` 或 `feature_social_heat_weekly`。
- 生成热门股票榜、热门板块榜。
- 写入 `signal_hot_stock` / `signal_hot_sector`。
- 不抓取外部数据。
- 不直接计算买卖收益。

输出字段建议：

```text
trade_date
entity_type
entity_id
entity_name
rank
heat_score
rank_change
window
score_version
signal_source
```

热门排序可以给策略使用，但策略仍然只组合信号，不直接读 X 原始帖子。

### 4.9 KDJ 指标任务

任务名：

```text
features.tasks.build_weekly_kdj
```

职责：

- 从 `data.services.market_data_service` 读取周线行情。
- 计算 KDJ。
- 写入指标表。

禁止：

- 禁止调用 Tushare。
- 禁止调用 akshare。
- 禁止调用 X。

### 4.10 KDJ 金叉信号任务

任务名：

```text
features.tasks.build_weekly_kdj_cross
```

职责：

- 读取周线 KDJ。
- 比较当前周和上一有效周。
- 输出金叉信号。

金叉判断：

```text
上一有效周 K < D
当前周 K >= D
```

不要用自然日假设上一周，必须使用已有交易周期。

### 4.11 持仓收益回测任务

任务名：

```text
backtest.tasks.run_holding_return
```

职责：

- 读取金叉信号。
- 读取信号日之后第 5 / 10 / 20 / 60 个交易日的收盘价。
- 计算收益率。
- 统计胜率、平均收益、中位数、分位数、最大亏损等。

## 5. 任务依赖关系

全量重算：

```text
1. data.tasks.ingest_stock_list
2. data.tasks.ingest_market_daily
3. data.tasks.build_weekly_bars
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

接入 X/Twitter：

```text
1. data.tasks.ingest_x_posts
2. data.tasks.validate_data --domain social
3. features.tasks.build_social_mentions
4. features.tasks.build_social_heat
5. features.tasks.build_hot_rankings
6. strategy/backtest 按需读取热度特征或热门信号
```

这条链路和行情链路是并行的，不应该影响行情任务。

组合行情和 X 热度做回测时，推荐任务顺序：

```text
1. 行情链路生成 KDJ 金叉信号
2. X 链路生成热门板块/热门股票信号
3. strategy 组合条件，例如：周线 KDJ 金叉 AND 所属板块热度排名前 N
4. backtest.tasks.run_holding_return 读取组合后的信号做收益统计
```

不要在 `build_social_heat` 中读取未来行情，也不要在回测中重新抓 X 数据。

## 6. mode 统一约定

所有批处理任务尽量统一支持：

```text
range
date
increment
all
sample
```

参数尽量统一：

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

## 7. 新增数据源的标准步骤

以后要从 X 获取数据，不应该改行情任务，也不应该改策略核心。

标准步骤：

```text
1. 新增 src/data/providers/x_provider.py
2. 新增 src/data/contracts/social.py 或扩展 social contract
3. 新增 src/data/normalizers/social_normalizer.py
4. 新增 src/data/repositories/social_repo.py
5. 新增 src/data/tasks/ingest_x_posts.py
6. 新增 src/features/social/entity_linking.py
7. 新增 src/features/social/heat_score.py
8. 新增 src/features/social/ranking.py
9. 新增 src/features/tasks/build_social_mentions.py
10. 新增 src/features/tasks/build_social_heat.py
11. 新增 src/features/tasks/build_hot_rankings.py
12. 新增 src/tests/data/providers/test_x_provider.py
```

如果 X 数据要参与策略：

```text
13. 新增 strategy 中的组合逻辑
14. 新增 backtest 中的组合信号回测
```

不要把 X 数据接入写到 `market_data_service` 里。热度特征可以通过 `social_data_service` 或专门的 feature repository 给策略读取。

## 8. 数据表建议

可以按层次建表：

```text
raw_instrument
raw_market_daily
raw_market_weekly
raw_social_post
dim_instrument_alias
dim_sector
dim_sector_member

feature_kdj_daily
feature_kdj_weekly
feature_social_entity_mention
feature_social_heat_daily
feature_social_heat_weekly

signal_weekly_kdj_cross
signal_hot_stock
signal_hot_sector

backtest_holding_return
```

RAW 表保存标准化后的原始数据。

feature 表保存指标。

signal 表保存策略信号。

backtest 表保存回测结果。

## 9. 关键边界

必须遵守：

- provider 不写库。
- normalizer 不抓数据。
- storage 不知道策略。
- repository 不调用外部 API。
- service 不调用外部 API。
- feature 不调用外部 API。
- strategy 不调用外部 API。
- backtest 不调用外部 API。

只有 task 可以把 provider、normalizer、repository 串起来。

## 10. 最终目标

拆分后的好处：

- 换 Tushare 为 akshare，不影响 KDJ。
- 增加 X/Twitter，不影响行情。
- 找热门板块和热门股票，不需要让策略直接读取 X。
- 重算周线 KDJ，不需要重新抓外部数据。
- 重算热度分数，不需要重新抓 X 原始帖子。
- 回测可复现，因为回测只读已落库标准数据。
- 每个失败点都能定位到抓取、标准化、写库、指标、信号或回测。
