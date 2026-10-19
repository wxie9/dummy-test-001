# LLM 实验

- `plans/<E-ID>.md`：复制 [实验计划模板](../templates/experiment-plan.md)，说明研究问题、基线、变量、训练/评测预算与预先确定的判断标准。
- [training/](training/README.md)：每次训练的配置、环境、日志和 checkpoint 交接。
- [evaluation/](evaluation/README.md)：每次评测的输入模型、协议、原始输出、指标和解释。

一个实验计划可以关联多次训练与评测。每次重跑分配新运行 ID；失败与中断运行同样记录。按研究任务组织，不按成员复制整套训练代码。
