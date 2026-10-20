# 外部评测器

本目录以 Git 子模块固定公开的上游评测实现，不复制其代码、题目、权重或运行产物。

| 目录 | 上游 | 固定提交 | 数据边界 |
| --- | --- | --- | --- |
| `decision-index/` | [apolinario/decision-index](https://github.com/apolinario/decision-index) | `25c6ec7b6b5f44a216c63c3a700de3a9c6d6699d` | 仅公开 0.3 suite；构建数据保留在仓库外。 |
| `decisionpivot/` | [StartLuxLabs/DecisionPivot](https://github.com/StartLuxLabs/DecisionPivot) | `2b7000f312ccbbdce4e8625b56d8a8186ea0047a` | Core 可重建；Reference 需要受限数据访问；均仅可评测。 |
| JevBench（协议来源） | [fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench) | `609a664e81f46e03731600bd7bd9f1b7a61257c5` | 仅公开组成；密封题不进入本仓库。上游较大，按需从协议链接克隆。 |

克隆本仓库后，按需执行 `git submodule update --init --recursive`。具体数据版本、接口与计分条件见 `benchmarks/` 下的 B-ID 协议；实际运行另建 `experiments/evaluation/EV-ID/` 记录。
