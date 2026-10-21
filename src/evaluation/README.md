# 外部评测器

本目录以 Git 子模块固定公开的上游评测实现，不复制其代码、题目、权重或运行产物。

| 目录 | 上游 | 固定提交 | 数据边界 |
| --- | --- | --- | --- |
| `decision-index/` | [apolinario/decision-index](https://github.com/apolinario/decision-index) | `25c6ec7b6b5f44a216c63c3a700de3a9c6d6699d` | 仅公开 0.3 suite；构建数据保留在仓库外。 |
| `decisionpivot/` | [StartLuxLabs/DecisionPivot](https://github.com/StartLuxLabs/DecisionPivot) | `2b7000f312ccbbdce4e8625b56d8a8186ea0047a` | Core 可重建；Reference 固定独立的 HF 数据 revision，运行前核对许可与访问条件；均仅可评测。 |
| JevBench（仓库外 checkout） | [fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench) | `609a664e81f46e03731600bd7bd9f1b7a61257c5` | 仅 `datasets/public/` 的 original/easy/hard 共 231 题（manifest 标识 v1.2）；不代表 v1.6 完整榜单。上游较大，按需在仓库外克隆并 checkout 此提交；详见 [协议与命令](../../benchmarks/B-20261021-CHENZW-004/v1.0.0.md)。 |

克隆本仓库后，按需执行 `git submodule update --init --recursive`。具体数据版本、接口与计分条件见 `benchmarks/` 下的 B-ID 协议；实际运行另建 `experiments/evaluation/EV-ID/` 记录。

JevBench 不在 `.gitmodules` 中，以上子模块命令不会创建 `src/evaluation/jevbench`。其外部 checkout 路径、依赖环境和运行输出位置由实际 EV 记录固定；本次协议登记没有克隆题目或执行模型。
