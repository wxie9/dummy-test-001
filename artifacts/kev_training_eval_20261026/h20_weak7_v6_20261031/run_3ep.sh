#!/usr/bin/env bash
set -euo pipefail
model="$1"
gpu="$2"
cd /data/kev
case "$model" in
  4b)
    init="runs/h20-4b-s4"
    base="Qwen/Qwen3.5-4B-Base"
    revision="1001bb4d826a52d1f399e183466143f4da7b741b"
    ;;
  9b)
    init="runs/h20-9b-s3"
    base="Qwen/Qwen3.5-9B-Base"
    revision="68c46c4b3498877f3ef123c856ecfde50c39f404"
    ;;
  *) echo "Expected model 4b or 9b" >&2; exit 2 ;;
esac
root="local_data/h20_weak7_v6_20261031"
run="runs/h20-${model}-weak7-v6-3ep-20261031"
eval_root="${run}-eval"
log="logs/h20-${model}-weak7-v6-3ep-20261031.log"
mkdir -p "$eval_root" logs
export CUDA_VISIBLE_DEVICES="$gpu" HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
echo "$(date -Is) TRAIN_START model=$model gpu=$gpu" >> "$eval_root/status.log"
/data/kev/.venv/bin/python -u -m kev.train \
  --suite evals/v7/decision-v7 \
  --data "$root/train_${model}.jsonl" --replay 6000 \
  --init_from "$init" \
  --base "$base" --base_revision "$revision" \
  --epochs 3 --lr 1e-5 --head_lr 0 --weight_decay 0.01 --lora 16 \
  --batch 2 --accum 4 --dtype bf16 --weights_dtype fp32 --checkpointing 1 \
  --p_none 0.10 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --max_state 7552 --seed 101 --device cuda \
  --out "$run" > "$log" 2>&1
test -f "$run/training_metrics.json"
echo "$(date -Is) TRAIN_DONE model=$model" >> "$eval_root/status.log"
/data/kev/.venv/bin/python -u -m kev.benchmark \
  --run "$run" --suite "$root/devsuite_$model" \
  --out "${run}-dev-after" --device cuda \
  > "logs/h20-${model}-weak7-v6-3ep-20261031-dev-after.log" 2>&1
echo "$(date -Is) DEV_DONE model=$model" >> "$eval_root/status.log"
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
echo "$(date -Is) ALL_DONE model=$model" >> "$eval_root/status.log"
