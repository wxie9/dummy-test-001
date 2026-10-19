# 计算运行记录

每次运行复制 [计算运行模板](../../templates/computational-run.md) 到 `<R-ID>/record.md`。配置可放同目录的小型文本文件，大型输出使用外部存储。

运行前确认代码 commit、工作区、输入数据版本、配置和环境。运行后补充实际命令、退出码、日志、产物与验证结果。重跑建立新 R-ID；`completed` 表示记录完成，结果字段单独填写。

可复用实现放 [src/](../../src/README.md)，探索放 [notebooks/](../../notebooks/README.md)，正式多步骤流程放 [workflows/](../../workflows/README.md)。各类代码均关联生成结果的运行记录。
