# 决策模型：训练方法、benchmark 与数据集清单

- 日期：2026-10-21
- 负责人：CHENZW
- 范围：公开论文与官方仓库；本项目尚未训练或跑分。
- 关联：[评测登记 #5](https://github.com/wxie9/dummy-test-001/issues/5)、[训练调研 #7](https://github.com/wxie9/dummy-test-001/issues/7)、[报告 #9](https://github.com/wxie9/dummy-test-001/issues/9)

## 训练方法

| 工作 | 方法 | 代码/完整复现状态 |
| --- | --- | --- |
| [StartLux](../../literature/notes/Zhuang2026StartLux.md) | 三阶段：① Lux-Release 全参 SFT；② adapter 决策训练（Instant 用双向 full-attention，AutoThink 保持 causal）；③ Lux-Think reasoning SFT，再用 RLCD²。RLCD² 用 frozen probability scorer、decision-weighted proper score 和 reasoning 长度软惩罚。 | 推理、服务和用户 LoRA 微调公开；作者原始 Stage 1–3、RLCD² 训练流水线未完整公开。 |
| [InnerJev](../../literature/notes/Duan2026GeneralDecisionModels.md) | First-Token Decision Readout：有效选项 token 的 next-token logits 归一化为概率。R2RSD：用模型 reasoning 结束处的分布作为 teacher，训练无 reasoning 的首 token student；loss 为 soft CE + score 期望等级项 + 冻结 readout 的 KL anchor。 | 论文披露方法；本次核查未定位官方训练代码/完整数据 manifest。 |
| [OpenJev-RLCD](../../literature/notes/Gao2026OpenJevRLCD.md) | 两阶段 RLCD：① proper scoring rule 校准 rationale 后的 readout；② 从 stage-1 checkpoint 出发，用 REINFORCE 强化 rationale，含 leave-one-out baseline 与 KL anchor。 | 训练代码、脚本和逐项结果公开。 |
| [Kev](../../literature/notes/Palmer2026Kev.md) | pointer head 对 question/option 表示打分，softmax 输出概率；小模型用 LoRA + cross-entropy，27B 支持 full fine-tune；之后做温度校准。 | 训练、数据构建、评测、Modal 运行和模型卡公开。 |
| [Laya](../../literature/notes/NandhaKishorM2026Laya.md) | 下游微调默认 `rlcd`：对 soft target 用 GRPO-style noisy-logit policy gradient + proper scores，同时加 soft CE；之后做温度和 abstention 校准。 | `laya-train`/notebook 与文档公开；不是原始 Laya checkpoint 的完整训练历史。 |
| Jev | 对外称 RLCD。 | 训练算法、数据、代码和训练栈未公开；仅 hosted API。 |

## benchmark

| Benchmark | 数据版本/范围 | 协议 | 公开状态 |
| --- | --- | --- | --- |
| Decision Index | 0.3 public index；不含 0.4 私有部分。 | [B-20261021-CHENZW-001](../../benchmarks/B-20261021-CHENZW-001/v1.0.0.md) | 公开重建工具与公开 suite；本项目未下载或运行。 |
| DecisionPivot Core | 1.1，13 个程序生成 families、7,800 items。 | [B-20261021-CHENZW-002](../../benchmarks/B-20261021-CHENZW-002/v1.0.0.md) | 可由公开 generator/seed 重建；仅限评测。 |
| DecisionPivot Reference | 1.3，35 个来源任务、32,233 items。 | [B-20261021-CHENZW-003](../../benchmarks/B-20261021-CHENZW-003/v1.0.0.md) | 固定 HF revision；运行前需核对来源许可/访问条件；仅限评测。 |
| JevBench public | 1.2 固定公开题：original 72、easy 48、hard 111，共 231 题。 | [B-20261021-CHENZW-004](../../benchmarks/B-20261021-CHENZW-004/v1.0.0.md) | 只覆盖公开题；不含密封题和后续榜单 composite，不能当作完整 JevBench 总分。 |

## 训练数据集

| 工作 | 训练数据 | 是否能直接取得 |
| --- | --- | --- |
| StartLux | Lux-Release：公开数据重写为 typed decisions，覆盖分类、NLI、QA、安全、偏好与 tool use；Lux-Think：约 4k–21k supervised reasoning examples/model。 | 数据类别和规模披露；完整样本清单、混合比例、处理代码与数据包未确认公开。 |
| InnerJev | 公共 option questions，覆盖语言理解、常识、逻辑、中英医学、规则/计算、安全和主观判断；27B 使用 39,279 questions。 | 论文给出类别和总量；本次核查未定位官方 manifest/下载包。 |
| OpenJev-RLCD | MMLU-Pro；GSM8K-Verify（GSM8K + Qwen3-0.6B 采样解答）；ChaosNLI。 | 上游公开数据；构造和切分在论文/代码中披露。 |
| Kev | `decision-v7`：十个公开数据集 10,000 examples、896 生成 policy examples、60 个生成 rule structures 的 1,680 examples；27B 还加入文档、技能、工具、长文档与 guardrail records。 | 代码与 manifest 公开；实际下载按上游许可和版本执行。 |
| Laya | 用户/下游任务提供的 typed decisions 与 teacher/gold soft target distributions。 | 微调框架公开；原始发布 checkpoint 的完整训练数据未在本次核查中固定。 |

## 评测数据登记

四个 benchmark 数据对象及其固定 revision、manifest hash、许可边界在 [`metadata/datasets.tsv`](../../metadata/datasets.tsv) 中登记。这里的 manifest hash 不表示本项目已下载、验证或使用题目正文。
