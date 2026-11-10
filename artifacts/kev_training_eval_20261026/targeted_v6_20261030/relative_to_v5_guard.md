# 与 targeted_v5_none_guard_candidate_20261030 的直接对照

|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|
|---|---|---:|---:|---:|---|
|qwen3|tool_routing|53/150|54/150|+0.67|6/5|
|qwen3|temporal|48/117|49/117|+0.85|3/2|
|qwen3|probability|83/158|85/158|+1.27|6/4|
|qwen3|insufficient|61/100|61/100|+0.00|2/2|
|qwen3|multihop|59/125|55/125|-3.20|2/6|
|qwen3|policy|118/200|116/200|-1.00|3/5|
|qwen3|injection|92/150|89/150|-2.00|0/3|
|qwen35|tool_routing|53/150|52/150|-0.67|4/5|
|qwen35|temporal|52/117|49/117|-2.56|3/6|
|qwen35|probability|86/158|84/158|-1.27|3/5|
|qwen35|insufficient|73/100|70/100|-3.00|1/4|
|qwen35|multihop|84/125|83/125|-0.80|6/7|
|qwen35|policy|130/200|135/200|+2.50|5/0|
|qwen35|injection|106/150|112/150|+4.00|6/0|

Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.
