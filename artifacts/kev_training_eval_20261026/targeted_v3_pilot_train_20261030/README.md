# Kev v3 小样本一轮试训（2026-10-30）

用户授权先用审阅题试训。全部68条新情境，加原三类各20条训练记录，128情境/154子题，原始行不改。只跑1 epoch、16次优化更新；LoRA与pointer head均从原stage3加载，学习率1e-5。没有接续v1/v2的stage4。

不额外混入6000条replay，不重复新题，关闭None/干扰选项增强。与v2存在数据量和训练配比差异，因此只作小规模试训，不声称是严格的仅换数据对照。

两模型分别使用GPU1、2。先用各自分词器确认全部128条能装入训练上下文；任何过滤都会终止。然后训练并保存，最后自动评测固定hard-v1。日志在远端数据目录的pipeline-qwen3.log / pipeline-qwen35.log；每个run有status.txt、preflight.json、stage4/和eval-hard-v1/。

hard-v1已参与错误分析，只能作为已知诊断集修复指标。此批review题已用于训练，不能再称独立测试题。启动情况另见run_status.json。
