# 评测运行

每次评测复制 [评测模板](../../templates/evaluation-run.md) 到 `<EV-ID>/record.md`，关联精确 checkpoint/模型版本和 [评测协议](../../benchmarks/README.md)。

保存实际 prompt/chat template、tokenizer、few-shot、解码参数、指标与聚合方式、有效与失败条目数。原始预测、逐条分数和评测日志使用外部存储，记录版本与校验和。

比较结果时核查协议、split、上下文长度、工具版本和硬件等条件；不把不同条件下的分数直接视为模型能力提升。评测完成不等同于通过验收或支持假设。
