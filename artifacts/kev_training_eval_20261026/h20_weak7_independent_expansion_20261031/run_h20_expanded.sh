#!/usr/bin/env bash
set -Eeuo pipefail

model="$1"
cd /data/kev
data_root="local_data/h20_weak7_independent_expansion_20261101"
case "$model" in
  4b)
    init="runs/h20-4b-s4"
    base="Qwen/Qwen3.5-4B-Base"
    revision="1001bb4d826a52d1f399e183466143f4da7b741b"
    gpus="0,1"
    world=2
    batch=2
    accum=2
    expected_sha="3d7b61e934f53e87c3766e975fd623adc0db0ba5a0d53e923e53cd04c23e70e5"
    run="runs/h20-4b-weak7-neighborhood-expansion-e1-2gpu-20261101"
    ;;
  9b)
    init="runs/h20-9b-s3"
    base="Qwen/Qwen3.5-9B-Base"
    revision="68c46c4b3498877f3ef123c856ecfde50c39f404"
    gpus="2,3,4,5"
    world=4
    batch=2
    accum=1
    expected_sha="460b1fac80b96a26c0df2d1cdf126340f10f2f217df3f96b1bf1633a83d9a30f"
    run="runs/h20-9b-weak7-neighborhood-expansion-e1-4gpu-20261101"
    ;;
  *) echo "model must be 4b or 9b" >&2; exit 2 ;;
esac

eval_root="${run}-eval"
status="$eval_root/status.log"
mkdir -p "$eval_root" logs
test ! -e "$run"
test "$(sha256sum "$data_root/${model}_combined_train.jsonl" | cut -d ' ' -f 1)" = "$expected_sha"
trap 'echo "$(date -Is) FAILED line=$LINENO model='"$model"'" >> '"$status"'' ERR
export CUDA_VISIBLE_DEVICES="$gpus" HF_HUB_OFFLINE=1 HF_HOME=/data/.cache/huggingface TOKENIZERS_PARALLELISM=false
echo "$(date -Is) TRAIN_START model=$model world=$world gpu=$gpus batch=$batch accum=$accum effective_batch=8" >> "$status"
/data/kev/.venv/bin/torchrun --standalone --nproc_per_node="$world" -m kev.train \
  --suite evals/v7/decision-v7 \
  --data "$data_root/${model}_combined_train.jsonl" --replay 6000 \
  --init_from "$init" --base "$base" --base_revision "$revision" \
  --epochs 1 --lr 1e-5 --head_lr 0 --weight_decay 0.01 --lora 16 \
  --batch "$batch" --accum "$accum" --dtype bf16 --weights_dtype fp32 --checkpointing 1 \
  --p_none 0.10 --p_none_distract 0.12 --p_distract 0.15 --p_none_pair 0.25 \
  --synthetic_repeat 1 --max_state 7552 --seed 101 --device cuda \
  --distributed_lora 1 --out "$run" \
  > "logs/$(basename "$run").log" 2>&1
test -f "$run/training_metrics.json"
echo "$(date -Is) TRAIN_DONE model=$model" >> "$status"

export CUDA_VISIBLE_DEVICES="${gpus%%,*}"
/data/kev/.venv/bin/python -u -m kev.benchmark \
  --run "$run" --data "$data_root/${model}_combined_development.jsonl" \
  --out "${run}-development" --device cuda \
  > "logs/$(basename "$run")-development.log" 2>&1
echo "$(date -Is) DEVELOPMENT_DONE model=$model" >> "$status"

for pair in \
  decision-v7:evals/v7/decision-v7 \
  transfer-v4:evals/v4/transfer-v4 \
  transfer-v9:evals/v9/transfer-v9 \
  hard-v1:evals/hard-v1 \
  devtools-v1:evals/devtools-v1 \
  documents-v1:evals/documents-v1; do
  name="${pair%%:*}"
  suite="${pair#*:}"
  echo "$(date -Is) START $name model=$model" >> "$status"
  /data/kev/.venv/bin/python -u -m kev.benchmark \
    --run "$run" --suite "$suite" --allow-test \
    --out "$eval_root/$name" --device cuda \
    > "$eval_root/$name.log" 2>&1
  echo "$(date -Is) DONE $name model=$model" >> "$status"
done
echo "$(date -Is) ALL_DONE model=$model" >> "$status"
