#!/bin/bash
set -euo pipefail
model="$1"
gpu="$2"
cd /data/kev
root="local_data/h20_weak7_v6_20261031"
pid="$(cat "$root/$model.pid")"
run="runs/h20-${model}-weak7-v6-20261031"
while [[ ! -f "$run/training_metrics.json" ]]; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$(date -Is) TRAINING_FAILED model=$model; no training_metrics.json" >&2
    exit 1
  fi
  sleep 30
done
echo "$(date -Is) TRAINING_DONE model=$model"
export CUDA_VISIBLE_DEVICES="$gpu" HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
/data/kev/.venv/bin/python -u -m kev.benchmark \
  --run "$run" --suite "$root/devsuite_$model" \
  --out "runs/h20-${model}-weak7-v6-20261031-dev-after" --device cuda \
  > "logs/h20-${model}-weak7-v6-20261031-dev-after.log" 2>&1
echo "$(date -Is) DEV_AFTER_DONE model=$model"
bash "$root/evaluate_six.sh" "$model" "$gpu"
echo "$(date -Is) ALL_DONE model=$model"
