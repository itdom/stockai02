# AI3 人工文档索引

本目录主要放面向人阅读的说明文档，同时保留 AI Agent 的执行计划 `AI_TASKS.md`，便于任务清单和架构说明一起维护。

## 文档列表

- [data_architecture.md](data_architecture.md)：AI3 数据底座、模块分层、任务链路和边界说明。
- [readmin01.txt](readmin01.txt)：外部参考项目的阅读笔记，用于借鉴数据接入和流水线设计。

## AI 文档位置

AI Agent 读取的文件位置：

- [../AGENTS.md](../AGENTS.md)：Agent 必须遵守的项目规则和架构边界。
- [AI_TASKS.md](AI_TASKS.md)：Agent 执行计划、里程碑和验收清单。

后续新增文档时，按读者区分：

- 给人读的架构说明、设计解释、参考笔记，放在 `docs/`。
- 给 AI 读的项目规则放在仓库根目录 `AGENTS.md`；AI 执行计划放在 `docs/AI_TASKS.md`。
- 所有 Python 代码和测试代码都从 `src/` 作为一级目录开始。
