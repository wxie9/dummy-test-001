# JEV LLM 协作骨架 Implementation Plan

> 执行方式：当前会话顺序实施与检查。范围为管理文档、模板、元数据表和 GitHub 表单，不新增训练/评测软件。

**Goal:** 让团队可以在同一仓库开展 LLM 文献调研、训练、评测与日志交接。

**Architecture:** 一个主仓库管理文本、代码、配置与版本元数据，外部保存大型数据和 checkpoint，以稳定 ID 连接实验计划、运行和报告。

**Tech Stack:** Markdown、BibTeX、TSV、GitHub Issue Forms YAML、Git；实现面向 Python 与启动脚本。

## 约束

- 中文说明、ASCII 路径与 ID，不编造研究结果、模型版本、GPU 或配置。
- 不安装第三方 skills、训练框架或运行服务，不修改远程分支保护。
- 每次训练/评测独立记录，区分执行时代码版本、数据 split 和 checkpoint。
- 实际 GPU 训练与评测不属于本次文档交付。

## Task 1：入口、规则与目录

- [x] 更新 README、CONTRIBUTING、AGENTS、编号与数据管理说明。
- [x] 建立 literature、research、experiments、benchmarks、configs、src、scripts、notebooks、reports、tests 等目录说明。
- [x] 配置大文件忽略与跨平台文本换行规则。

## Task 2：记录与元数据

- [x] 建立文献检索/笔记、问题/假设、实验计划、训练、评测协议/运行、决策和周报模板。
- [x] 建立成员、数据集、模型与 checkpoint 的 TSV 表头，不生成实际记录。
- [x] 核查代码 commit、dirty 快照、恢复状态、评测条件和失败条目的字段。

## Task 3：协作表单

- [x] 建立文献、训练与评测 Issue Forms，更新 PR 模板。
- [x] 解析全部 YAML 并检查字段结构、必填状态和唯一 ID。

## Task 4：验收与交付

- [x] 检查相对链接、4 张 TSV 表头、模板字段与无关领域内容清理。
- [x] 在临时目录演练文献、实验计划、失败训练、checkpoint 登记和未执行评测的关联。
- [x] 检查忽略规则与 git diff，独立评审当前 LLM 范围。
- [x] 保存验收记录，提交并更新同一草稿 PR 的最终标题与描述，报告验证范围与资源限制。
