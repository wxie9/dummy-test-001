#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/targeted_three_20261031"
OUT="$ROOT/runs/qwen35-20261031-targeted-three-fit-diagnostic"
test ! -e "$OUT"
mkdir -p "$OUT"
export HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/stages/stage3"

(
  export CUDA_VISIBLE_DEVICES=1
  "$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" \
    "$ROOT/runs/replica-20261026/stage3" "$DATA/train.jsonl" "$OUT/before-train"
  "$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" \
    "$ROOT/runs/replica-20261026/stage3" "$DATA/development.jsonl" "$OUT/before-development"
  printf 'complete\n' > "$OUT/before-status.txt"
) > "$OUT/before.log" 2>&1 &
before_pid=$!

(
  export CUDA_VISIBLE_DEVICES=2
  "$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" \
    "$ROOT/runs/qwen35-20261031-targeted-three-pure-e1/stage4" "$DATA/train.jsonl" "$OUT/after-train"
  "$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" \
    "$ROOT/runs/qwen35-20261031-targeted-three-pure-e1/stage4" "$DATA/development.jsonl" "$OUT/after-development"
  printf 'complete\n' > "$OUT/after-status.txt"
) > "$OUT/after.log" 2>&1 &
after_pid=$!

printf '%s\n' "$before_pid" > "$OUT/before.pid"
printf '%s\n' "$after_pid" > "$OUT/after.pid"
wait "$before_pid"
wait "$after_pid"
printf 'complete\n' > "$OUT/status.txt"
