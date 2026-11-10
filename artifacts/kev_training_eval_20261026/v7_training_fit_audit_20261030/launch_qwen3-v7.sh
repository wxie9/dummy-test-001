#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/v7_training_fit_audit_20261030"
test ! -e "$DATA/qwen3-v7"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$DATA/qwen3-v7.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=2 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
printf 'evaluating\n' > "$DATA/qwen3-v7.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "/C20545/kev-08b-official-repro-20261026/runs/qwen3-20261030-targeted-v7/stage4" "$DATA/train_eval.jsonl" "$DATA/qwen3-v7"
printf 'complete\n' > "$DATA/qwen3-v7.status.txt"
