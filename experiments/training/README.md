# 训练运行

每次训练复制 [训练模板](../../templates/training-run.md) 到 `<TR-ID>/record.md`。配置放 [configs/](../../configs/README.md)，通用实现放 [src/](../../src/README.md)，启动脚本放 [scripts/](../../scripts/README.md)。

记录执行时 commit、代码工作区状态、模型/tokenizer revision、训练与验证 split、实际超参数、随机种子、硬件和软件环境。恢复训练需要关联源 checkpoint、恢复 step 和优化器状态。

日志、checkpoint 和大文件存外部共享位置，登记 [checkpoint 表](../../metadata/checkpoints.tsv)。记录“执行完成”和“结果支持假设”是两件事；日志文档的提交不是执行时的代码版本。
