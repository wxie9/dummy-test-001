# Kev-27B v1 六卡训练与评测报告

报告日期：2026-11-02

## 摘要

Kev-27B v1 在 H20 服务器上完成了六卡 LoRA 训练。训练使用与官方 B1-v2 完全同哈希的 15,401 条数据和相同的 Qwen3.8-27B 基座 revision。全程完成 2,567 个 optimizer steps，耗时 3 小时 59 分 48 秒，训练和六套评测均没有 rejected 或 truncated records。

六套冻结测试 clean 加权准确率为 **82.33%**（4,939/5,999）。模型在 decision-v7、transfer-v4 和 transfer-v9 上比 9B stage3 高 0.58、1.98 和 4.02 个百分点；在 hard-v1、devtools-v1 和 documents-v1 上低 5.61、10.53 和 2.88 个百分点。这不是纯参数 scaling：27B v1 只训 B1-v2，而 4B/9B checkpoint 训过后续 skills、devtools 和 documents 数据。

按官方审计口径对齐后，本次六卡 checkpoint 在 hard + audited devtools + documents 三套 pooled 上是 **81.40%**（2,275/2,795），官方 v1 为 80.00%；本次高 1.40 个百分点。transfer-v4 为 88.72%，比官方 v1 低 0.91 个百分点，但与官方 v2 的 88.87% 只差 0.15 个百分点。综合判断：**这次训练成功复现了官方 v1 的性能层级，但不是 bit-for-bit 复现。**

## 1. 实验目标

本次实验要验证三件事：

1. 官方 Kev-27B v1 的 B1-v2 LoRA 路线能否在六卡 H20 上完整跑通。
2. 使用官方同哈希数据和同基座后，重训 checkpoint 能否达到官方 v1 的测试水平。
3. 27B v1 与现有 4B/9B 多阶段 checkpoint 的强弱项分布有什么不同。

## 2. 数据与基座

| 项目 | 配置 |
|---|---|
| 基座 | `Qwen/Qwen3.8-27B` |
| 基座 revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| 训练数据 | 官方 B1-v2 重建数据 |
| requested records | 15,401 |
| 数据 SHA-256 | `fb86543b3baccb5aff9355065821e8481a083b874521637dc2f3a5cb06faa56a` |
| 数据关系 | 与官方 v1 B1-v2 完全同哈希 |

Qwen3.8-27B 是 Qwen 的 post-trained checkpoint，不是 `-Base` checkpoint。因此 Kev-27B v1 与从 Qwen3.5 Base 开始的小模型 Kev 不是只改变参数量的受控对比。

## 3. 训练配方

| 超参 | 本次配置 |
|---|---:|
| 训练方式 | LoRA |
| LoRA rank | 16 |
| LoRA targets | `all` |
| GPU / world size | 6 |
| per-GPU batch | 1 |
| gradient accumulation | 1 |
| effective batch | 6 records |
| epochs | 1 |
| backbone learning rate | `5e-5` |
| head learning rate | `0.0` |
| weight decay | `0.01` |
| precision | bf16 |
| gradient checkpointing | 开启 |
| max state | 7,552 tokens |
| seed | 2 |
| none-pair probability | 0.25 |

官方 v1 单卡配方的有效 batch 是 8；本次六卡为 6。因此两者虽然数据、基座、epoch、学习率和 LoRA rank 一致，但 optimizer 更新次数和学习轨迹不同。本次还使用了当前代码和 distributed-LoRA 改动，所以应称为“同配方层级复现”，不是逐比特复现。

## 4. 训练运行结果

| 指标 | 结果 |
|---|---:|
| optimizer steps | 2,567 / 2,567 |
| requested records | 15,401 |
| records seen | 18,172 |
| forward tokens | 10,164,492 |
| rejected records | 0 |
| truncated records | 0 |
| wall time | 14,387.924 s（3:59:47.9） |
| 平均 step time | 5.61 s |
| 平均梯度范数 | 6.352912 |
| 最大梯度范数 | 443.807129 |
| 触发 gradient clipping | 2,157 steps（84.0%） |
| peak device bytes | 79,335,837,184 bytes（约 73.9 GiB/GPU） |

`records seen` 多于 requested records，是因为训练时启用了 none-pair 扩增，不是重复计数错误。训练无 OOM、NaN、数据拒绝或截断。

84.0% 的 steps 触发了 gradient clipping。这表明该配方的原始梯度经常高于剪裁阈值；它没有导致训练失败，但是后续做精确复现或学习率消融时应保留的诊断信号。

## 5. 六套冻结测试

评测使用和 4B/9B 之前完全相同的 six-suite manifests。六套分别在 GPU0–5 上并行运行，覆盖 5,378 records / 6,565 questions，0 rejected/truncated。

| 测试集 | 4B stage4 | 9B stage3 | 27B v1 | 27B−9B |
|---|---:|---:|---:|---:|
| decision-v7 | 86.92% | 86.67% | **87.25%** (1047/1200) | +0.58 pp |
| transfer-v4 | 83.99% | 86.74% | **88.72%** (582/656) | +1.98 pp |
| transfer-v9 | 77.53% | 80.50% | **84.51%** (884/1046) | +4.02 pp |
| hard-v1 | 80.06% | 83.55% | **77.94%** (848/1088) | −5.61 pp |
| devtools-v1 | 75.21% | 81.17% | **70.64%** (758/1073) | −10.53 pp |
| documents-v1 | 89.32% | 90.49% | **87.61%** (820/936) | −2.88 pp |
| **clean 加权** | **82.00%** | **84.65%** | **82.33%** (4939/5999) | **−2.32 pp** |

