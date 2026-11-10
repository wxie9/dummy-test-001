# 与 targeted_v6_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|54/150|52/150|-1.33|8/10|
|qwen3|temporal|49/117|49/117|+0.00|7/7|
|qwen3|probability|85/158|82/158|-1.90|3/6|
|qwen3|insufficient|61/100|64/100|+3.00|8/5|
|qwen3|multihop|55/125|60/125|+4.00|5/0|
|qwen3|policy|116/200|121/200|+2.50|9/4|
|qwen3|injection|89/150|88/150|-0.67|3/4|
|qwen35|tool_routing|52/150|50/150|-1.33|7/9|
|qwen35|temporal|49/117|54/117|+4.27|6/1|
|qwen35|probability|84/158|88/158|+2.53|12/8|
|qwen35|insufficient|70/100|73/100|+3.00|7/4|
|qwen35|multihop|83/125|83/125|+0.00|4/4|
|qwen35|policy|135/200|131/200|-2.00|2/6|
|qwen35|injection|112/150|103/150|-6.00|0/9|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
