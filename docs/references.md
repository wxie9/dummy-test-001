# 架构与工具参考

以下原始资料用于 LLM 训练、评测与多人协作的骨架设计，核查日期为 2026-10-19。工具入口是候选参考，尚未作为依赖安装。

| 来源 | 采用的思想或后续用途 |
| --- | --- |
| [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) | 代码、数据、探索与报告分开组织 |
| [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) | 任务、短分支、PR 与评审 |
| [Transformers Trainer](https://huggingface.co/docs/transformers/main/en/trainer) | Python 训练入口与训练配置的候选实现 |
| [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | 版本化任务、prompt、指标与 LLM 评测的候选工具 |
| [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) | 训练运行、参数、指标与产物的可选平台 |
| [DVC Get Started](https://doc.dvc.org/start) | 大数据/模型外部存储与版本指针 |
| [Zotero Better BibTeX](https://retorque.re/zotero-better-bibtex/exporting/) | 稳定引用键与参考文献导出 |

## Skills

本版先维护团队共享模板，尚未安装第三方 skills。文献部分可评估 [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) 的 literature-review/citation-management；采用前记录上游 commit、检查依赖与实际输出。

项目 skills 待真实工作流验证后提炼：`jev-literature`、`jev-train-log`、`jev-eval-audit`，分别负责文献证据、训练记录完整性和评测可比性。字段以 templates/ 为唯一来源，不建立重复规范。
