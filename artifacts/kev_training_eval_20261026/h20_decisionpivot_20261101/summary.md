# Kev 4B/9B DecisionPivot Core 1.1 续训前后评测

日期：2026-11-01

## 结论

本轮 weak7 邻域扩充续训在独立的 DecisionPivot Core 1.1 上没有带来可信的整体提升：

| 模型 | 官方七层总分（续训前→后） | 平均逐题准确率 | 平均 contrast-pair 准确率 | 整体配对检验 |
|---|---:|---:|---:|---:|
| Kev 4B | 11.56 → 11.97（+0.41） | 48.19% → 48.10%（−0.09 pp） | 10.58% → 10.63%（+0.05 pp） | McNemar p=0.805 |
| Kev 9B | 15.99 → 16.11（+0.12） | 52.22% → 52.00%（−0.22 pp） | 14.59% → 14.91%（+0.32 pp） | McNemar p=0.450 |

4B 的官方分数略升主要来自 `log_count_check`，但被 `toolcall_valid` 的明显退化抵消；9B 基本持平，`answerable_facts`、`perm_inherit`、`state_goal` 的收益被 `record_rule`、`dep_resolve` 等退化抵消。两种规模的 7,800 道逐题准确率变化均不显著。

## 评测对象

| 模型 | 续训前检查点 | 本轮扩充续训后检查点 |
|---|---|---|
| 4B | `/data/kev/runs/h20-4b-s4` | `/data/kev/runs/h20-4b-weak7-neighborhood-expansion-e1-2gpu-20261101` |
| 9B | `/data/kev/runs/h20-9b-s3` | `/data/kev/runs/h20-9b-weak7-neighborhood-expansion-e1-4gpu-20261101` |

四组模型均用 Kev TypeSafe `/v1/systemone` 推理接口、BF16 权重和官方 DecisionPivot runner 评测。续训前在 GPU 4、续训后在 GPU 5 并行推理；32 个请求 worker。GPU 0–3 和 6–7 上的其他任务未被干预。

## 4B：13 类结果

| Family | 层 | Acc 前 | Acc 后 | Δ Acc | Pair 前 | Pair 后 | Δ Pair | 官方分数 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| answerable_facts | A | 57.50% | 57.83% | +0.33 pp | 16.00% | 20.00% | +4.00 pp | +0.67 |
| perm_inherit | B | 53.67% | 53.33% | −0.33 pp | 12.33% | 14.00% | +1.67 pp | −0.67 |
| policy_case | B | 50.00% | 51.00% | +1.00 pp | 8.46% | 9.95% | +1.49 pp | +1.50 |
| log_count_check | C | 50.67% | 52.50% | +1.83 pp | 14.33% | 16.67% | +2.33 pp | +3.67 |
| sched_conflict | D | 52.67% | 52.50% | −0.17 pp | 7.00% | 7.33% | +0.33 pp | −0.33 |
| state_goal | D | 54.83% | 55.33% | +0.50 pp | 12.00% | 13.67% | +1.67 pp | +1.00 |
| toolcall_valid | D | 66.33% | 60.67% | **−5.67 pp** | 32.67% | 21.33% | **−11.33 pp** | **−11.33** |
| triage_order | D | 30.00% | 30.83% | +0.83 pp | 5.47% | 6.47% | +1.00 pp | +1.04 |
| clause_change | E | 36.67% | 36.67% | 0.00 pp | 1.00% | 1.00% | 0.00 pp | 0.00 |
| dep_resolve | E | 54.67% | 54.67% | 0.00 pp | 12.67% | 12.33% | −0.33 pp | 0.00 |
| ledger_reconcile | F | 31.33% | 32.33% | +1.00 pp | 5.97% | 6.47% | +0.50 pp | +1.20 |
| record_rule | F | 34.67% | 34.00% | −0.67 pp | 2.00% | 1.33% | −0.67 pp | −0.76 |
| filter_match | G | 53.50% | 53.67% | +0.17 pp | 7.67% | 7.67% | 0.00 pp | +0.33 |

逐题配对中，只有 `toolcall_valid` 的退化清晰：56 道由对变错，22 道由错变对，McNemar p=0.00015。其余单类均无显著变化。4B 的层 D 因此从 15.04 降至 12.64。

## 9B：13 类结果

