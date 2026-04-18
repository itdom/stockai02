# AGENTS.md
> 本文件供 OpenAI Codex 及其他 AI 编程 Agent 自动读取，请勿删除。

---

## 项目简介
A 股全市场量化回测系统。
核心策略：扫描沪深两市所有股票的**周线 KDJ 金叉信号**，
模拟买入后分别统计持仓 5 / 10 / 20 / 60 个交易日的收益表现。

---

## 技术栈
- Python 3.11
- 数据源：tushare Pro（主力），akshare（备用/补充）
- Token：从环境变量 `TUSHARE_TOKEN` 读取，**严禁硬编码**
- 核心库：pandas / numpy / matplotlib / tqdm / tushare / akshare
- 测试框架：pytest

---

## 目录结构