按官方 devtools 口径剔除重复 ID `codereviewer/cls-test/19245` 的两条后，devtools 为 756/1,071 = 70.59%，六套加权为 4,937/5,997 = 82.32%。

## 6. 与官方 Kev-27B v1 对比

| 同口径 test panel | 官方 v1 | 本次六卡 v1 | 本次−官方 |
|---|---:|---:|---:|
| decision-v7 test | 87.00% | 87.25% | +0.25 pp |
| transfer-v4 locked test | 89.63% | 88.72% | −0.91 pp |
| hard-v1 | 74.90% | 77.94% | +3.04 pp |
| devtools-v1 audited sources | 78.90% | 78.73% | −0.17 pp |
| documents-v1 | 86.90% | 87.61% | +0.71 pp |
| **hard + audited devtools + documents pooled** | **80.00%** | **81.40%** | **+1.40 pp** |
| devtools-v1 all sources | 71.10% | 70.59% | −0.51 pp |

本次 checkpoint 在可直比 panel 上和官方 v1 处于同一水平。不同 suite 之间的差值有正有负，没有出现所有数据集一起下降的系统性失败。

transfer-v9 只有官方 development 成绩，没有与本次 1,046 题 test 同口径的官方 v1 数字，因此不纳入直比。

## 7. 与官方 Kev-27B v2 对比

| 同口径 test panel | 官方 v2 | 本次 v1 | 本次 v1−v2 |
|---|---:|---:|---:|
| transfer-v4 locked test | 88.87% | 88.72% | −0.15 pp |
| hard-v1 | 91.80% | 77.94% | −13.86 pp |
| devtools-v1 audited sources | 82.50% | 78.73% | −3.77 pp |
| documents-v1 | 90.80% | 87.61% | −3.19 pp |
| **hard + audited devtools + documents pooled** | **88.90%** | **81.40%** | **−7.50 pp** |
| devtools-v1 all sources | 79.00% | 70.59% | −8.41 pp |

v2 在 transfer-v4 上与本次 v1 基本持平，主要提升来自 hard/devtools/documents。官方 v2 的全参数 SFT 语料显式包含这三类的 training splits，因此它们的差距主要反映训练覆盖，不能简单解释为 v1 复现质量不够。

## 8. 结论

1. **训练完整跑通。** 2,567 steps 全部完成，权重、head、tokenizer、config 和 metrics 均已保存，数据拒绝和截断均为 0。
2. **达到官方 v1 性能层级。** 官方口径的三套 pooled 高 1.40 个百分点，transfer-v4 低 0.91 个百分点，整体没有系统性退化。
3. **不是 bit-for-bit 复现。** 六卡 effective batch=6，官方为 8；本次使用 distributed-LoRA 代码改动。
4. **与 4B/9B 的差异主要来自数据，不是单纯 scaling。** 27B v1 在 decision/transfer 强，在后续多阶段数据覆盖的 hard/devtools/documents 弱。
5. **与 v2 的主要差距是定向语料和全参数训练。** transfer-v4 只差 0.15 个百分点，但三套 trained-family pooled 低 7.50 个百分点。

## 9. 限制

- 只训了一个 seed，没有 seed 间方差。
- 本次六卡配方与官方 effective batch 不同。
- 评测使用 raw T=1；top-choice accuracy 不受正温度缩放影响，但 Brier/ECE 不可与官方 calibrated checkpoint 直比。
- 六套 clean 加权是本地总结指标，不是官方单一 headline metric。
- 4B/9B checkpoint 的训练阶段和基座与 27B v1 不同，只能作描述性比较。
- 官方 v2 的 hard/devtools/documents 测试属于已训练家族的 held-out items，不是完全新任务迁移。

## 10. 建议的下一步

1. 用 DecisionPivot Core 1.1 测试 27B v1，补充与 4B/9B 相同的结构化决策基准。
2. 补测 breadth-v1 和 tasksource-heldout-v1，与官方 v1/v2 的主要横向指标对齐。
3. 如果要测置信度，单独准备合规 calibration pool 拟合温度，再报 Brier/ECE。
4. 如果要精确对齐官方 v1，重跑 effective batch=8 或增加至少一个 seed，并冻结代码 commit。

## 11. 证据与路径

- 训练 checkpoint：`/data/kev/runs/h20-27b-v1-b1v2-ddp6-20261101/`
- 训练证据归档：`../h20_27b_v1_6gpu_20261101/`
- 六套评测归档：`../h20_27b_v1_six_test_20261102/`
- 评测副本 provenance：`../h20_27b_v1_six_test_20261102/evaluation_path_provenance.json`
- adapter SHA-256：`2254c36f318d23e83eeb363101b00fa840fd58f7bee7894c962520e1373bddfa`
- head SHA-256：`e35c7090af0b6ddde9740065d2c5747a9a31caaa0618f620de88a8d4c29b2cb3`
- 官方 v1：https://huggingface.co/jaredpalmer/kev-27b/blob/v1-lora/README.md
- 官方 v2：https://huggingface.co/jaredpalmer/kev-27b/blob/main/README.md

