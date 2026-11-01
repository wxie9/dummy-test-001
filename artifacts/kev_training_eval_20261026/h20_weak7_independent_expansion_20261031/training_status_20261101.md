# H20 4B/9B 扩充数据续训状态

## 启动状态

- 启动时间：2026-11-01 01:03:37 CST。
- 4B：从 `/data/kev/runs/h20-4b-s4` 重新开始，一轮，GPU 0–1，world 2，batch 2，accum 2，有效 batch 8。
- 9B：从 `/data/kev/runs/h20-9b-s3` 重新开始，一轮，GPU 2–5，world 4，batch 2，accum 1，有效 batch 8。
- 两者均使用 LR `1e-5`、LoRA rank 16、seed 101、max_state 7552，并混入 6,000 条 decision-v7 replay。
- 4B 训练输入 3,084 条，预期 1,136 updates；9B 训练输入 2,928 条，训练请求总数 8,928。

远端数据目录：`/data/kev/local_data/h20_weak7_independent_expansion_20261101/`。

远端运行目录：

- 4B：`/data/kev/runs/h20-4b-weak7-neighborhood-expansion-e1-2gpu-20261101/`
- 9B：`/data/kev/runs/h20-9b-weak7-neighborhood-expansion-e1-4gpu-20261101/`

训练完成后，两个启动脚本会自动评测各自 combined development 和六套冻结测试。

## 预检

- 本地与远端四份 JSONL SHA-256 一致。
- 4B：train 3,084/3,654 子问题，development 538/658，7552-token rejected 0。
- 9B：train 2,928/3,990 子问题，development 486/682，7552-token rejected 0。

## 启动验证

- 4B 已进入 `ep0 step 20/1136`；两张卡约使用 21 GB 显存。
- 9B 已完成 warm start 并进入训练计算；四张卡约使用 43–49 GB 显存，启动核验时 GPU 利用率均为 100%。
- 服务器另有 GPU 6–7 空闲。

当前状态：训练进行中，尚无训练后结果。

## 01:34 后续状态与评测修复

- 4B 训练在 01:34:09 CST 完成，`training_metrics.json` 已保存。
- 原启动脚本直接用 `benchmark --data` 读取 combined development。推理完成约 450/538 后，汇总器把自定义 source 全部视为 heldout，clean population 为空，报 `ValueError: cannot score an empty population`。这是评测清单元数据问题，不是模型训练或推理失败。
- 已按此前成功使用的 suite 格式建立 `devsuite_4b`、`devsuite_9b`，明确 `holdout_sources: []`，并准备 `post_eval_h20.sh`。两个 development 文件的 SHA-256 已再次核对。
- 当前 GPU 0、1、6、7 被服务器上的其他任务占用；未抢占或终止这些任务。9B 仍在 GPU 2–5 正常训练。待 9B 释放 GPU 后，用空闲卡分别重跑 4B/9B development，并继续六套冻结测试。

## 02:56 第二次评测修复

- 4B 与 9B 训练均已完成并保存检查点；9B 于 02:40:00 CST 完成。
- 第一版 suite 修复后，两组 development 推理均已跑完，但汇总仍失败。根因是 Kev 评测器只把 `_meta.variant == "clean"` 的记录计入准确率，而 combined development 保留了合成数据的来源变体标签（4B：328 条 `error_neighborhood`、210 条 `independent_development`；9B：276 条和 210 条），因此 scored population 仍为空。
- 已生成仅供评测的派生副本，只把 `_meta.variant` 规范为 `clean`；题目、选项、答案标签、source、记录 ID 及其余元数据均不变。
- 完整来源哈希、派生哈希、记录数和原始 variant 计数记录在 `eval_development_derivation.json`。

## 完成状态

- 4B development 与六套冻结测试于 03:25:39 CST 全部完成。
- 9B development 与六套冻结测试于 03:41:16 CST 全部完成。
- 两组训练和所有评测的 rejected/truncated 均为 0；六套测试的 suite hash、分母和逐题键与原始 checkpoint、上一轮 weak7 候选一致。
- 60 个训练指标、报告、逐题 rows、预测及日志文件已归档到本目录 `archive/`，并通过 `archive_sha256.txt` 全量校验。
- 完整三方逐题对比见 `expanded_results.md` / `expanded_results.json`。

核心结果：4B 六套加权准确率从原始 82.00% 提到 83.41%（+1.42 pp，McNemar exact p=2.81e-05）；9B 从 84.65% 提到 85.08%（+0.43 pp，p=0.1336）。4B 的增益主要集中在 devtools 与目标弱类，非目标类别合计下降 1.2 pp；9B 的 hard-v1 明显改善，但工具路由及若干 transfer 套件回落。因此两个 checkpoint 均保留为候选，不自动替换默认模型。
