# 文献笔记：Kev

- 引用键：Palmer2026Kev
- 作者、年份、标题、期刊/预印本平台：Jared Palmer，2026，*Kev* 官方仓库与模型卡
- DOI/PMID/原文链接：https://github.com/jaredpalmer/kev
- 版本与获取日期：仓库提交 `1f04cfa28e6a708485b28a9585010b9e436b776e`；2026-10-21
- 负责人：CHENZW
- 创建/更新日期：2026-10-21
- 状态：completed
- 阅读范围：README、`kev/train.py` 模块说明、公开模型卡
- 关联检索、问题/假设、Issue 与路径：`L-20261021-CHENZW-001`；[Issue #7](https://github.com/wxie9/dummy-test-001/issues/7)

## 研究问题与方法

Kev 在 Qwen 基座上训练 pointer head，对 `<decide>` 与各 option 表示打分并 softmax 成概率。小模型采用 LoRA + cross-entropy；27B 提供全参训练分支。仓库同时公开数据构建、训练、评测、校准和 Modal 运行入口。

## 证据卡片

| 主张 | 证据摘要 | 原文位置（页/节/图/表） | 不确定性或局限 |
| --- | --- | --- | --- |
| 输出与目标 | pointer head 对 option 隐状态与 question 隐状态打分；训练是正确答案的 cross-entropy，且明确不使用 Jev 输出。 | README “Training”前的模型说明 | 与 next-token option-letter readout 是不同实现。 |
| 主数据配方 | `decision-v7` 包含 10 个公开数据集的 10,000 examples、896 个生成 policy examples、60 个生成 rule structures 的 1,680 examples。 | README “Training” | 各来源许可与具体 revision 应在实际取数时再按 manifest 核查。 |
| 小模型训练 | 0.8B/4B/9B 训练两 epoch、LoRA rank 16、cross-entropy；之后有短的 follow-up fine-tunes。 | README “Training” | 已发布模型可能有各版本差异，须查对应 model card。 |
| 27B 训练 | `--full_ft 1` 训练全基座；README 报告 145,840 records、8×H200、一 epoch，并与早期 adapter 模型加权平均。 | README “Training” | 资源和数据规模远高于基础复现。 |
| 公开框架 | `kev.train` 支持 JSONL/suite、LoRA 和 full FT；full FT 使用 torchrun + FSDP2；Modal 脚本可运行 study。 | [`kev/train.py`](https://github.com/jaredpalmer/kev/blob/1f04cfa28e6a708485b28a9585010b9e436b776e/kev/train.py)、README | 公开实现仍依赖外部模型、数据镜像和计算资源。 |

## 对本项目的意义

- 可借鉴的方法/数据：这是目前披露最完整的通用 Jev 类训练框架之一，可作为可执行的 SFT/pointer-head 基线。
- 与已有文献一致或冲突之处及引用键：与 `Zhuang2026StartLux` 同属 typed decision，但不含 AutoThink/RLCD²；与 `Gao2026OpenJevRLCD` 的 reasoning RL 不同。
- 作者结论：仓库将训练、校准、固定评测 manifest 和试验计划纳入可执行工作流。
- 我们的解释或假设：若先做可复现系统，Kev 的代码组织更适合作为工程起点；若追求 StartLux 的方法，仍需单独实现 AutoThink 与 RLCD²。
- 需要进一步验证的问题：目标模型架构与 pointer head 的兼容性、许可证、完整数据镜像与硬件预算。

## 附件与复现线索

- PDF 的 Zotero 条目或共享定位：不适用：本记录以官方仓库和模型卡为一手来源。
- 代码、数据、方案链接及版本：[Kev](https://github.com/jaredpalmer/kev/tree/1f04cfa28e6a708485b28a9585010b9e436b776e)。
- BibTeX 是否已加入 references.bib：否；仓库型来源暂不写入共享 BibTeX。

## 更正记录

无。
