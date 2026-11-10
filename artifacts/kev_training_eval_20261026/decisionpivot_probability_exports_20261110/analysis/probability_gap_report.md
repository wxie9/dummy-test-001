# DecisionPivot 三模型概率差异分析

日期：2026-11-10  
模型：Kev 融合版、StartLux Instant、StartLux AutoThink  
题目：DecisionPivot Core 1.1，13 个任务族，共 7,800 题

## 1. 比较口径

同一道题的选项概率分布用总变差距离（Total Variation distance，TV）比较：

```text
TV(p, q) = 0.5 × Σ_i |p_i - q_i|
```

- `TV=0`：两套选项概率完全一致。
- `TV=1`：两套概率质量几乎完全放在不同选项上。
- `TV≥0.5`：记为明显概率分歧。
- `TV≥0.75`：记为强烈概率分歧。

为了与没有独立 `none_probability` 的 Kev 公平比较，主指标只使用正常候选选项内部归一化后的 `probabilities`，不把 StartLux 的 `none_probability` 加入 TV。Kev 源概率约保留四位小数，这会带来不超过约 0.0003 的概率和误差，不影响本报告的大差异结论。

## 2. 总体结果

| 比较 | 平均 TV | 中位 TV | P90 | TV≥0.50 | TV≥0.75 | 最终选项不同 |
|---|---:|---:|---:|---:|---:|---:|
| Kev 融合版 vs SL Instant | 0.263 | 0.149 | 0.719 | 1,671（21.42%） | 671（8.60%） | 2,096（26.87%） |
| Kev 融合版 vs SL AutoThink | 0.240 | 0.110 | 0.677 | 1,697（21.76%） | 356（4.56%） | 2,161（27.71%） |
| SL Instant vs SL AutoThink | 0.180 | 0.072 | 0.599 | 1,048（13.44%） | 354（4.54%） | 1,330（17.05%） |

Kev 与两种 StartLux 的选项分歧率都约为 27%。StartLux Instant 与 AutoThink 之间也有 17.05% 的题发生改选，说明 thinking 并非只做小幅概率校准。

## 3. 强烈分歧时谁更常正确

### TV ≥ 0.75

| 比较 | 强烈分歧题数 | A 独对 | B 独对 | 两者都错且选项不同 |
|---|---:|---:|---:|---:|
| Kev（A）vs SL Instant（B） | 671 | 42 | **589** | 40 |
| Kev（A）vs SL AutoThink（B） | 356 | 28 | **325** | 3 |
| SL Instant（A）vs SL AutoThink（B） | 354 | 134 | **213** | 7 |

Kev 与 StartLux 强烈分歧时，大部分是 StartLux 纠正了 Kev：Instant 在 671 题中独对 589 题（87.78%），AutoThink 在 356 题中独对 325 题（91.29%）。

但需要注意一个反向现象：在 **Instant 与 AutoThink 差异最大的前 100 题**中，Instant 独对 75 题、AutoThink 独对 25 题。即 AutoThink 整体准确率更高，但其最激烈的概率翻转反而更常破坏 Instant 已经答对的题；不能把“thinking 改得越多”简单解释为“越有帮助”。

## 4. 哪些任务族的概率差异最大

### Kev 融合版 vs SL Instant

| 任务族 | 平均 TV | P90 | TV≥0.50 | 改选题数 | Kev 独对 | SL 独对 |
|---|---:|---:|---:|---:|---:|---:|
| `ledger_reconcile` | **0.392** | 0.763 | 269 | 288 | 51 | 110 |
| `log_count_check` | **0.347** | 0.670 | 144 | 173 | 5 | 168 |
| `dep_resolve` | **0.344** | 0.953 | 185 | 186 | 1 | 185 |
| `policy_case` | **0.316** | 0.886 | 177 | 170 | 0 | 170 |
| `perm_inherit` | **0.307** | 0.771 | 160 | 184 | 26 | 158 |
| `triage_order` | 0.293 | 0.657 | 138 | 227 | 47 | 80 |
| `sched_conflict` | 0.274 | 0.664 | 121 | 222 | 68 | 154 |

