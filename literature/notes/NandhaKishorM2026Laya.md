# 文献笔记：Laya

- 引用键：NandhaKishorM2026Laya
- 作者、年份、标题、期刊/预印本平台：Laya 维护者，2026，*Laya* 官方仓库与微调文档
- DOI/PMID/原文链接：https://github.com/NandhaKishorM/laya
- 版本与获取日期：仓库提交 `ffc142012af63d015fa19f05f29f9c5ff329a2cc`；2026-10-21
- 负责人：CHENZW
- 创建/更新日期：2026-10-21
- 状态：completed
- 阅读范围：官方 `docs/finetune.md` 与 README；未将其当作原始 checkpoint 完整训练报告
- 关联检索、问题/假设、Issue 与路径：`L-20261021-CHENZW-001`；[Issue #7](https://github.com/wxie9/dummy-test-001/issues/7)

## 研究问题与方法

Laya 是非自回归 typed decision engine。其公开微调工具支持 `choice`、`score`、`noul`，默认 `rlcd` loss，或仅用 soft cross-entropy；输入训练数据携带 teacher/gold distribution，训练后再使用 calibration slice 拟合温度与 abstention 设置。

## 证据卡片

| 主张 | 证据摘要 | 原文位置（页/节/图/表） | 不确定性或局限 |
| --- | --- | --- | --- |
| 可执行微调框架 | `laya-train`/`laya.train.finetune` 公开；可指定 base、数据、encoder/head LR、mixed precision、checkpointing 和 evaluation data。 | [`docs/finetune.md`](https://github.com/NandhaKishorM/laya/blob/ffc142012af63d015fa19f05f29f9c5ff329a2cc/docs/finetune.md) | 是用户/下游微调框架，不自动等于发布 checkpoint 的完整原始训练流程。 |
| RLCD 形式 | 文档称默认 `rlcd`：对 teacher distribution 使用 proper-score 的 GRPO-style noisy-logit policy gradient，加 full-weight soft CE。 | 同上，"The training recipe" | 目标质量上限受 teacher confidence 限制，文档也明确提醒。 |
| 训练配置 | 文档示例：4 epochs、effective batch 64、AdamW/cosine、encoder LR 2.5e-5、head LR 1e-4；CUDA 默认 mixed precision。 | 同上，"The training recipe" | 是 notebook 默认，不应误认为所有已发布 Laya 权重的历史配置。 |
| 数据边界 | 工具要求输入 typed decisions 与 soft targets；文档提供示例数据规模，但本次核查未获得原始发布模型的完整训练数据清单。 | 同上，"What to watch" | 原始模型训练数据和全历史复现性仍待单独核查。 |

## 对本项目的意义

- 可借鉴的方法/数据：低门槛 typed-decision 微调、soft targets、option shuffle、温度/弃答校准与训练报告结构。
- 与已有文献一致或冲突之处及引用键：与 `Gao2026OpenJevRLCD` 都以 proper scoring 为核心，但 Laya 把 RLCD 包装为可用的下游微调流程；与 `Palmer2026Kev` 的硬标签 pointer-head SFT 形成对照。
- 作者结论：文档提供训练、评估、校准、推送 Hub 的完整用户流程。
- 我们的解释或假设：可作为快速 baseline，但不应据此声称复现 Laya 原始模型，也不能直接等同 StartLux 的 AutoThink/RLCD²。
- 需要进一步验证的问题：官方发布 checkpoint 的真实训练语料、基座、训练阶段及与文档默认值的差异。

## 附件与复现线索

- PDF 的 Zotero 条目或共享定位：不适用：本记录以官方仓库文档为一手来源。
- 代码、数据、方案链接及版本：[Laya](https://github.com/NandhaKishorM/laya/tree/ffc142012af63d015fa19f05f29f9c5ff329a2cc)。
- BibTeX 是否已加入 references.bib：否；仓库型来源暂不写入共享 BibTeX。

## 更正记录

无。
