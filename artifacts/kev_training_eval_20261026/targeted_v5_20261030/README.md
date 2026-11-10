# 七类定向续训 v5

**终态更新：两模型训练、全部评测及训练集probe均完成，七类改善目标未达成。**完整原始预测/报告/实际远端训练代码见`evidence/`，44个归档文件hash已校验；下文训练中描述为历史。

七类合计Qwen3 512→513/1000（+0.1pp），Qwen3.5 551→579/1000（+2.8pp）。详见`七类结果.md`、`comparison-seven.json/.csv`、`paired-seven.jsonl`、`all_seven_mechanism_diagnostics.json`。Qwen3概率/信息不足/多跳退步，Qwen3.5时间/概率/政策退步；不应按总体分数宣布成功。

成对题诊断见`development_pair_diagnostics.json`：信息不足的决定变量对照，两题都对的组数Q3 4→7/28，Q3.5 6→17/28；政策整对全部子题正确仍非常少（Q3所有30对均未全对，Q3.5仅3/30）。这是更严格的成组指标，不可与单题准确率混用。

训练集抽样见`train_probe_comparison.json`。Q3概率9→12/35、政策12→16/40、多跳5→7/20；Q3.5为9→15/35、11→24/40、5→11/20。新增复杂题尚未充分学会，但小样本probe本身不能证明增加epoch一定改善真实题。

后续固定数据对照已准备于`../targeted_v5_3ep_20261030/`：只把epoch从1改为3（OneCycleLR按总步数伸长），仍原stage3初始化，保留原数据和其他参数，不接续v5权重。新多跳覆盖候选180/330子题尚未加入；原三类语义问题亦未在冻结v5中修改。运行状态必须查看新目录run_status与远端进程。

状态：已生成并通过题面复算，2026-10-30 05:17北京时间，两模型已完成分词预检和开发集基线，正在训练。实时情况必须检查远端进程和日志，不能将本文件视为持续存活证明。尚无训练后效果结论。

规模为1500定向情境/2055子题，另6000回放；总7500情境/9481子题（增强前）。开发340情境/440子题。训练和开发均没有因长度被过滤。模型从原stage3开始，1 epoch、lr1e-5、LoRA16+head、batch4/accum2、seed101，原v4/v2选项增强。没有从v4权重继续训练。本轮保持优化设置不变，评估数据修订的效果。

| 类别 | 训练情境 | 本轮变化 |
|---|---:|---|
| 概率 |350|增加反向条件覆盖；选项包含条件方向、基率、补集及附近数值等更可信的错误答案|
| 信息不足 |280|140对相同情境有/缺一个事实的样本，其中112个未知答案，占40%；另有缺失不改变结论的对照|
| 多跳 |270|软/硬依赖与部分候选判断、等级条件升级、控制权链|
| 长政策 |300|150对运算顺序、边界条件和多重拒赔原因对照；180正赔付、120零赔付|
| 工具路由 |100|v4原记录保留|
| 时间数值 |100|v4原记录保留|
| 提示注入 |100|v4原记录保留|

四类新训练1200条已用另一份计算实现从可见文字重算；每条构造一个错误选择标签，检查器均拒绝。所有记录通过Kev materialize；开发与训练无相同归一化题面，与已检查官方冻结test无相同题面。成对样本不跨split。原三类train/development记录与v4逐对象一致。检查不等于外部独立审阅，也不证明语义独立泛化。

v4概率百分比题275道全部只有至多两个非25%整倍数选项，通常为正确数值与补集，可能提供形式捷径；v5已扩充其他合理计算结果。不能据此宣称已证明v4退步原因。

后续只读审计发现保留的时间数据中，train28条、development12条退款题使用“through结束日”，标签却按结束日不计入计算。详见`retained_temporal_audit.json`。题面有日期边界歧义；为遵守“三类不改”，本轮没有修改这些记录，已询问用户是否允许后续仅修正文案。不要将该问题解释为已证明的因果结论。时区题未发现重复/不存在的本地时间。

远端：`/C20545/kev-08b-official-repro-20261026/runs/qwen3-20261030-targeted-v5`与`runs/qwen35-20261030-targeted-v5`。pipeline会在训练后自动评开发、hard-v1、devtools-v1。比较时报告全部七类，并单独报告未知题和成对题全部答对率，不能只看总体分数。hard-v1已用于诊断，结果不属于未见测试；单种子不能证明稳定性。

文件：train.jsonl、development.jsonl、manifest.json、validation.json、paired_examples.md、retained_temporal_audit.json、launch_qwen3.sh、launch_qwen35.sh、preflight.py、evaluate_development.py、run_status.json。生成工具`tools/build_targeted_v5.py`；评测汇总使用`tools/summarize_targeted_v4.py --run-version v5 --data-dir artifacts/kev_training_eval_20261026/targeted_v5_20261030`；成对诊断`tools/diagnose_targeted_v5_pairs.py`。训练效果目标仍未达成。
