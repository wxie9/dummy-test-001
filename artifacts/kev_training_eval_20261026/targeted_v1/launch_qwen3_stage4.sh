#!/usr/bin/env bash
set -euo pipefail

ROOT=/C20545/kev-08b-official-repro-20261026
cd "$ROOT/stages/stage3"
exec env CUDA_VISIBLE_DEVICES=1 "$ROOT/python.sh" -m kev.train \
  --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \
  --perm_kl 0.0 --perm_frac 0.3 --ord_w 0.0 \
  --p_none 0.1 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \
  --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \
  --dtype bf16 --checkpointing 1 --replay 6000 --max_state 7552 \
  --data "$ROOT/targeted_v1/train.jsonl" \
  --base /C20545/models/Qwen3-0.6B-Base \
  --base_revision local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba \
  --init_from "$ROOT/runs/qwen3-06b-20261026/stage3" \
  --suite "$ROOT/evals/v7/decision-v7" \
  --out "$ROOT/runs/qwen3-06b-20261028-targeted-v1/stage4" \
  --device cuda
