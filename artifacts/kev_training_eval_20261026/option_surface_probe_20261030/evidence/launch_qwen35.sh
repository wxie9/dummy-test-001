#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/option_surface_probe_20261030"
export CUDA_VISIBLE_DEVICES=4 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/stages/stage3"
test ! -e "$DATA/qwen35-stage3"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/replica-20261026/stage3" "$DATA/probe.jsonl" "$DATA/qwen35-stage3"
test ! -e "$DATA/qwen35-v5"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/qwen35-20261030-targeted-v5/stage4" "$DATA/probe.jsonl" "$DATA/qwen35-v5"
printf "complete\n" > "$DATA/qwen35-status.txt"