差异最大的前 100 题中，`dep_resolve` 占 43 题，`policy_case` 占 31 题；这 100 题里 StartLux Instant 独对 99 题，Kev 独对 1 题。

### Kev 融合版 vs SL AutoThink

| 任务族 | 平均 TV | P90 | TV≥0.50 | 改选题数 | Kev 独对 | SL 独对 |
|---|---:|---:|---:|---:|---:|---:|
| `triage_order` | **0.400** | 0.719 | 294 | 323 | 6 | 313 |
| `ledger_reconcile` | **0.369** | 0.708 | 250 | 257 | 1 | 239 |
| `sched_conflict` | 0.276 | 0.734 | 174 | 207 | 17 | 190 |
| `filter_match` | 0.270 | 0.697 | 144 | 209 | 12 | 197 |
| `policy_case` | 0.266 | 0.753 | 145 | 170 | 13 | 155 |
| `log_count_check` | 0.240 | 0.517 | 68 | 187 | 27 | 160 |
| `perm_inherit` | 0.237 | 0.610 | 105 | 181 | 33 | 148 |

差异最大的前 100 题以 `policy_case` 最多（38题），其次是 `answerable_facts` 和 `clause_change`（各13题）。其中 AutoThink 独对85题、Kev独对14题、两者都错且选项不同1题。

### SL Instant vs SL AutoThink

| 任务族 | 平均 TV | P90 | TV≥0.50 | 改选题数 | Instant 独对 | AutoThink 独对 |
|---|---:|---:|---:|---:|---:|---:|
| `triage_order` | **0.413** | 0.803 | 289 | 310 | 12 | 286 |
| `ledger_reconcile` | **0.290** | 0.764 | 194 | 217 | 5 | 184 |
| `filter_match` | 0.221 | 0.551 | 85 | 169 | 25 | 144 |
| `sched_conflict` | 0.211 | 0.515 | 68 | 137 | 25 | 112 |
| `perm_inherit` | 0.185 | 0.560 | 76 | 95 | 56 | 39 |
| `log_count_check` | 0.178 | 0.466 | 47 | 58 | 44 | 14 |
| `record_rule` | 0.161 | 0.566 | 73 | 88 | 15 | 69 |

AutoThink 的主要整体收益集中在分诊排序、账本核对、条件筛选和排期冲突；但权限继承、日志计数和依赖解析中存在较多 Instant 独对、AutoThink 改错的反例。

## 5. 差异最大的具体题

### Kev 融合版 vs SL Instant

| 排名 | 题目 ID | 任务族 | TV | 标准答案 | Kev | SL Instant | 结果 |
|---:|---|---|---:|---|---|---|---|
| 1 | `state_goal:00201` | state_goal | 0.9997 | no | yes | no | SL独对 |
| 2 | `policy_case:00432` | policy_case | 0.9993 | approve | deny | approve | SL独对 |
| 3 | `policy_case:00394` | policy_case | 0.9993 | approve | escalate | approve | SL独对 |
| 4 | `policy_case:00309` | policy_case | 0.9982 | deny | escalate | deny | SL独对 |
| 5 | `policy_case:00266` | policy_case | 0.9981 | approve | deny | approve | SL独对 |
| 6 | `dep_resolve:00081` | dep_resolve | 0.9977 | yes | no | yes | SL独对 |
| 7 | `dep_resolve:00572` | dep_resolve | 0.9973 | yes | no | yes | SL独对 |
| 8 | `policy_case:00175` | policy_case | 0.9970 | deny | approve | deny | SL独对 |
| 9 | `policy_case:00446` | policy_case | 0.9965 | approve | deny | approve | SL独对 |
| 10 | `perm_inherit:00210` | perm_inherit | 0.9963 | yes | no | yes | SL独对 |

