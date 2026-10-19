# 训练与评测配置

按需创建 `training/` 和 `evaluation/`，保存可提交的配置文件。框架与启动入口确定后，配置必须与实际入口对应，不创建无法运行的示例配置。

- 训练配置记录：基础模型与 tokenizer revision、训练/验证数据版本、训练方式、超参数、随机种子、精度和分布式配置。
- 评测配置记录：checkpoint、评测集 split/revision、协议版本、prompt/chat template、解码参数、指标及评测工具版本。
- 配置仅保存非敏感参数；令牌、机器密码和个人绝对路径通过本地环境注入。

具体执行关联 [训练记录](../templates/training-run.md) 或 [评测记录](../templates/evaluation-run.md)，记录实际生效的配置、命令行覆盖与配置哈希。
