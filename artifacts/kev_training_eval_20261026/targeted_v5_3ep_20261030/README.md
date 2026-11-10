# 固定 v5 数据的三轮训练对照

目的：v5一轮训练后的训练题抽样仍有较低正确率，检验增加训练暴露能否改善学习及真实题迁移。不能将启动实验当作已有收益。

与v5一轮相比，仅将epochs从1改为3；OneCycleLR随总步数从938延长至2814。原stage3初始化、lr1e-5、LoRA16+head、batch4/accum2、seed101、6000回放与选项增强均不变。不是从v5 stage4继续训练。

train.jsonl、development.jsonl、train_probe.jsonl与v5逐字节相同并已在远端校验：1500个定向情境/2055子题，开发340/440，训练题probe140/175。三轮重复学习不算新增题目。原三类中的日期歧义与工具路由问题保持不变，此实验不能被称为已修复这些问题。

两模型的三轮训练与全部评测现已完成。Qwen3七类合计512→525/1000，Qwen3.5为551→583/1000；概率两者持平，多跳与长政策仍下降。原pipeline PID100877/100878和训练PID103165/104246均已退出，不能按此前启动记录重启。完整对比见父目录v5_control_comparison_20261030.md及本目录七类结果.md。远端根`/C20545/kev-08b-official-repro-20261026`，run为`runs/qwen3-20261030-targeted-v5-3ep`、`runs/qwen35-20261030-targeted-v5-3ep`。流程自动预检、开发与probe基线、训练、开发after、hard-v1、devtools-v1、probe after。

验收仍看全部七类逐题前后变化、旧错修复与新增错，另看开发整对正确率及训练probe。hard-v1是已看过的诊断集，训练probe是已训练题，均不能替代独立泛化验证。目标仍未达成。

汇总工具支持`--data-dir artifacts/kev_training_eval_20261026/targeted_v5_3ep_20261030 --run-version v5-3ep`：tools/summarize_targeted_v4.py、tools/diagnose_targeted_v5_pairs.py、tools/summarize_targeted_v5_train_probe.py。
