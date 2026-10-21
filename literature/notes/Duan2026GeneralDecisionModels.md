# 文献笔记：General Decision Models—Benchmarking and Insights Beyond Jev

- 引用键：Duan2026GeneralDecisionModels
- 作者、年份、标题、期刊/预印本平台：Feiyu Duan 等，2026，*General Decision Models: Benchmarking and Insights Beyond Jev*，arXiv
- DOI/PMID/原文链接：https://arxiv.org/abs/2610.03935
- 版本与获取日期：arXiv:2610.03935；2026-10-21
- 负责人：CHENZW
- 创建/更新日期：2026-10-21
- 状态：completed
- 阅读范围：论文 §3、§4、§6、附录 F 的训练说明
- 关联检索、问题/假设、Issue 与路径：`L-20261021-CHENZW-001`；[Issue #7](https://github.com/wxie9/dummy-test-001/issues/7)

## 研究问题与方法

论文一面提出 JEVal 评测，一面用 First-Token Decision Readout 和 Reasoning-to-Readout Self-Distillation（R2RSD）把开放 LLM 的 reasoning 终点分布蒸馏到首个答案 token，得到 InnerJev-4B/27B 的单次前向决策 readout。

## 证据卡片

| 主张 | 证据摘要 | 原文位置（页/节/图/表） | 不确定性或局限 |
| --- | --- | --- | --- |
| Jev 原始配方未公开 | 文中明说 Jev 仅以 hosted API 可用，其训练 recipe 不公开。 | §6 开头 | 闭源 Jev 不能作为可复现训练基线。 |
| 首 token readout | 从 answer position 的 next-token distribution 中取有效 option labels，归一化得到决策概率；不需要新 head 或生成 token。 | §6.1，公式 (11) | 依赖每个有效标签被 tokenizer 编为单 token。 |
| 自蒸馏 teacher | 对每个训练问题生成两条 reasoning chain，取 reasoning 结束位置的 readout 分布平均为 teacher；不使用 gold label 替换或筛掉错误 teacher。 | §6.2，§6.2 Teacher | 自蒸馏会继承 teacher 的能力边界和错误。 |
| 学生目标 | student 在无 reasoning 的首 token 以 cross-entropy 拟合 teacher 分布，并以 KL 锚定冻结原 readout；score 另有期望等级项。 | §6.2，公式 (12) | 这是蒸馏方法，不是 RL。 |
| 数据和训练 | 训练池来自 8 类公共 decision datasets；InnerJev-27B 扩展至 39,279 questions；训练一 epoch，冻结 embeddings/output layer，更新 attention/MLP（full rank 或 LoRA）。 | §6.2、附录 F.2 | 论文给出类别和数量；本次核查未定位到官方训练代码仓库、数据 manifest 或 weights 发布页。 |

## 对本项目的意义

- 可借鉴的方法/数据：R2RSD 是最直接的“把 reasoning LLM 压缩成单步 decision readout”路线；可使用自身 reasoning 的分布，不需要外部教师标签。
- 与已有文献一致或冲突之处及引用键：与 `Zhuang2026StartLux` 同样使用有效选项读出，但 InnerJev 的训练核心是 SFT 式分布蒸馏；与 `Gao2026OpenJevRLCD` 的 on-policy RLCD 不同。
- 作者结论：InnerJev-27B 在 JEVal 上接近 Jev，同时以单步 readout 降低延迟；见 §6.3。
- 我们的解释或假设：这一路线适合先建立可复现 single-pass baseline，再考虑 RL/CD；但训练问题池和 reasoning 采样成本是关键变量。
- 需要进一步验证的问题：是否发布模型权重、具体来源/去重/许可、reasoning sampling 参数与实现。

## 附件与复现线索

- PDF 的 Zotero 条目或共享定位：arXiv:2610.03935。
- 代码、数据、方案链接及版本：论文方法与附录 F；本次核查未发现官方训练仓库链接，待后续复核。
- BibTeX 是否已加入 references.bib：否；共享 BibTeX 由指定维护者导入。

## 更正记录

无。
