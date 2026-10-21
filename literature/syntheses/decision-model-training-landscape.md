# 开放决策模型：训练方法与复现线索

范围：截至 2026-10-21，基于 [检索记录](../searches/L-20261021-CHENZW-001.md) 中的论文和官方仓库。此文不报告本项目训练或评测结果。

## 结论先行

- **StartLux 的方法最完整，但原始训练复现条件不完整。** 论文披露三阶段、RLCD² 和数据类别；公开仓库提供推理和用户 LoRA 微调，不等同于发布 Lux-Release、Lux-Think、Stage 1–3 脚本及 RL rollout。
- **InnerJev 提供最清楚的“reasoning 内化成首 token 决策”训练目标。** 它是 self-distillation，而非 Jev 蒸馏，也不是 RL；本次核查未定位到官方训练代码/数据 manifest。
- **OpenJev-RLCD 是最小、可运行的 proper-score RL 原型。** 它适合理解校准 readout 与 rationale policy 的两阶段优化，但不是通用大语料决策模型训练配方。
- **Kev 是当前工程复现信息最充分的 SFT 基线。** 数据构建、训练、校准和评测流程都有公开代码；但其 pointer head 与 StartLux 的 option-letter readout 不是同一架构。
- **Laya 公开的是可用的下游微调工具。** 它可快速试验 soft target/RLCD，但不能据此声称复现原始 Laya checkpoint 或 StartLux。

## 横向比较

| 工作 | 训练数据 | 训练方法 | 公开实现 | 复现结论 |
| --- | --- | --- | --- | --- |
| [StartLux](../notes/Zhuang2026StartLux.md) | Lux-Release typed-decision mixture；Lux-Think 约 4k–21k reasoning examples/model | 全参 SFT → adapter specialization → reasoning SFT + RLCD²（proper score、frozen scorer、长度惩罚） | 推理/服务、用户 LoRA SFT；未在本次核查中见完整原始 pipeline/data | **方法部分可依；论文模型不可一键复现。** |
| [InnerJev](../notes/Duan2026GeneralDecisionModels.md) | 公共选项题池；27B 为 39,279 questions | reasoning endpoint distribution → first-token student；CE + KL anchor，1 epoch | 本次核查未定位官方训练仓库/manifest | **方法可实现，原作者模型复现材料不足。** |
| [OpenJev-RLCD](../notes/Gao2026OpenJevRLCD.md) | MMLU-Pro、GSM8K-Verify、ChaosNLI | Stage 1 proper-score readout calibration → Stage 2 REINFORCE rationale，KL/LOO baseline | 训练代码、脚本、逐项结果公开 | **小规模 RL 原型可复现。** |
| [Kev](../notes/Palmer2026Kev.md) | decision-v7 与后续文档/技能/工具数据；公开 manifest | pointer head + CE；LoRA 或 full FT；温度校准 | 训练、数据构建、Modal、评测和模型卡公开 | **最适合作为可执行 SFT 工程基线。** |
| [Laya](../notes/NandhaKishorM2026Laya.md) | 用户提供 typed soft targets；原始发布训练集未在本次核查中固定 | RLCD 风格 noisy-logit policy gradient + soft CE；下游校准 | `laya-train`/notebook 与文档公开 | **可复现下游微调，不等同原始模型复现。** |
| Jev（闭源对照） | 未披露 | 宣称 RLCD，但算法、数据和训练栈未公开 | hosted API | **不能作为本项目可复现训练起点。** |

## 训练路线建议

1. 先选 **Kev 或 Laya** 跑通公开、低风险的 typed-decision SFT/soft-target 基线，并独立记录数据与评测。
2. 若目标是把 reasoning 能力压缩成单次决策，先实现 **InnerJev 的 R2RSD**：固定 label-token readout、生成 reasoning teacher distribution、以 CE+KL 训练 first-token student。
3. 只有在已有可靠的概率 readout、标注 outcome、可承受 rollout 成本时，才引入 **OpenJev-RLCD** 风格两阶段 RL；不要直接声称它复现 RLCD²。
4. 若追求 StartLux，需另建复现计划，逐项补齐训练数据来源、adapter/attention 改造、reasoning supervisor、frozen scorer、长度惩罚、分布式栈和 policy-aware calibration。

## 已知边界

- 论文与仓库的公开状态会变化；链接固定到笔记中的版本或获取日期。
- “公开训练脚本”不等于“作者报告模型完全可复现”；需要同时有数据 revision、配置、环境、随机性和 checkpoint 选择规则。
- 本文没有下载数据、启动训练或验证性能；任何实践结论须以新的 TR/EV 记录为准。
