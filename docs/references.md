# 架构参考

以下是 2026-10-19 调研并用于本仓库设计的原始资料。仓库结构是针对计算与湿实验协作的组合设计，未复制完整软件模板。

| 来源 | 采用的思想 |
| --- | --- |
| [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) | 代码、数据、探索和报告分开组织 |
| [The Turing Way：Research Data Management](https://book.the-turing-way.org/reproducible-research/rdm/) | 元数据、可复用性和备份 |
| [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) | 短分支、PR 与评审 |
| [Snakemake：Distribution and Reproducibility](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html) | 工作流、配置、环境与结果的边界 |
| [DVC Get Started](https://doc.dvc.org/start) | Git 中保存数据版本描述，外部保存大文件 |
| [eLabFTW](https://www.elabftw.net/) | 湿实验记录和资源管理的可选接入 |
| [Zotero Better BibTeX](https://retorque.re/zotero-better-bibtex/exporting/) | 稳定引用键和参考文献导出 |

## 后续 skills 候选

尚未安装或内置以下第三方 skills。实际接入前选择需要的能力，检查依赖与授权范围，记录采用的上游 commit，避免团队成员各自使用不一致版本。

- [K-Dense scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)：优先评估 `literature-review`、`citation-management`，按任务考虑 `experimental-design`、`scientific-critical-thinking`。
- [Google DeepMind science-skills](https://github.com/google-deepmind/science-skills)：按任务选择文献与科学数据库访问能力。

项目自己的文献、实验日志与复现检查 skills，在至少一轮实际任务完成后，从本仓库模板提炼；模板保持字段的唯一来源。
