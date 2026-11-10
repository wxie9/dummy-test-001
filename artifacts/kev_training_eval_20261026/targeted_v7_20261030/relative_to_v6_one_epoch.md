# 与 targeted_v6_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|54/150|53/150|-0.67|4/5|
|qwen3|temporal|49/117|46/117|-2.56|1/4|
|qwen3|probability|85/158|81/158|-2.53|2/6|
|qwen3|insufficient|61/100|65/100|+4.00|8/4|
|qwen3|multihop|55/125|54/125|-0.80|2/3|
|qwen3|policy|116/200|117/200|+0.50|4/3|
|qwen3|injection|89/150|95/150|+4.00|7/1|
|qwen35|tool_routing|52/150|54/150|+1.33|5/3|
|qwen35|temporal|49/117|46/117|-2.56|2/5|
|qwen35|probability|84/158|82/158|-1.27|5/7|
|qwen35|insufficient|70/100|68/100|-2.00|6/8|
|qwen35|multihop|83/125|84/125|+0.80|3/2|
|qwen35|policy|135/200|135/200|+0.00|4/4|
|qwen35|injection|112/150|110/150|-1.33|0/2|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
