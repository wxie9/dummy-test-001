# Evidence Log — 2026/11/05

Name: DecisionPivot 评测与 Kev v2 数据重建

> 状态：本地审阅稿，尚未同步飞书。
>
> 评测范围只包含 **DecisionPivot Core 1.1**。本文不混入六套 Kev 冻结测试，也不把官方模型卡数字冒充本地结果。

## 1. Last Meeting’s Actions

### 1.1 DecisionPivot 七层结果

| 层 | 能力范围 | Kev-27B v1 | SL Instant | SL−Kev |
|---|---|---:|---:|---:|
| A | 信息是否足够回答 | 63.7 | **95.3** | **+31.6** |
| B | 权限与政策守卫 | 46.0 | **91.8** | **+45.8** |
| C | 输出后事实核验 | 22.3 | **94.7** | **+72.4** |
| D | Agent循环与工具决策 | 45.6 | **65.6** | **+20.0** |
| E | 需要推理的分类 | 44.9 | **98.3** | **+53.4** |
| F | 数据记录与规则核验 | 60.4 | **71.1** | **+10.7** |
| G | 搜索与条件匹配 | 24.7 | **45.3** | **+20.6** |
| **七层平均** |  | **43.9** | **80.3** | **+36.4** |

### 1.2 DecisionPivot 13 个任务族

| 层 | 任务族 | Kev v1 | SL Instant | 差值 |
|---|---|---:|---:|---:|
| A | `answerable_facts` | 63.7 | **95.3** | +31.6 |
| B | `perm_inherit` | 34.7 | **83.7** | +49.0 |
| B | `policy_case` | 57.2 | **100.0** | +42.8 |
| C | `log_count_check` | 22.3 | **94.7** | **+72.4** |
| D | `sched_conflict` | 29.7 | **57.7** | +28.0 |
| D | `state_goal` | 43.0 | **80.7** | +37.7 |
| D | `toolcall_valid` | 85.0 | **88.3** | +3.3 |
| D | `triage_order` | 24.6 | **35.8** | +11.2 |
| E | `clause_change` | 56.0 | **96.9** | +40.9 |
| E | `dep_resolve` | 33.7 | **99.7** | **+66.0** |
| F | `ledger_reconcile` | 42.8 | **57.6** | +14.8 |
| F | `record_rule` | 78.0 | **84.7** | +6.7 |
| G | `filter_match` | 24.7 | **45.3** | +20.6 |

### 1.3 DecisionPivot 细分类差距（从高到低）

