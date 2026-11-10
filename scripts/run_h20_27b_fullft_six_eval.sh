#!/usr/bin/env bash
set -Eeuo pipefail

cd /data/kev

run="/data/kev/runs/h20-27b-v2-custom114627-fullft8-20261107/checkpoint"
root="/data/kev/runs/h20-27b-v2-custom114627-fullft8-20261107-eval-standard-20261108"
status="$root/status.log"

mkdir -p "$root"
: > "$status"

names=(decision-v7 transfer-v4 transfer-v9 hard-v1 devtools-v1 documents-v1)
suites=(evals/v7/decision-v7 evals/v4/transfer-v4 evals/v9/transfer-v9 evals/hard-v1 evals/devtools-v1 evals/documents-v1)
pids=()

for i in "${!names[@]}"; do
  name="${names[$i]}"
  suite="${suites[$i]}"
  (
    export CUDA_VISIBLE_DEVICES="$i"
    export HF_HUB_OFFLINE=1
    export HF_HOME=/data/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    echo "$(date -Is) START $name GPU=$i" >> "$status"
    /data/kev/.venv/bin/python -u -m kev.benchmark \
      --run "$run" --suite "$suite" --allow-test \
      --out "$root/$name" --device cuda \
      > "$root/$name.log" 2>&1
    echo "$(date -Is) DONE $name GPU=$i" >> "$status"
  ) &
  pids+=("$!")
done

printf '%s\n' "${pids[@]}" > "$root/worker_pids.txt"

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "$(date -Is) FAILED" >> "$status"
  exit 1
fi

echo "$(date -Is) ALL_DONE" >> "$status"