### Kev 融合版 vs SL AutoThink

| 排名 | 题目 ID | 任务族 | TV | 标准答案 | Kev | SL AutoThink | 结果 |
|---:|---|---|---:|---|---|---|---|
| 1 | `triage_order:00449` | triage_order | 0.9920 | K-4060 | K-3991 | K-4060 | SL独对 |
| 2 | `policy_case:00536` | policy_case | 0.9859 | escalate | deny | escalate | SL独对 |
| 3 | `policy_case:00281` | policy_case | 0.9825 | escalate | deny | escalate | SL独对 |
| 4 | `triage_order:00391` | triage_order | 0.9781 | K-4034 | K-3991 | K-4034 | SL独对 |
| 5 | `policy_case:00270` | policy_case | 0.9724 | escalate | deny | escalate | SL独对 |
| 6 | `policy_case:00474` | policy_case | 0.9577 | deny | approve | deny | SL独对 |
| 7 | `perm_inherit:00210` | perm_inherit | 0.9506 | yes | no | yes | SL独对 |
| 8 | `policy_case:00503` | policy_case | 0.9452 | approve | escalate | approve | SL独对 |
| 9 | `policy_case:00129` | policy_case | 0.9438 | escalate | escalate | approve | **Kev独对** |
| 10 | `policy_case:00436` | policy_case | 0.9361 | approve | escalate | approve | SL独对 |

### SL Instant vs SL AutoThink

| 排名 | 题目 ID | 任务族 | TV | 标准答案 | Instant | AutoThink | 结果 |
|---:|---|---|---:|---|---|---|---|
| 1 | `triage_order:00464` | triage_order | 0.9951 | R-1838 | R-1838 | R-1839 | Instant独对 |
| 2 | `triage_order:00426` | triage_order | 0.9941 | H-353 | H-353 | H-362 | Instant独对 |
| 3 | `state_goal:00201` | state_goal | 0.9939 | no | no | yes | Instant独对 |
| 4 | `triage_order:00117` | triage_order | 0.9928 | L-625 | L-625 | L-628 | Instant独对 |
| 5 | `triage_order:00019` | triage_order | 0.9924 | T-490 | T-490 | T-498 | Instant独对 |
| 6 | `clause_change:00022` | clause_change | 0.9896 | yes_only_B | yes_only_B | same | Instant独对 |
| 7 | `policy_case:00217` | policy_case | 0.9865 | deny | deny | approve | Instant独对 |
| 8 | `clause_change:00325` | clause_change | 0.9862 | same | same | yes_only_A | Instant独对 |
| 9 | `dep_resolve:00455` | dep_resolve | 0.9831 | yes | yes | no | Instant独对 |
| 10 | `log_count_check:00157` | log_count_check | 0.9820 | yes | yes | no | Instant独对 |

## 6. 文件说明

- `all_pairwise_question_gaps.csv`：全部 3×7,800 个配对题，含概率、TV、confidence差、标准答案和对错状态。
- `top100_per_pair.csv`：每组比较差异最大的100题。
- `top100_per_pair_detailed.jsonl`：上述300题的完整状态、问题和元数据。
- `task_summary.csv`：每组比较、每个任务族的统计。
- `top100_task_counts.csv`：每组前100题的任务族构成。
- `summary.json`：机器可读的总体结果和口径。

## 7. 结论

1. Kev 与 StartLux 的最大差距是结构化规则推理中的**高置信反向判断**，不是单纯置信度高低不同。
2. Kev 对 Instant 的首要分歧集中在依赖解析与政策规则；对 AutoThink 的首要分歧转向分诊排序和账本核对。
3. AutoThink 整体显著提高准确率，但它对 Instant 的极端翻转不是单调有益：最极端100题中75题是把 Instant 的正确答案改错。
4. 后续若做定向训练或置信度路由，不能只按 TV 大小选样本；应把“SL纠正Kev”和“thinking破坏Instant”分开建池。
