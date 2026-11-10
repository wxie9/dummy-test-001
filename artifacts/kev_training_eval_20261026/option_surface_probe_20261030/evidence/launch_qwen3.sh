#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/option_surface_probe_20261030"
export CUDA_VISIBLE_DEVICES=3 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 PYTHONPATH="$ROOT/stages/stage3"
test ! -e "$DATA/qwen3-stage3"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/qwen3-06b-20261026/stage3" "$DATA/probe.jsonl" "$DATA/qwen3-stage3"
test ! -e "$DATA/qwen3-v5"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/qwen3-20261030-targeted-v5/stage4" "$DATA/probe.jsonl" "$DATA/qwen3-v5"
printf "complete\n" > "$DATA/qwen3-status.txt"
