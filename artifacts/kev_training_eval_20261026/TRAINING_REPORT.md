# Kev 训练与评测报告：Qwen3-0.6B 与 Qwen3.5-0.8B

## 结论

两条三阶段 Kev 训练都已完成，并在同一组 6 个 held-out 测试集上完成评测。Qwen3.5-0.8B 在六项准确率上全部高于 Qwen3-0.6B，差距从 1.3 到 7.8 个百分点；Qwen3-0.6B 的总训练时间少约 21%，显存峰值也更低。

如果目标是这套 Kev 决策任务上的质量，当前结果应选 Qwen3.5-0.8B。如果更看重单卡训练时间和显存，Qwen3-0.6B 是更省资源的对照，但需要接受较低的准确率，尤其是 hard-v1。

这不是多 seed 的统计显著性实验，也不能把速度差全部归因于 `causal_conv1d`：模型规模、架构和该算子缺失同时变化。

## 实验目的与范围

本次比较两个 Base 模型在相同 Kev 三阶段训练流程下的表现：

- **Qwen3.5 run**：`Qwen/Qwen3.5-0.8B-Base`，GPU 1，输出目录 `runs/replica-20261026/`。
- **Qwen3 run**：本地 `/C20545/models/Qwen3-0.6B-Base`，GPU 2，输出目录 `runs/qwen3-06b-20261026/`。

Kev 不是自由文本生成训练。两个 run 都冻结 Base 模型，训练 LoRA（rank 16）和 256 维 pointer head；模型为候选选项直接输出概率，损失是选项级交叉熵。

## 共同训练设置

| 阶段 | 数据与初始化 | 主要设置 |
|---|---|---|
| Stage 1 | `decision-v7` 训练分区，12,576 records，2 epochs | batch 8，LR `1e-4`，seed 2 |
| Stage 2 | Stage 1 checkpoint；1,425 条日期/不可判定样本 + 2,000 条 `decision-v7` replay | batch 8，LR `4e-5`，seed 1 |
| Stage 3 | Stage 2 checkpoint；16,539 条 documents/skills/devtools 样本 + 6,000 条 replay | batch 4 × accumulation 2，LR `2e-5`，gradient checkpointing，最大状态长度 7,552 tokens，seed 1 |

`decision-v7` Stage 1 训练文件的 SHA-256 为 `7ed5254b5cb5291baefaceb09edf7e13110258211518c8038f4a12c11bd628ad`。两条 run 都在训练完成后仅用 development 集拟合一个温度，再读取测试集。

## 训练资源与时长

| 阶段 | Qwen3.5-0.8B | Qwen3-0.6B | Qwen3 相对更快 |
|---|---:|---:|---:|
| Stage 1 | 25 分 14 秒 | 17 分 25 秒 | 31.0% |
| Stage 2 | 2 分 22 秒 | 1 分 59 秒 | 16.3% |
| Stage 3 | 1 小时 32 分 4 秒 | 1 小时 14 分 35 秒 | 19.0% |
| 三阶段合计 | 1 小时 59 分 40 秒 | 1 小时 33 分 59 秒 | 21.5% |

Stage 3 是两条 run 最耗时的阶段。它处理长文档和规则/工具任务，前向 token 数约为 Stage 1 的 2.6 倍，同时 batch 较小并启用了 gradient checkpointing。

Qwen3.5 Stage 3 的日志还显示未安装 `causal_conv1d`，DeltaNet 卷积走了正确但较慢的 PyTorch fallback。Qwen3 不使用这一模块。这个差异很可能影响速度，但与模型参数量和架构差异混在一起，本次不能量化其单独贡献。

| 训练阶段显存峰值 | Qwen3.5-0.8B | Qwen3-0.6B |
|---|---:|---:|
| Stage 1 | 52.8 GiB | 34.5 GiB |
| Stage 2 | 40.8 GiB | 30.6 GiB |
| Stage 3 | 22.2 GiB | 15.9 GiB |

## Held-out 测试结果

所有下表测试集均完整评测，没有被拒绝或截断的记录。数值是 clean accuracy；`Δ` 为 Qwen3.5 减 Qwen3。

