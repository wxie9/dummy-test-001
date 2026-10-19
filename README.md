# JEV 科研协作

本仓库用于多人共同开展文献调研、湿实验记录、计算分析和阶段汇报。当前处于协作基础建设阶段，尚无研究数据或实验结论。

## 第一次参与

1. 阅读 [协作流程](CONTRIBUTING.md)、[编号与记录规范](docs/conventions.md) 和 [数据管理](docs/data-management.md)。
2. 在 `metadata/members.tsv` 注册唯一成员代号，并通过 PR 合并；代号使用 2–8 位大写字母或数字。
3. 在 GitHub 新建或认领一个文献、实验或分析 Issue，写清负责人和交付物。
4. 从最新 `main` 建短期分支，复制 [对应模板](templates/README.md)，开展工作并保存证据。
5. 提交 PR，关联任务和记录，请另一位成员评审后合并。

网页编辑文档也应选择新建分支并提交 PR。代码与数据分析在本地进行。完整命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 工作导航

| 工作 | 位置 | 从哪里开始 |
| --- | --- | --- |
| 找论文、读论文、整理综述 | [literature/](literature/README.md) | [检索记录](templates/literature-search.md)、[文献笔记](templates/literature-note.md) |
| 提出问题、假设、记录决策 | [research/](research/README.md) | [研究问题](templates/research-question.md)、[假设](templates/hypothesis.md)、[决策](templates/decision.md) |
| 维护实验方案 | [protocols/](protocols/README.md) | [方案模板](templates/protocol.md) |
| 记录湿实验 | [experiments/wet/](experiments/wet/README.md) | [湿实验记录](templates/wet-experiment.md) |
| 记录计算实验 | [experiments/computational/](experiments/computational/README.md) | [运行记录](templates/computational-run.md) |
| 登记样本、数据集 | [metadata/](metadata/README.md) | 按表头追加 TSV 记录 |
| 写分析代码、探索、复现流程 | [src/](src/README.md)、[notebooks/](notebooks/README.md)、[workflows/](workflows/README.md) | 先确定输入、输出和环境 |
| 保存测试与小型测试数据 | [tests/](tests/README.md) | 为分析逻辑加入适当验证 |
| 周报、阶段总结与图表 | [reports/](reports/README.md) | [周报模板](templates/weekly-report.md) |

## 一项研究如何串起来

文献引用键 → 研究问题 `Q-…` / 假设 `H-…` → 方案 `P-…@版本` → 湿实验 `E-…` 和样本 `S-…` → 数据集 `D-…@版本` → 计算运行 `R-…` → 图表与报告。

每一步写明上一环节的 ID 和记录路径。独立计算研究可以直接从公开数据集和研究问题开始，不必创建无关的湿实验记录。

## 文件放在哪里

- **Git：** 文献笔记、BibTeX、方案、实验记录、代码、参数、环境文件、元数据、小型测试数据和精选图表。
- **外部共享存储：** 原始仪器文件、大型图像、测序文件、模型和大量运行产物。仓库登记版本、校验和和团队可访问的定位。
- **文献附件：** 建议使用 Zotero 共享库；仓库保存稳定引用键、DOI/PMID 和阅读笔记。

数据下载位置与权限见 [数据管理](docs/data-management.md)。外部存储尚未配置；需要共享数据时由团队确定存储位置与维护人。

## 当前建设状态

已提供目录说明、模板、编号规则、GitHub Issue/PR 表单和 [AI 工作规范](AGENTS.md)。

成员代号表、样本表和数据集表目前只有表头。尚未配置外部数据存储、DVC、分析运行环境、流水线、CI 或远程分支保护。需要重复执行分析时再选择流程工具，按实际研究任务选择 Python、R 或其他环境。

后续可从已完成的工作流中提炼项目 skills，当前模板和规则是团队共同维护的依据。架构参考见 [参考来源](docs/references.md)。
