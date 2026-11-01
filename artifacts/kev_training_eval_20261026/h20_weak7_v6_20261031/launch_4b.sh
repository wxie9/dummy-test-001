#!/bin/bash
set -euo pipefail
cd /data/kev
export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
/data/kev/.venv/bin/python -u -m kev.train \
  --suite evals/v7/decision-v7 \
  --data local_data/h20_weak7_v6_20261031/train_4b.jsonl --replay 6000 \
  --init_from runs/h20-4b-s4 \
  --base Qwen/Qwen3.5-4B-Base --base_revision 1001bb4d826a52d1f399e183466143f4da7b741b \
  --epochs 1 --lr 1e-5 --head_lr 0 --weight_decay 0.01 --lora 16 \
  --batch 2 --accum 4 --dtype bf16 --weights_dtype fp32 --checkpointing 1 \
  --p_none 0.10 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --max_state 7552 --seed 101 --device cuda \
  --out runs/h20-4b-weak7-v6-20261031
