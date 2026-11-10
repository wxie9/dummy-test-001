# 与 targeted_v6_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|54/150|53/150|-0.67|3/4|
|qwen3|temporal|49/117|48/117|-0.85|0/1|
|qwen3|probability|85/158|85/158|+0.00|1/1|
|qwen3|insufficient|61/100|59/100|-2.00|0/2|
|qwen3|multihop|55/125|54/125|-0.80|0/1|
|qwen3|policy|116/200|115/200|-0.50|1/2|
|qwen3|injection|89/150|90/150|+0.67|1/0|
|qwen35|tool_routing|52/150|52/150|+0.00|0/0|
|qwen35|temporal|49/117|49/117|+0.00|0/0|
|qwen35|probability|84/158|84/158|+0.00|1/1|
|qwen35|insufficient|70/100|70/100|+0.00|1/1|
|qwen35|multihop|83/125|83/125|+0.00|0/0|
|qwen35|policy|135/200|135/200|+0.00|0/0|
|qwen35|injection|112/150|111/150|-0.67|0/1|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
