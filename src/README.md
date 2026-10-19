# LLM 训练与评测代码

保存 Python 实现，按需组织 `data/`、`training/`、`evaluation/` 和公共组件，避免逐份复制完整训练代码。具体训练框架、包结构和依赖随首个任务确定，目前没有默认入口或安装命令。

记录输入、输出和异常情况；新增数据处理、训练或计分逻辑时在 [tests/](../tests/README.md) 加入适当验证。启动入口放 [scripts/](../scripts/README.md)，配置放 [configs/](../configs/README.md)，具体执行保存到 [实验记录](../experiments/README.md)。
