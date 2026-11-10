# 与 targeted_v7_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|53/150|50/150|-2.00|9/12|
|qwen3|temporal|46/117|45/117|-0.85|7/8|
|qwen3|probability|81/158|78/158|-1.90|10/13|
|qwen3|insufficient|65/100|60/100|-5.00|4/9|
|qwen3|multihop|54/125|57/125|+2.40|13/10|
|qwen3|policy|117/200|111/200|-3.00|6/12|
|qwen3|injection|95/150|88/150|-4.67|1/8|
|qwen35|tool_routing|54/150|55/150|+0.67|5/4|
|qwen35|temporal|46/117|49/117|+2.56|8/5|
|qwen35|probability|82/158|84/158|+1.27|12/10|
|qwen35|insufficient|68/100|65/100|-3.00|2/5|
|qwen35|multihop|84/125|81/125|-2.40|6/9|
|qwen35|policy|135/200|132/200|-1.50|5/8|
|qwen35|injection|110/150|103/150|-4.67|1/8|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
