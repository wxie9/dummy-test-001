# 事实表达对照：训练与评测已完成

保留 v6 的1500个情境、3440个子问和全部标签，只把信息不足中的140个情境（70组）改为句子表达；其余1360条不变。改写替换原条目，不增加样本数。三个原定保留类别全部不动。规则、事实、问题、ID及行顺序不变；配对情境仍相关，不能将其视为统计独立样本。

这份候选用于单独检验事实表达方式是否影响学习。30个开发情境的既有推理诊断显示Qwen3对表达敏感，但不能据此认定这种训练修改会提升效果。v6三轮训练没有使用这份数据；本对照单独从原stage3训练一轮。

## 已完成检查

- 140个改写情境均能精确恢复原文事实，问题和标签一致；问题字典顺序不变。
- 按场景、缺失类型、完整答案分层平衡两种表达；开发集保持原样，规范化题面交集为零。
- 使用服务器实际增强代码、seed101和三轮设置：三轮分别生成2182、2088、2172个定向变体；4122、4028、4112个子问。逐个比较的问题、选项顺序、标签、target和变体数完全相同。回放来源与记录顺序保持原样，因此未改变训练监督的标量分配。
- 两种模型的实际tokenizer均接受1500定向+6000回放记录，共10866子问；336个开发情境无拒绝。

这不意味着梯度相同，也不证明有效。2026-10-30 07:32:52启动单独的一轮对照，GPU3/4，pipeline8730/8731；从原stage3初始化，不接续任何定向续训checkpoint。利用空闲卡并行检验表达因素，同时等待原三轮对照；全部七类统一评测，不按类别选择不同checkpoint。启动时尚处于检查与训练前评测，最新状态以run_status.json和服务器进程为准。

## 证据

`manifest.json`记录状态和数据哈希；`changes.json`列出140条改写；`examples.json`展示七个信息不足场景；`preflight_qwen3.json`、`preflight_qwen35.json`和`augmentation_check.json`是服务器校验结果。

`validation-evidence.tar.gz` SHA256：`5a0f15537e83d497da389148846515efe161fb96c2ea501aac1a66e51ea93b85`。7个索引文件均逐一核验，原始日志和实际校验脚本保存在`evidence/`。


## Completed result

Both models completed training and evaluation. Qwen3: 512 to 504/1000; Qwen3.5: 551 to 584/1000. Compared with v6 one epoch: -5 and -1 correct. Earlier launch paragraphs are historical; current status is complete, goal unachieved. See comparison-seven.json and the Chinese results report.
