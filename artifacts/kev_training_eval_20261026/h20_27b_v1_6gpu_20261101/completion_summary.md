# Kev-27B v1 六卡训练完成

- 完成时间：2026-11-02 01:41 CST 前
- 远端 checkpoint：`/data/kev/runs/h20-27b-v1-b1v2-ddp6-20261101/`
- 远端日志：`/data/kev/logs/h20-27b-v1-b1v2-ddp6-20261101.log`
- 基座：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
- 数据：官方 B1-v2 重建，15,401 requested records，源文件 SHA-256 `fb86543b3baccb5aff9355065821e8481a083b874521637dc2f3a5cb06faa56a`
- 训练：LoRA rank 16，world size 6，batch 1，accum 1，1 epoch
- optimizer steps：2,567 / 2,567
- records seen：18,172（包括 none-pair 扩增后的实际训练 records）
- forward tokens：10,164,492
- rejected / truncated：0 / 0
- wall time：14,387.924 秒（3 小时 59 分 47.9 秒）
- 梯度范数：mean 6.352912，max 443.807129；2,157 steps 触发 clip
- peak device bytes：79,335,837,184
- 输出：adapter、head、tokenizer、config、metrics 均存在；逐文件远端 SHA 见 `remote_checkpoint_hashes.sha256`

本地只归档日志、配置、指标和哈希，没有复制 adapter 或其他大权重。`training_config.json` 与 `training_metrics.json` 的本地 SHA 与远端完全一致。

## v2 状态

官方 v2 所需 `evals/sft-v2-r22/train.jsonl` 在服务器本地和 `/mnt/kevtrain` 仍不存在。公开仓库只有 manifest；所需精确训练文件应为 145,840 records / 337,130 questions，SHA-256 `e73542a70413ba73d1b67d4365cf5210778805292de5d72268aefb3d9d6c4d0d`。因此没有停止 GPU 6–7，也没有启动近似 v2。
