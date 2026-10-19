# 评测协议

复制 [评测协议模板](../templates/evaluation-protocol.md) 到 `<B-ID>/v1.0.0.md`，固化可比较的测试条件：数据集与 split、prompt、chat template、few-shot 示例、解码参数、指标实现、聚合方式和资源约束。

改变会影响分数的条件时创建新版本，报告中区分不同协议的结果。每次实际执行保存在 [评测运行](../experiments/evaluation/README.md)，不在协议中填写虚构分数。

采用外部评测框架时记录其精确版本/commit 与任务配置；不能只写一个 benchmark 名称。测试集用于最终评估的边界、污染检查和调参限制也写入协议。
