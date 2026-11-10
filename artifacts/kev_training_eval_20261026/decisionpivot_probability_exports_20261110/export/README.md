# DecisionPivot 三模型逐题概率导出

本目录对齐了 Kev 融合版、StartLux Instant 和 StartLux AutoThink 的 7,800 道 DecisionPivot Core 1.1 题目。没有重新推理；全部字段来自已有运行归档。

## 文件

- `kev_blend_questions.jsonl`：Kev 融合版逐题结果。
- `startlux_instant_questions.jsonl`：StartLux Instant 逐题结果。
- `startlux_autothink_questions.jsonl`：StartLux AutoThink 逐题结果。
- `all_three_questions.jsonl`：三模型合并的逐题 JSONL。
- `all_three_question_level.csv`：每个模型每题一行，概率字典放在 `probabilities_json`。
- `all_three_option_level.csv`：每个选项一行，便于透视、筛选和画图。
- `manifest.json`：来源哈希、输出哈希、计数及一致性检查。

## 字段边界

Kev 源文件的概率约保留四位小数，StartLux 保留完整 JSON 浮点精度。Kev 没有 `none_probability`，因此在 JSONL 中为 `null`、CSV 中为空。StartLux 的 `none_probability` 是候选集合之外的额外概率；`probabilities` 已在正常候选内部归一化。
