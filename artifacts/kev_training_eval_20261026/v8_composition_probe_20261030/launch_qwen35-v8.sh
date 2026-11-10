#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/v8_composition_probe_20261030"
test ! -e "$DATA/qwen35-v8"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$DATA/qwen35-v8.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=4 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
printf 'evaluating\n' > "$DATA/qwen35-v8.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "/C20545/kev-08b-official-repro-20261026/runs/qwen35-20261030-targeted-v8-steps/stage4" "$DATA/probe.jsonl" "$DATA/qwen35-v8"
printf 'complete\n' > "$DATA/qwen35-v8.status.txt"
