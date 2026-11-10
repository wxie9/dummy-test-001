#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/targeted_three_hardmatched_20261031"
RUN="$ROOT/runs/qwen35-20261031-targeted-three-hardmatched-e1"
test ! -e "$RUN"
mkdir "$RUN"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$RUN/status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=1 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/stages/stage3"
printf 'preflight\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/preflight.py" Qwen/Qwen3.5-0.8B-Base dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 "$DATA" "$RUN/preflight.json"
printf 'development_before\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" "$ROOT/runs/replica-20261026/stage3" "$DATA/development.jsonl" "$RUN/development-before"
printf 'training_before\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" "$ROOT/runs/replica-20261026/stage3" "$DATA/train.jsonl" "$RUN/train-before"
printf 'training\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.train \
  --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \
  --perm_kl 0.0 --perm_frac 0.3 --ord_w 0.0 \
  --p_none 0.1 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \
  --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \
  --dtype bf16 --checkpointing 1 --replay 0 --max_state 7552 \
  --data "$DATA/train.jsonl" \
  --base Qwen/Qwen3.5-0.8B-Base \
  --base_revision dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68 \
  --init_from "$ROOT/runs/replica-20261026/stage3" \
  --suite "$ROOT/evals/v7/decision-v7" \
  --out "$RUN/stage4" --device cuda
printf 'development_after\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" "$RUN/stage4" "$DATA/development.jsonl" "$RUN/development-after"
printf 'training_after\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$ROOT/targeted_v6_20261030/evaluate_development.py" "$RUN/stage4" "$DATA/train.jsonl" "$RUN/train-after"
printf 'hard_v1\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/hard-v1" --allow-test --device cuda --out "$RUN/eval-hard-v1"
printf 'complete\n' > "$RUN/status.txt"
