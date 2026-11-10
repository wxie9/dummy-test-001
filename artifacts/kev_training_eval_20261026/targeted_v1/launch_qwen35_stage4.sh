#!/usr/bin/env bash
set -euo pipefail

ROOT=/C20545/kev-08b-official-repro-20261026
cd "$ROOT/stages/stage3"
exec env CUDA_VISIBLE_DEVICES=2 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 "$ROOT/python.sh" -m kev.train \
  --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \
  --perm_kl 0.0 --perm_frac 0.3 --ord_w 0.0 \
  --p_none 0.1 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \
  --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \
  --dtype bf16 --checkpointing 1 --replay 6000 --max_state 7552 \
  --data "$ROOT/targeted_v1/train.jsonl" \
  --base Qwen/Qwen3.5-0.8B-Base \
  --base_revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --init_from "$ROOT/runs/replica-20261026/stage3" \
  --suite "$ROOT/evals/v7/decision-v7" \
  --out "$ROOT/runs/replica-20261028-targeted-v1/stage4" \
  --device cuda