| 测试集 | Qwen3.5-0.8B | Qwen3-0.6B | Δ |
|---|---:|---:|---:|
| decision-v7 | 84.00% | 81.67% | +2.33pp |
| transfer-v4 | 67.84% | 65.40% | +2.44pp |
| transfer-v9 | 61.38% | 59.08% | +2.29pp |
| hard-v1 | 64.98% | 57.17% | +7.81pp |
| devtools-v1 | 65.14% | 63.00% | +2.14pp |
| documents-v1 | 83.44% | 82.16% | +1.28pp |

最明显的质量差异在 hard-v1。两模型在 documents-v1 和 decision-v7 上都较高，但 Qwen3.5 仍稳定领先。

评测与校准总时长如下：

| 流程 | Qwen3.5-0.8B | Qwen3-0.6B |
|---|---:|---:|
| 6 个测试集纯评测 | 8 分 12 秒 | 6 分 12 秒 |
| 含 development 温度校准 | 10 分 55 秒 | 7 分 28 秒 |

## 与官方 Kev-0.8B 报告的关系

Qwen3.5 run 使用官方公开训练流程和同一个 Base revision，但它从 Base 模型重新训练 LoRA 与 pointer head，并未加载官方发布的 `adapter_model.safetensors` 或 `head.pt`。因此它是配方复现，不是官方权重的副本。

与 Kev-0.8B model card 可逐项对应的结果如下：

| 测试集 | 本次 Qwen3.5 | 官方 Kev-0.8B | 差值 |
|---|---:|---:|---:|
| decision-v7 test | 84.0% | 83.8% | +0.2pp |
| transfer-v4 locked test | 67.8% | 69.7% | -1.9pp |
| documents-v1 test | 83.4% | 85.1% | -1.7pp |
| hard-v1 test | 65.0% | 66.5% | -1.5pp |
| devtools-v1 test | 65.17%* | 63.7% | +1.47pp |

\* 原始 devtools-v1 测试文件有 900 条记录、1,073 个问题，其中 `codereviewer/cls-test/19245` 这个 ID 被用于两条不同记录。官方 Kev 统计会排除这两条，留下 1,071 个问题；本地通用评测器默认保留全部 1,073 个问题，原始分数为 65.14%。表中为了对齐官方口径，使用排除后重算的 65.17%。

官方报告未提供可直接对应的 transfer-v9 locked-test 总分，因此不应把本次 61.38% 与官方某一数字直接比较。

官方发布训练环境与本次不同：官方使用 H100/H200；本次使用 A800、Python 3.12、Torch 2.8、Transformers 5.17 和 GLIBC 2.31 兼容层。Qwen3.5 缺少优化的 `causal_conv1d` 扩展。温度也重新拟合：本次 Qwen3.5 为 2.406，官方发布权重为 2.35。温度影响概率校准、NLL 和 ECE，不改变每题最高概率选项，因而不改变 accuracy。

## 结论边界与下一步

- 这是一对相同数据和日程下的单次 Base 模型对比，足以说明当前 run 中 Qwen3.5 的准确率更高、Qwen3 的资源成本更低。
- 不应把单次结果写成“Qwen3.5 普遍优于 Qwen3”的统计结论。至少需要多 seed，并在同一测试项上做配对 bootstrap 或 McNemar 检验。
- 不应把 Qwen3.5 的速度劣势全部归咎于 `causal_conv1d` 缺失。一个后续实验应在相同 Qwen3.5 checkpoint 与数据上，仅切换该 CUDA 扩展，再测 token/s 和端到端时长。
- 如果目标是选择当前可部署的 Kev checkpoint，应先确认是否需要官方发布权重；若目标是比较可复现训练流程，下一步应固定一个第二 seed，并使用官方的 devtools 去重规则统一重算。

## 可追溯文件

- 汇总指标：`runs/replica-20261026/summary.json`、`runs/qwen3-06b-20261026/summary.json`。
- 训练过程：每个 run 的 `stage{1,2,3}-train.log`、`stage{1,2,3}.resolved_config.json`、`stage{1,2,3}/training_metrics.json`。
- 校准与评测：`calibration.log`、`development-raw/report.json` 和 `benchmarks/*/report.json`。
- 环境与输入谱系：各 run 的 `reproduction_manifest.json`；Qwen3.5 另有 `final_checkpoint_metadata.json`。

官方对照来源：[Kev-0.8B model card](https://huggingface.co/jaredpalmer/kev-0.8b/blob/main/README.md)。
