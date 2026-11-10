#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA=/C20545/kev-08b-official-repro-20261026/targeted_v3_pilot_train_20261030
RUN=/C20545/kev-08b-official-repro-20261026/runs/qwen3-20261030-targeted-v3-pilot
test ! -e "$RUN"
mkdir "$RUN"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\n" "$code" > "$RUN/status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES=1
export HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/stages/stage3"
printf 'preflight\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/preflight.py" '/C20545/models/Qwen3-0.6B-Base' 'local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba' "$DATA/train.jsonl" "$RUN/preflight.json"
printf 'training\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.train \
 --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \
 --perm_kl 0.0 --perm_frac 0.0 --ord_w 0.0 \
 --p_none 0.0 --p_none_distract 0.0 --p_distract 0.0 --p_none_pair 0.0 \
 --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \
 --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \
 --dtype bf16 --checkpointing 1 --replay 0 --max_state 7552 \
 --data "$DATA/train.jsonl" --base '/C20545/models/Qwen3-0.6B-Base' --base_revision 'local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba' \
 --init_from "$ROOT/runs/qwen3-06b-20261026/stage3" --suite "$ROOT/evals/v7/decision-v7" \
 --out "$RUN/stage4" --device cuda
printf 'evaluating_hard_v1\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/hard-v1" \
 --allow-test --out "$RUN/eval-hard-v1" --device cuda
printf 'complete\n' > "$RUN/status.txt"