| 排名 | 细分类 | n | Kev | SL | 差距 |
|---:|---|---:|---:|---:|---:|
| 1 | 账本：批次总额错误 | 23 | 26.1% | 91.3% | **+65.2 pp** |
| 2 | 日志计数：实际声明正确 | 300 | 42.3% | 98.3% | **+56.0 pp** |
| 3 | 状态目标：相同性条件失败 | 28 | 35.7% | 89.3% | **+53.6 pp** |
| 4 | 记录规则：派生字段计算 | 40 | 35.0% | 85.0% | **+50.0 pp** |
| 5 | 事实判断：多表聚合后减法 | 40 | 50.0% | 100.0% | **+50.0 pp** |
| 6 | 依赖解析：Level 3复杂依赖闭包 | 200 | 50.5% | 100.0% | **+49.5 pp** |
| 7 | 政策判断：规则优先级 | 200 | 52.5% | 100.0% | **+47.5 pp** |
| 8 | 依赖解析：版本冲突 | 40 | 52.5% | 100.0% | **+47.5 pp** |
| 9 | 记录规则：字段依赖范围 | 40 | 57.5% | 97.5% | **+40.0 pp** |
| 10 | 日志计数：同时处理起止边界 | 240 | 61.3% | 99.6% | **+38.3 pp** |
| 11 | 依赖解析：排除式版本边界 | 56 | 62.5% | 100.0% | **+37.5 pp** |
| 12 | 状态目标：关键步骤缺失 | 75 | 49.3% | 86.7% | **+37.3 pp** |
| 13 | 依赖解析：依赖项缺失 | 156 | 62.8% | 100.0% | **+37.2 pp** |
| 14 | 权限继承：三层权限树 | 70 | 55.7% | 92.9% | **+37.1 pp** |
| 15 | 政策判断：四条例外规则 | 107 | 63.6% | 100.0% | **+36.4 pp** |
| 16 | 权限继承：角色链 | 34 | 55.9% | 91.2% | **+35.3 pp** |
| 17 | 依赖解析：包自身约束 | 156 | 67.9% | 99.4% | **+31.4 pp** |
| 18 | 分诊排序：类别优先级 | 99 | 68.7% | 100.0% | **+31.3 pp** |
| 19 | 状态目标：目标对象错误 | 75 | 49.3% | 80.0% | **+30.7 pp** |
| 20 | 依赖解析：运行时依赖 | 90 | 70.0% | 100.0% | **+30.0 pp** |
| 21 | 事实判断：Level 3四跳事实链 | 200 | 69.0% | 99.0% | **+30.0 pp** |
| 22 | 权限继承：Level 2 | 200 | 63.5% | 93.0% | **+29.5 pp** |
| 23 | 状态目标：步骤顺序交换 | 75 | 54.7% | 84.0% | **+29.3 pp** |
| 24 | 权限继承：Level 3 | 200 | 57.0% | 86.0% | **+29.0 pp** |
| 25 | 事实判断：两层继承链 | 80 | 71.2% | 100.0% | **+28.8 pp** |
| 26 | 依赖解析：普通版本边界 | 158 | 71.5% | 100.0% | **+28.5 pp** |
| 27 | 状态目标：数量条件失败 | 86 | 32.6% | 60.5% | **+27.9 pp** |
| 28 | 事实判断：继承关系推理 | 80 | 65.0% | 92.5% | **+27.5 pp** |
| 29 | 权限继承：作用域变化 | 66 | 66.7% | 93.9% | **+27.3 pp** |
| 30 | 权限继承：操作权限变化 | 67 | 68.7% | 95.5% | **+26.9 pp** |
| 31 | 排期冲突：设备条件 | 30 | 60.0% | 86.7% | **+26.7 pp** |
| 32 | 日志计数：差1条 | 75 | 64.0% | 90.7% | **+26.7 pp** |
| 33 | 账本核对：缺少条目 | 142 | 65.5% | 91.5% | **+26.1 pp** |
| 34 | 条款变化：条件范围外 | 167 | 71.9% | 97.6% | **+25.7 pp** |
| 35 | 状态目标：内容条件错误 | 179 | 74.9% | 100.0% | **+25.1 pp** |
| 36 | 政策判断：需要处理例外 | 200 | 75.0% | 100.0% | **+25.0 pp** |
| 37 | 账本核对：费用错误 | 24 | 8.3% | 33.3% | **+25.0 pp** |
| 38 | 条款变化：Level 3 | 200 | 75.5% | 100.0% | **+24.5 pp** |
| 39 | 权限继承：密封资源 | 33 | 57.6% | 81.8% | **+24.2 pp** |
| 40 | 条件筛选：k-of-n证书要求 | 42 | 71.4% | 92.9% | **+21.4 pp** |
| 41 | 账本核对：日期错误 | 57 | 22.8% | 43.9% | **+21.1 pp** |
| 42 | 排期冲突：座位容量 | 96 | 72.9% | 94.8% | **+21.9 pp** |
| 43 | 条件筛选：条件式规则 | 42 | 73.8% | 92.9% | **+19.0 pp** |
| 44 | 排期冲突：Level 3 | 200 | 51.0% | 70.0% | **+19.0 pp** |
| 45 | 条件筛选：换算后的最小值 | 42 | 59.5% | 76.2% | **+16.7 pp** |

### 1.4 完成 Kev v2 公开近似数据生成框架

已实现一套独立的数据生成代码：

`/Users/chen/Documents/ChatGPT/procogs/tools/kev_v2_data_generation/`

该框架不是复制官方私有数据，而是根据公开数量和能力描述做可复现的近似重建。核心约束如下：

- 规则生成器先确定标准答案；
- LLM 只负责改写语言表面、渲染长文档或生成候选回答；
- 使用 LLM 的 family 默认再调用模型做忠实性审核；
- 失败样本写入 rejected 文件，不静默进入训练集；
- 任务可恢复，已有稳定 index 不重复生成；
- API key 只从环境变量读取，不写入代码、manifest 或日志。

八个 synthetic family 的当前结果：

