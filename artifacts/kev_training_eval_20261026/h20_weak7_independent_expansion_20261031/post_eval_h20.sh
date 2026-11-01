#!/usr/bin/env bash
set -Eeuo pipefail

model="$1"
gpu="$2"
cd /data/kev
data_root="local_data/h20_weak7_independent_expansion_20261101"
case "$model" in
  4b) run="runs/h20-4b-weak7-neighborhood-expansion-e1-2gpu-20261101" ;;
  9b) run="runs/h20-9b-weak7-neighborhood-expansion-e1-4gpu-20261101" ;;
  *) echo "model must be 4b or 9b" >&2; exit 2 ;;
esac
eval_root="${run}-eval"
status="$eval_root/status.log"
test -f "$run/training_metrics.json"
trap 'echo "$(date -Is) POST_EVAL_FAILED line=$LINENO model='"$model"'" >> '"$status"'' ERR
export CUDA_VISIBLE_DEVICES="$gpu" HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
echo "$(date -Is) POST_EVAL_RESTART model=$model gpu=$gpu reason=normalize-development-variant-to-clean" >> "$status"
/data/kev/.venv/bin/python -u -m kev.benchmark \
  --run "$run" --suite "$data_root/devsuite_${model}" \
  --out "${run}-development-fixed" --device cuda \
  > "logs/$(basename "$run")-development-fixed.log" 2>&1
echo "$(date -Is) DEVELOPMENT_DONE model=$model" >> "$status"

for pair in \
  decision-v7:evals/v7/decision-v7 \
  transfer-v4:evals/v4/transfer-v4 \
  transfer-v9:evals/v9/transfer-v9 \
  hard-v1:evals/hard-v1 \
  devtools-v1:evals/devtools-v1 \
  documents-v1:evals/documents-v1; do
  name="${pair%%:*}"
  suite="${pair#*:}"
  echo "$(date -Is) START $name model=$model" >> "$status"
  /data/kev/.venv/bin/python -u -m kev.benchmark \
    --run "$run" --suite "$suite" --allow-test \
    --out "$eval_root/$name" --device cuda \
    > "$eval_root/$name.log" 2>&1
  echo "$(date -Is) DONE $name model=$model" >> "$status"
done
echo "$(date -Is) ALL_DONE model=$model" >> "$status"
