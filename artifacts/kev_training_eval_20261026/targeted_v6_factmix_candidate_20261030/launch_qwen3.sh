#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/targeted_v6_factmix_candidate_20261030"
RUN="$ROOT/runs/qwen3-20261030-targeted-v6-factmix"
test ! -e "$RUN"
mkdir "$RUN"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$RUN/status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=3 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/stages/stage3"
printf 'preflight\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/preflight.py" '/C20545/models/Qwen3-0.6B-Base' 'local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba' "$DATA" "$ROOT/evals/v7/decision-v7" "$RUN/preflight.json"
printf 'development_before\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/qwen3-06b-20261026/stage3" "$DATA/development.jsonl" "$RUN/development-before"
printf 'train_probe_before\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/qwen3-06b-20261026/stage3" "$DATA/train_probe.jsonl" "$RUN/train-probe-before"
printf 'training\n' > "$RUN/status.txt"
env CUDA_VISIBLE_DEVICES=3 HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 "$ROOT/python.sh" -m kev.train \
  --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \
  --perm_kl 0.0 --perm_frac 0.3 --ord_w 0.0 \
  --p_none 0.1 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \
  --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \
  --dtype bf16 --checkpointing 1 --replay 6000 --max_state 7552 \
  --data "$ROOT/targeted_v6_factmix_candidate_20261030/train.jsonl" \
  --base /C20545/models/Qwen3-0.6B-Base \
  --base_revision local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba \
  --init_from "$ROOT/runs/qwen3-06b-20261026/stage3" \
  --suite "$ROOT/evals/v7/decision-v7" \
  --out "$ROOT/runs/qwen3-20261030-targeted-v6-factmix/stage4" \
  --device cuda

printf 'development_after\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/development.jsonl" "$RUN/development-after"
printf 'train_probe_after\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/train_probe.jsonl" "$RUN/train-probe-after"
printf 'hard_v1\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/hard-v1" --allow-test --device cuda --out "$RUN/eval-hard-v1"
printf 'devtools_v1\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/devtools-v1" --allow-test --device cuda --out "$RUN/eval-devtools-v1"
printf 'complete\n' > "$RUN/status.txt"
