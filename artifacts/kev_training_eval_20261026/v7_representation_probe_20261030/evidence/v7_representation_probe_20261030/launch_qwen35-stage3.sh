#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/v7_representation_probe_20261030"
test ! -e "$DATA/qwen35-stage3"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$DATA/qwen35-stage3.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=3 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
printf 'evaluating\n' > "$DATA/qwen35-stage3.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "/C20545/kev-08b-official-repro-20261026/runs/replica-20261026/stage3" "$DATA/probe.jsonl" "$DATA/qwen35-stage3"
printf 'complete\n' > "$DATA/qwen35-stage3.status.txt"