| Family | 层 | Acc 前 | Acc 后 | Δ Acc | Pair 前 | Pair 后 | Δ Pair | 官方分数 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| answerable_facts | A | 58.50% | 60.33% | +1.83 pp | 17.33% | 21.67% | +4.33 pp | +3.67 |
| perm_inherit | B | 54.17% | 55.17% | +1.00 pp | 12.33% | 14.33% | +2.00 pp | +2.00 |
| policy_case | B | 55.00% | 55.17% | +0.17 pp | 14.43% | 13.43% | −1.00 pp | +0.25 |
| log_count_check | C | 50.83% | 50.50% | −0.33 pp | 13.67% | 13.00% | −0.67 pp | −0.67 |
| sched_conflict | D | 53.67% | 53.50% | −0.17 pp | 8.67% | 8.00% | −0.67 pp | −0.33 |
| state_goal | D | 53.67% | 55.00% | +1.33 pp | 9.33% | 12.33% | +3.00 pp | +2.67 |
| toolcall_valid | D | 76.67% | 76.50% | −0.17 pp | 53.33% | 53.00% | −0.33 pp | −0.33 |
| triage_order | D | 33.33% | 33.33% | 0.00 pp | 5.97% | 6.97% | +1.00 pp | 0.00 |
| clause_change | E | 55.33% | 54.17% | −1.17 pp | 13.93% | 13.43% | −0.50 pp | −0.52 |
| dep_resolve | E | 56.83% | 55.17% | −1.67 pp | 17.33% | 15.33% | −2.00 pp | −3.33 |
| ledger_reconcile | F | 29.17% | 28.33% | −0.83 pp | 4.98% | 4.98% | 0.00 pp | −1.00 |
| record_rule | F | 45.00% | 42.00% | **−3.00 pp** | 4.00% | 2.67% | −1.33 pp | **−3.41** |
| filter_match | G | 56.67% | 56.83% | +0.17 pp | 14.33% | 14.67% | +0.33 pp | +0.33 |

`record_rule` 的逐题变化为 35 道由对变错、17 道由错变对，未校正 p=0.0175；但对 13 类做 Bonferroni 校正后不再显著。9B 所有 7,800 道的整体 McNemar p=0.450，不能认为续训改变了整体准确率。

## 官方层分数

| 模型 | A | B | C | D | E | F | G | 七层均值 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4B 前 | 15.00 | 16.17 | 1.33 | 15.04 | 4.67 | 21.69 | 7.00 | 11.56 |
| 4B 后 | 15.67 | 16.58 | 5.00 | 12.64 | 4.67 | 21.91 | 7.33 | 11.97 |
| 9B 前 | 17.00 | 20.42 | 1.67 | 21.17 | 12.09 | 26.26 | 13.33 | 15.99 |
| 9B 后 | 20.67 | 21.54 | 1.00 | 21.67 | 10.17 | 24.05 | 13.67 | 16.11 |

## 数据完整性与限制

- DecisionPivot 官方仓库 commit：`fd57688f033864e64c452561ffdfcba9739d1811`。
- Core 1.1：13 个 family，每类 600 条，共 7,800 条；生成器复核均为 `identical`，独立 solver 每类 600/600，key balance 全部通过。
- 四组运行均为 13/13 family、7,800/7,800 输出、0 请求错误、100% coverage。
- 官方 `score.py` 使用 1,000 次重采样计算区间。
- 这次只测了可公开重建的 Core track；Hugging Face gated reference track 未下载、未计入。
- 4B 续训前 `head.pt` 的 temperature 为 2.4623，续训后为 1.0，因此 ECE/Brier/置信度阈值类指标不可直接前后比较。本报告的主要结论基于 top-choice accuracy、pair accuracy 和官方 chance-corrected score；这些不受 temperature 缩放改变排序的影响。9B 前后 temperature 均为 1.0。
- 多类单项检验以探索性结果解读；没有把未经多重比较校正的 p 值当成正式提升证据。

## 复现与归档

- 官方评分文本：`kev_eval/results/{4b,9b}/report.txt`
- 官方结构化评分：`kev_eval/results/{4b,9b}/scores.json`
- 四组逐题输出：`kev_eval/runs/{4b-before,4b-after,9b-before,9b-after}/`
- Core 1.1 数据：`eval_data/tasks/`
- 数据哈希：`kev_eval/task_sha256.txt`
- 检查点哈希：`kev_eval/checkpoint_sha256.txt`
- 完整压缩归档：`decisionpivot-kev-before-after-20261101.tar.gz`
- 归档 SHA-256：`7bf05cfdca690a8d3af21ba1be3d4134663517ca5af35969b166614803c0fb30`

