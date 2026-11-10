# Tasksource Pivot 定向 24K 候选集（2026-11-05）

## 结论

已从公开的 `tasksource/tasksource-jev-typed-decisions`（`full` 配置）中抽取一份面向 DecisionPivot 薄弱能力的 24,000 条候选集。

这份数据是**我们自行选择 family 后得到的可复现重建集**，不是 Kev-27B v2 官方私有 Tasksource 24K 的精确副本。官方 119 个 family、精确抽样行和最终顺序仍未公开。

## 远端文件

- 数据：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource_pivot_commercial_24k_typed.jsonl`
- manifest：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource_pivot_commercial_24k_manifest.json`
- 商用 family 库存：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/commercial_selection_inventory.json`
- 原 60-family 默认配置库存：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/default_selected_inventory.json`
- 原 60-family 完整配置库存：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/full_selected_inventory.json`
- 未进入 Jev 发布配置的四项可访问性检查：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/missing_four_access_check.json`
- Tasksource 源码：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource`
- Tasksource commit：`2796c32a346733e14b8c19b47e2fd9aade5aa03b`

## 文件指纹

- 行数：24,000
- 字节数：62,584,510
- SHA-256：`f71e19e14c1aadb4ccc6bec17a92c53a65abe7a3ec9b05638797da56d9757133`
- 抽样 seed：`kev-tasksource-20261105`
- 原始 split：`train` 24,000 条
- `license_use`：`commercial` 24,000 条
- 来源 family：44 个
- 精确内容重复：0

## 能力配比

| 能力组 | 条数 | 主要面向的 Pivot 薄弱点 |
|---|---:|---|
| rule_policy_dependency | 7,000 | 规则链、政策依赖、条件组合、permission/constraint |
| table_ledger_filter | 4,500 | 表格、账本、筛选、计数与结构化事实 |
| state_time_order | 4,000 | 状态变化、时间顺序、计划步骤与多步状态维护 |
| grounding_multihop | 4,000 | 文档证据、可回答性、跨段支持与多跳归因 |
| agent_action | 2,500 | 网页元素、动作选择、工具/agent 安全与步骤判断 |
| ambiguity_abstention | 2,000 | 歧义、不可回答、域外请求、可行性与拒答边界 |
| **合计** | **24,000** | |

## 44 个 family

### rule_policy_dependency（12）

`ruletaker`、`PARARULE-Plus`、`FOL-nli`、`folio`、`logical-entailment`、`conceptrules_v2`、`naturallogic`、`probability_words_nli/reasoning_1hop`、`probability_words_nli/reasoning_2hop`、`maud/bringdown-timing`、`maud/ordinary-course-consent`、`maud/specific-performance`

### table_ledger_filter（3）

`tabfact`、`infotabs`、`equate`

### state_time_order（13）

`babi_nli/time-reasoning`、`babi_nli/counting`、`babi_nli/lists-sets`、`babi_nli/path-finding`、`babi_nli/two-supporting-facts`、`babi_nli/three-supporting-facts`、`babi_nli/size-reasoning`、`temporal-nli`、`tracie`、`scone`、`goal-step-wikihow/goal`、`goal-step-wikihow/step`、`goal-step-wikihow/order`

### grounding_multihop（7）

`wice`、`hover`、`doc-nli`、`squad-v2/answerability`、`faithdial/grounding`、`ragtruth/grounding`、`fever-evidence-related`

### agent_action（4）

`websrc/element`、`websrc/yesno`、`agent_action_safety`、`prm800k_dpo/step`

### ambiguity_abstention（5）

`clinc_oos/plus`、`cuad/answerability`、`quac/answerability`、`feasibilityQA`、`google_wellformed_query`

## 格式构成

| typed decision kind | 条数 |
|---|---:|
| choice | 21,419 |
| noul | 2,244 |
| score | 337 |

当前文件仍是 Tasksource/Jev 的单题 typed-decision 结构，尚不是 Kev 训练器最终使用的 `state + questions[]` 记录。

## 独立审计结果

2026-11-05 对成品逐行重新解析并独立计算：

- JSON 解析失败：0
- 缺失必需字段：0
- 空 state/question：0
- 重复 ID：0
- 重复 selection digest：0
- 重复精确内容键：0
- choice/score 选项与 target 长度异常：0
- choice/score target 概率和不为 1：0
- noul target 越界：0
- 来源、能力组和 kind 计数与 manifest 不一致：0
- 非 `train` split：0
- 非 `commercial` license use：0

## 许可证筛查说明

最初选择的 60 个 Tasksource ID 在当前 Tasksource 目录中全部存在，但许可证元数据分布为：

- commercial：30
- unspecified：24
- non-commercial：6

为避免把限制用途或许可证不明确的数据静默混入正式训练，本次 24K 没有直接沿用原 60 项，而是改为 44 个均被 Tasksource 标记为 `commercial` 的 family。

明确排除的 non-commercial 项：`ConTRoL-nli`、`contract-nli/contractnli_a/seg`、`contract-nli/contractnli_b/full`、`logiqa-2.0-nli`、`weblinx/action`、`weblinx/dom-element`。

## 尚未完成（不能直接开训）

1. 将单题 typed rows 合并/转换为 Kev `state + questions[]` 格式。
2. 与 Kev corpus 及其他 v2 组件做跨组件去重。
3. 对 DecisionPivot 和七套冻结评测集做污染检查。
4. 使用固定的 Qwen3.8-27B tokenizer 做上下文长度准入。
5. 再验 hard/soft target、异常标签和被截断样本。
6. 固定 train/development 划分与最终排序，并生成新的哈希清单。

因此当前状态为：`candidate_not_train_ready`。