| Family | 目标数 | 当前接受 | 完成度 | 生成方式 | rejected | 状态 |
|---|---:|---:|---:|---|---:|---|
| abstention | 3,530 | 3,530 | 100% | 规则求解 | 0 | 完成 |
| intent | 4,848 | 4,848 | 100% | 规则标签 + LLM 表述 | 169 | 完成 |
| long_doc | 6,042 | 5,201 | 86.1% | 规则标签 + LLM 长文档 | 6,728 | **未完成，差 841** |
| numeric | 3,684 | 3,684 | 100% | 精确数值求解 | 0 | 完成 |
| retrieval | 2,772 | 2,772 | 100% | 程序控制证据位置 | 0 | 完成 |
| rubric_judge | 7,288 | 4,311 | 59.2% | 预设 winner + LLM 候选回答 | 23,816 | **未完成，差 2,977** |
| tool_routing | 5,514 | 5,514 | 100% | 工具能力状态机 | 0 | 完成 |
| hard_v1_extra | 6,000 | 6,000 | 100% | 规则政策 + LLM 渲染 | 12 | 完成 |
| **合计** | **39,678** | **35,860** | **90.4%** |  | **30,725** | **差 3,818** |

拒绝原因表明，未完成主要不是规则标签冲突，而是 API 批次失败：

- `long_doc`：6,657 次 `batch_api_failed`，65 次 LLM 忠实性审核失败，6 次 materialization 失败；
- `rubric_judge`：23,780 次 `batch_api_failed`，35 次 LLM 忠实性审核失败，1 次 materialization 失败；
- 已完成的 `intent` 和 `hard_v1_extra` 也分别拒绝了 169 和 12 条未通过忠实性审核的输出。

当前生成文件位于：

`/data/kev-v2-public-reconstruction-20261104/generated/`

### 1.5 完成 Pivot 定向 Tasksource 24K 候选集

从公开 `tasksource/tasksource-jev-typed-decisions` 的 `full` 配置中，完成了一个面向 DecisionPivot 薄弱能力的 24,000 条确定性抽样候选集。

| 能力组 | 数量 | 对应 Pivot 能力 |
|---|---:|---|
| rule_policy_dependency | 7,000 | 规则链、权限、政策与依赖解析 |
| table_ledger_filter | 4,500 | 表格、账本、过滤与结构化事实 |
| state_time_order | 4,000 | 状态变化、时间顺序与步骤维护 |
| grounding_multihop | 4,000 | 证据支持、可回答性与多跳归因 |
| agent_action | 2,500 | 网页元素、动作选择与 agent 安全 |
| ambiguity_abstention | 2,000 | 歧义、域外请求和拒答边界 |
| **合计** | **24,000** | |

审计结果：

- 44 个 Tasksource family；
- 24,000 行全部可解析；
- 全部来自原始 `train` split；
- 全部标记为 `license_use=commercial`；
- ID、抽样摘要和精确内容均无重复；
- 选项、target 长度、离散概率和连续目标范围无异常；
- SHA-256：`f71e19e14c1aadb4ccc6bec17a92c53a65abe7a3ec9b05638797da56d9757133`。

远端文件：

`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource_pivot_commercial_24k_typed.jsonl`

这 24K 是我们的 Pivot 定向重建，不是 Kev 官方私有的 Tasksource 24K。官方使用的 119 个 family、精确抽样行和最终顺序没有公开。

## 2. Blockers

### 2.1 synthetic 数据尚缺 3,818 条

`long_doc` 尚缺 841 条，`rubric_judge` 尚缺 2,977 条。当前没有生成进程在运行。现有 rejected 记录中绝大多数是 API batch 失败，因此下一次续跑应先确认 API 可用性、速率和返回格式，再从缺失 index 恢复；不能把 rejected 行直接补进数据集。

### 2.2 生成完成不等于可以开训

当前 synthetic 35,860 条和 Tasksource 24K 都是候选数据。正式混合前仍缺：

1. 将 Tasksource 单题 typed-decision 转成 Kev `state + questions[]` 格式；
2. 对 synthetic、Tasksource、Kev corpus 其他来源做跨组件去重；
3. 对 DecisionPivot Core、七套冻结评测和其他 held-out 集做污染检查；
4. 用固定的 Qwen3.8-27B tokenizer 做长度准入；
5. 抽查 LLM 渲染是否保留程序预设标签；
6. 固定训练/开发划分、顺序与最终 SHA。

