#!/usr/bin/env bash
set -Eeuo pipefail
cd /data/kev
root="local_data/h20_weak7_v6_20261031"
run="runs/h20-9b-weak7-v6-3ep-4gpu-20261031"
eval_root="${run}-eval"
test ! -e "$run"
test "$(sha256sum "$root/train_9b.jsonl" | cut -d ' ' -f 1)" = 4133171bdefe0a6d7a9c482f5680af4601f7cd41ee2cc2b6872227ab0c7c62fc
mkdir -p "$eval_root" logs
trap 'echo "$(date -Is) FAILED line=$LINENO model=9b" >> "$eval_root/status.log"' ERR
export CUDA_VISIBLE_DEVICES=2,3,4,5 HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
echo "$(date -Is) TRAIN_START model=9b world=4 gpu=2,3,4,5" >> "$eval_root/status.log"
/data/kev/.venv/bin/torchrun --standalone --nproc_per_node=4 -m kev.train \
  --suite evals/v7/decision-v7 \
  --data "$root/train_9b.jsonl" --replay 6000 \
  --init_from runs/h20-9b-s3 \
  --base Qwen/Qwen3.5-9B-Base --base_revision 68c46c4b3498877f3ef123c856ecfde50c39f404 \
  --epochs 3 --lr 1e-5 --head_lr 0 --weight_decay 0.01 --lora 16 \
  --batch 2 --accum 1 --dtype bf16 --weights_dtype fp32 --checkpointing 1 \
  --p_none 0.10 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --max_state 7552 --seed 101 --device cuda \
  --distributed_lora 1 --out "$run" \
  > logs/h20-9b-weak7-v6-3ep-4gpu-20261031.log 2>&1
test -f "$run/training_metrics.json"
echo "$(date -Is) TRAIN_DONE model=9b" >> "$eval_root/status.log"
export CUDA_VISIBLE_DEVICES=2
/data/kev/.venv/bin/python -u -m kev.benchmark \
  --run "$run" --suite "$root/devsuite_9b" \
  --out "${run}-dev-after" --device cuda \
  > logs/h20-9b-weak7-v6-3ep-4gpu-20261031-dev-after.log 2>&1
echo "$(date -Is) DEV_DONE model=9b" >> "$eval_root/status.log"
for pair in \
  decision-v7:evals/v7/decision-v7 \
  transfer-v4:evals/v4/transfer-v4 \
  transfer-v9:evals/v9/transfer-v9 \
  hard-v1:evals/hard-v1 \
  devtools-v1:evals/devtools-v1 \
  documents-v1:evals/documents-v1; do
  name="${pair%%:*}"
  suite="${pair#*:}"
  echo "$(date -Is) START $name" >> "$eval_root/status.log"
  /data/kev/.venv/bin/python -u -m kev.benchmark \
    --run "$run" --suite "$suite" --allow-test \
    --out "$eval_root/$name" --device cuda \
    > "$eval_root/$name.log" 2>&1
  echo "$(date -Is) DONE $name" >> "$eval_root/status.log"
done
echo "$(date -Is) ALL_DONE model=9b" >> "$eval_root/status.log"
