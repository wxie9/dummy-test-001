# JEV · LLM 训练与评测协作

本仓库用于多人共同开展大语言模型的文献调研、训练、评测和实验日志管理。当前处于协作基础建设阶段，尚无训练代码、数据、checkpoint 或实验结论。

## 第一次参与

1. 阅读 [协作流程](CONTRIBUTING.md)、[编号与记录规范](docs/conventions.md) 和 [数据管理](docs/data-management.md)。
2. 在 `metadata/members.tsv` 注册唯一成员代号，并通过 PR 合并；代号使用 2–8 位大写字母或数字。
3. 在 GitHub 新建或认领一个文献、训练或评测 Issue，写清负责人和交付物。
4. 从最新 `main` 建短期分支，复制 [对应模板](templates/README.md)，开展工作并保存证据。
5. 提交 PR，关联任务和记录，请另一位成员评审后合并。

网页编辑文档也应选择新建分支并提交 PR。训练与评测在具备相应资源的环境执行。完整协作命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 工作导航

| 工作 | 位置 | 从哪里开始 |
| --- | --- | --- |
| 找论文、读论文、整理综述 | [literature/](literature/README.md) | [检索记录](templates/literature-search.md)、[文献笔记](templates/literature-note.md) |
| 提出问题、假设、记录决策 | [research/](research/README.md) | [研究问题](templates/research-question.md)、[假设](templates/hypothesis.md)、[决策](templates/decision.md) |
| 计划基线、变量与消融实验 | [experiments/](experiments/README.md) | [实验计划](templates/experiment-plan.md) |
| 记录训练与 checkpoint | [experiments/training/](experiments/training/README.md) | [训练记录](templates/training-run.md) |
| 固定评测条件与计分规则 | [benchmarks/](benchmarks/README.md) | [评测协议](templates/evaluation-protocol.md) |
| 保存评测运行与结果 | [experiments/evaluation/](experiments/evaluation/README.md) | [评测记录](templates/evaluation-run.md) |
| 登记数据、模型与 checkpoint | [metadata/](metadata/README.md) | 按表头追加 TSV 记录 |
| 实现与启动训练/评测 | [src/](src/README.md)、[scripts/](scripts/README.md)、[configs/](configs/README.md) | 先确定框架、输入、输出和环境 |
| 临时探索与结果检查 | [notebooks/](notebooks/README.md) | Python notebook |
| 保存测试与小型测试数据 | [tests/](tests/README.md) | 为数据处理、训练和计分逻辑加入适当验证 |
| 周报、阶段总结与图表 | [reports/](reports/README.md) | [周报模板](templates/weekly-report.md) |

## 一项研究如何串起来

文献 → 问题 `Q-…` / 假设 `H-…` → 实验计划 `E-…` → 训练 `TR-…` → checkpoint `C-…` → 评测 `EV-…` → 指标与报告。

训练关联基础模型 `M-…`、数据版本 `D-…@版本:split` 和配置；评测关联精确模型/checkpoint、数据 split 与评测协议 `B-…@版本`。仅评测外部模型时直接从 M-ID 开始，无需创建虚构训练记录。

## 文件放在哪里

- **Git：** 文献笔记、BibTeX、实验计划、训练/评测配置、运行记录、代码、环境锁定文件、元数据、小型测试数据和精选结果摘要。
- **外部共享存储：** 训练语料、tokenized 数据、模型权重/checkpoint、大型预测结果与完整日志。仓库登记精确版本、校验和和团队可访问的定位。
- **文献附件：** 建议使用 Zotero 共享库；仓库保存稳定引用键、DOI/PMID 和阅读笔记。

数据下载位置与权限见 [数据管理](docs/data-management.md)。外部存储尚未配置；需要共享数据时由团队确定存储位置与维护人。

## 当前建设状态

已提供目录说明、模板、编号规则、GitHub Issue/PR 表单和 [AI 工作规范](AGENTS.md)。

成员、数据集、基础模型和 checkpoint 表目前只有表头。实现面向 Python 与训练/评测启动脚本；具体训练框架、评测工具、GPU 资源和依赖环境随首个任务确定。尚未配置外部存储、运行平台、CI 或远程分支保护。

后续可从已完成的工作流中提炼项目 skills，当前模板和规则是团队共同维护的依据。架构参考见 [参考来源](docs/references.md)，本次检查范围见 [验收记录](docs/verification.md)。