### 2.3 不能声称复现官方 Kev v2 数据

官方 `sft-v2-r22` 共 145,840 条，但精确 `train.jsonl`、Tasksource 的 119-family 清单、若干生成组件的逐行结果、跨 partition 去重和污染筛查实现均未公开。

因此当前工作只能称为“公开信息约束下的 Pivot 定向近似重建”，不能称为官方 Kev v2 数据复现，也不能期待匹配官方训练 SHA。

## 3. Decisions / Learnings

### 3.1 下一轮数据不应平均覆盖所有能力，而应优先补 Pivot 的结构弱项

Kev-27B v1 相对 StartLux Instant 的主要差距集中在：

- `triage_order`；
- `ledger_reconcile`；
- `filter_match`；
- `log_count_check`；
- `sched_conflict`；
- `dep_resolve`。

对应的数据优先级应是：

1. Tasksource 的 `table_ledger_filter`、`state_time_order`、`rule_policy_dependency`；
2. synthetic 的 `tool_routing`、`numeric`、`retrieval` 与 `hard_v1_extra`；
3. 用成对反事实样本训练“只改变一个决定性字段时答案如何变化”，而不是只增加同标签改写。

### 3.2 StartLux Instant 的优势不只是模型更大，而是训练覆盖更贴合 Pivot

同为 27B，StartLux Instant 的七层分为 80.3，Kev-27B v1 为 43.9。差距在日志计数、依赖解析、权限与政策守卫等结构任务上尤其大。

这支持的结论是：Kev 当前数据主要强化一般决策读出和若干定向能力，但没有形成 StartLux 那种围绕成对反事实、七层结构和按置信度触发推理的训练覆盖。它不支持“只把 Kev 数据量加大就会自动追平 StartLux”的说法。

## 4. Next Meeting — New Actions

1. **完成缺失生成**：从稳定 index 恢复 `long_doc` 841 条和 `rubric_judge` 2,977 条；完成后重新计算 manifest、SHA 和 rejected 分布。
2. **构建 Pivot 定向训练混合**：把 Tasksource 24K 转成 Kev 格式，与 synthetic 数据按能力组配比，而不是简单全量拼接。
3. **先做污染和长度门禁**：在任何训练启动前，完成 DecisionPivot/七套测试污染筛查、跨组件去重和 Qwen3.8-27B tokenizer 预检。
4. **冻结一个独立开发集**：开发题不得来自 DecisionPivot Core 题面或其近邻模板；DecisionPivot 只用于最终回测。
5. **做最小消融**：至少比较 `Tasksource-only`、`synthetic-only`、`Tasksource+synthetic` 三组，并固定训练步数、基座、随机种子和 replay 比例。
6. **报告停止条件**：如果 Pivot 总体不升，或 `toolcall_valid`/`triage_order` 等关键 family 明显下降，则不继续扩大 epoch，也不晋升 checkpoint。

## 5. Evidence and Provenance

### DecisionPivot

- DecisionPivot 仓库 commit：`fd57688f033864e64c452561ffdfcba9739d1811`
- H20 Kev-27B v1 评分：`/data/kev/benchmarks/DecisionPivot/kev_eval/results/27b-v1/`
- H20 StartLux Instant 评分：`/data/kev/benchmarks/DecisionPivot/startlux_eval/results/27b-instant/`
- 两个模型的逐题结果：对应 `runs/27b-v1/` 和 `runs/27b-instant/` 目录。

### 数据生成

- 生成代码：`/Users/chen/Documents/ChatGPT/procogs/tools/kev_v2_data_generation/`
- synthetic 输出：`/data/kev-v2-public-reconstruction-20261104/generated/`
- Tasksource 24K：`/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/`
- Tasksource 本地说明：`/Users/chen/Documents/ChatGPT/procogs/artifacts/kev_training_eval_20261026/tasksource_pivot_reconstruction_20261105/README.md`

### 证据等级

- DecisionPivot 表格：本地实际运行结果，可回溯到 `scores.json`、`report.txt` 和逐题输出。
- synthetic 数量：远端 manifest、JSONL 行数和 rejected 行数交叉核对。
- Tasksource 24K：成品逐行独立审计并重算 SHA。
- 对官方 Kev v2 数据构成的判断：来自公开 manifest/模型卡与本地文件核对；私有逐行数据不可验证。

