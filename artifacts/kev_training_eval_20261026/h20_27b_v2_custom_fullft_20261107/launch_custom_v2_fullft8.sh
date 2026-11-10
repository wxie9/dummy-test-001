#!/usr/bin/env bash
set -euo pipefail

MODE="${1:?usage: $0 smoke|full}"
BASE=/data/models/Qwen3.8-27B
DATA=/data/kev-v2-custom-115047-20261107/train.dedup.jsonl
ROOT=/data/kev/runs

case "$MODE" in
  smoke)
    RUN="$ROOT/h20-27b-v2-custom114627-fullft8-smoke-20261107"
    EXTRA=(--max_steps 2)
    ;;
  full)
    RUN="$ROOT/h20-27b-v2-custom114627-fullft8-20261107"
    EXTRA=(
      --snapshot_fractions 0.25,0.5,0.75
      --snapshot_dir "$ROOT/h20-27b-v2-custom114627-fullft8-20261107/snapshots"
    )
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 2
    ;;
esac

mkdir -p "$RUN"
cp /data/kev-v2-custom-115047-20261107/manifest.dedup.json "$RUN/data_manifest.json"
cp /data/kev-v2-custom-115047-20261107/scripts/launch_custom_v2_fullft8.sh "$RUN/launch.sh"
sha256sum "$DATA" "$RUN/data_manifest.json" "$RUN/launch.sh" > "$RUN/input_hashes.sha256"
cd /data/kev

exec env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  .venv/bin/torchrun --standalone --nproc_per_node=8 -m kev.train \
  --base "$BASE" \
  --base_revision 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 \
  --data "$DATA" \
  --epochs 1 \
  --lr 2e-6 \
  --head_lr 1e-4 \
  --weight_decay 0.01 \
  --batch 8 \
  --accum 2 \
  --device cuda \
  --dtype bf16 \
  --weights_dtype bf16 \
  --checkpointing 1 \
  --full_ft 1 \
  --shared_prefix 1 \
  --length_sort 1 \
  --max_state 32768 \
  --p_none_pair 0.25 \
  --none_pair_max_state 8192 \
  --pass_tokens_max 40960 \
  --seed 0 \
  --out "$RUN/checkpoint" \
  "${EXTRA[@]}"
