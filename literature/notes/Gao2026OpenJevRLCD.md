# 文献笔记：OpenJev-RLCD

- 引用键：Gao2026OpenJevRLCD
- 作者、年份、标题、期刊/预印本平台：Zhimin Gao、Pichao Wang，2026，*OpenJev-RLCD: A Working RLCD Implementation*，arXiv
- DOI/PMID/原文链接：https://arxiv.org/abs/2609.38850
- 版本与获取日期：arXiv:2609.38850；2026-10-21
- 负责人：CHENZW
- 创建/更新日期：2026-10-21
- 状态：completed
- 阅读范围：论文 §3–4；官方 README 与训练入口说明
- 关联检索、问题/假设、Issue 与路径：`L-20261021-CHENZW-001`；[Issue #7](https://github.com/wxie9/dummy-test-001/issues/7)

## 研究问题与方法

对 reasoning LLM，先生成 rationale，再从 rationale 后的 answer readout 取分布 `u(r)`；用 strictly proper scoring rule 对该分布给 reward。训练分两段：先校准 readout，再以同一 proper-score reward 强化 rationale。

## 证据卡片

| 主张 | 证据摘要 | 原文位置（页/节/图/表） | 不确定性或局限 |
| --- | --- | --- | --- |
| 两阶段 RLCD | Stage 1 对 sampled rationale 后的 readout 做 pathwise proper-score 优化；Stage 2 从 stage-1 checkpoint 出发，以 REINFORCE 强化 rationale。 | §3.3，算法 1 | 这是作者实现的 RLCD，不代表闭源 Jev 的未公开算法。 |
| 稳定化设置 | Stage 2 使用 leave-one-out baseline、KL anchor 与降权 score-function 项（论文示例 `c=0.3`, `β=0.04`）。 | §3.3 | 超参数是论文实验设置，迁移任务需重新验证。 |
| 训练数据和模型 | Qwen3-1.7B；MMLU-Pro、GSM8K-Verify 和 ChaosNLI。GSM8K-Verify 由 GSM8K 问题与 Qwen3-0.6B 采样解答构造。 | §4，尤其 4.1 | 不是通用大规模决策语料配方。 |
| 公开实现 | 仓库公开训练代码、运行脚本和逐项结果；入口为 `openjev_rlcd.train`。 | [GitHub README](https://github.com/ZimmyGao/openjev-rlcd/tree/22db40ad3333f5cf0bc5139097da70e0f8c05018) | 可运行代码不消除上游数据许可、GPU 与版本差异。 |

## 对本项目的意义

- 可借鉴的方法/数据：是目前最清晰、可读的 proper-score RL reasoning 最小实现，可用于理解 Stage 1/2 的梯度分工。
- 与已有文献一致或冲突之处及引用键：`Zhuang2026StartLux` 的 RLCD² 以 frozen scorer、decision-weighted score 和长度项扩展该方向；`Duan2026GeneralDecisionModels` 则不需 RL。
- 作者结论：在两个 reasoning tasks 上与 SFT/RFT/GRPO 比较，强调 selective prediction 与校准；详见 §5。
- 我们的解释或假设：适合作为 RL 机制原型，而不是直接替代 StartLux 的数据和多阶段架构。
- 需要进一步验证的问题：适配 typed multi-question API、长上下文和非单选输出时的 reward/rollout 成本。

## 附件与复现线索

- PDF 的 Zotero 条目或共享定位：arXiv:2609.38850。
- 代码、数据、方案链接及版本：[openjev-rlcd](https://github.com/ZimmyGao/openjev-rlcd/tree/22db40ad3333f5cf0bc5139097da70e0f8c05018)。
- BibTeX 是否已加入 references.bib：否；共享 BibTeX 由指定维护者导入。

## 更正记录

无。
