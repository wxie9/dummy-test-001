#!/bin/bash
set -euo pipefail
model="$1"
gpu="$2"
cd /data/kev
export CUDA_VISIBLE_DEVICES="$gpu" HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
run="runs/h20-${model}-weak7-v6-20261031"
root="runs/h20-${model}-weak7-v6-20261031-eval"
mkdir -p "$root"
for pair in \
  decision-v7:evals/v7/decision-v7 \
  transfer-v4:evals/v4/transfer-v4 \
  transfer-v9:evals/v9/transfer-v9 \
  hard-v1:evals/hard-v1 \
  devtools-v1:evals/devtools-v1 \
  documents-v1:evals/documents-v1; do
  name="${pair%%:*}"
  suite="${pair#*:}"
  echo "$(date -Is) START $name GPU=$gpu" >> "$root/status.log"
  /data/kev/.venv/bin/python -u -m kev.benchmark --run "$run" --suite "$suite" --allow-test --out "$root/$name" --device cuda > "$root/$name.log" 2>&1
  echo "$(date -Is) DONE $name" >> "$root/status.log"
done
echo "$(date -Is) ALL_DONE" >> "$root/status.log"
