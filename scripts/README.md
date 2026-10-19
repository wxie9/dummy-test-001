# 启动与工具脚本

保存数据准备、训练启动、分布式启动、评测启动和结果汇总入口。入口确定后，在此补充可运行命令、配置位置、环境要求和输出位置。

当前没有训练框架或默认训练命令，不预设 GPU 数量、模型名称、云平台或分布式方案。公共实现放 [src/](../src/README.md)，配置放 [configs/](../configs/README.md)，实际执行保存到 [实验记录](../experiments/README.md)。

[check_large_files.py](check_large_files.py) 是仓库基础检查，验证 Git 文件与新提交历史中的 10 MiB 上限；使用方式见 [自动检查说明](../docs/repository-checks.md)。
