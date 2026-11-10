# 与 targeted_v7_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|53/150|56/150|+2.00|7/4|
|qwen3|temporal|46/117|46/117|+0.00|3/3|
|qwen3|probability|81/158|87/158|+3.80|7/1|
|qwen3|insufficient|65/100|66/100|+1.00|2/1|
|qwen3|multihop|54/125|58/125|+3.20|5/1|
|qwen3|policy|117/200|116/200|-0.50|3/4|
|qwen3|injection|95/150|95/150|+0.00|0/0|
|qwen35|tool_routing|54/150|53/150|-0.67|1/2|
|qwen35|temporal|46/117|45/117|-0.85|3/4|
|qwen35|probability|82/158|85/158|+1.90|5/2|
|qwen35|insufficient|68/100|66/100|-2.00|0/2|
|qwen35|multihop|84/125|84/125|+0.00|1/1|
|qwen35|policy|135/200|137/200|+1.00|3/1|
|qwen35|injection|110/150|112/150|+1.33|2/0|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
