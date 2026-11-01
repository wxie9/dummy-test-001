#!/usr/bin/env bash
set -euo pipefail
model="$1"
validation="/data/kev/local_data/h20_weak7_v6_20261031/multigpu_validation"
case "$model" in
  4b) init="/data/kev/runs/h20-4b-s4"; base="Qwen/Qwen3.5-4B-Base"; revision="1001bb4d826a52d1f399e183466143f4da7b741b" ;;
  9b) init="/data/kev/runs/h20-9b-s3"; base="Qwen/Qwen3.5-9B-Base"; revision="68c46c4b3498877f3ef123c856ecfde50c39f404" ;;
  *) echo "Expected model 4b or 9b" >&2; exit 2 ;;
esac
cd "$validation"
export PYTHONPATH="$validation" CUDA_VISIBLE_DEVICES=2,3,4,5 HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
/data/kev/.venv/bin/torchrun --standalone --nproc_per_node=4 -m kev.train \
  --suite /data/kev/evals/v7/decision-v7 \
  --data "/data/kev/local_data/h20_weak7_v6_20261031/train_${model}.jsonl" --replay 6000 \
  --init_from "$init" --base "$base" --base_revision "$revision" \
  --epochs 1 --max_steps 20 --lr 1e-5 --head_lr 0 --weight_decay 0.01 --lora 16 \
  --batch 2 --accum 1 --dtype bf16 --weights_dtype fp32 --checkpointing 1 \
  --p_none 0.10 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --max_state 7552 --seed 101 --device cuda --distributed_lora 1 \
  --out "/data/kev/runs/h20-${model}-4gpu-smoke-20261031"
