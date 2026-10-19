# LLM 代码与评测验证

当前没有训练/评测代码。仓库大小策略已有标准库 unittest 回归测试，可用 `python3 -m unittest discover -s tests -p 'test_*.py' -v` 运行。加入训练/评测实现时再按实际框架选择测试与冒烟验证方式。

验证应覆盖会影响训练或分数的逻辑，例如数据 split 与去重、tokenization、label/padding mask、训练配置解析、checkpoint 加载、prompt 构造、答案解析、指标聚合和失败条目计分。训练/评测入口使用小型 fixture 做冒烟验证；涉及 GPU 时记录实际设备与未验证范围。

小型可共享数据放 `tests/fixtures/`，标明来源与预期结果；虚构数据明确标记，不能混入真实 benchmark 结果。

纯文档与模板变更检查相对链接、字段一致性和 `git diff --check`，不把文档检查称为训练或评测通过。
