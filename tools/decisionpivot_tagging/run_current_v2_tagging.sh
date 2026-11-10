#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  echo "DASHSCOPE_API_KEY is not set" >&2
  exit 2
fi

output_dir="${1:-/data/kev/analysis/decisionpivot_taxonomy_qwen38flash_20261105/current_v2_candidates_run01}"
tag_concurrency="${TAG_CONCURRENCY:-24}"
tag_batch_size="${TAG_BATCH_SIZE:-8}"
mkdir -p "$output_dir"

exec /data/kev/.venv/bin/python /data/kev/tools/decisionpivot_tagging/tag_v2.py \
  --input synthetic_abstention=/data/kev-v2-public-reconstruction-20261104/generated/abstention.jsonl \
  --input synthetic_intent=/data/kev-v2-public-reconstruction-20261104/generated/intent.jsonl \
  --input synthetic_long_doc=/data/kev-v2-public-reconstruction-20261104/generated/long_doc.jsonl \
  --input synthetic_numeric=/data/kev-v2-public-reconstruction-20261104/generated/numeric.jsonl \
  --input synthetic_retrieval=/data/kev-v2-public-reconstruction-20261104/generated/retrieval.jsonl \
  --input synthetic_rubric_judge=/data/kev-v2-public-reconstruction-20261104/generated/rubric_judge.jsonl \
  --input synthetic_tool_routing=/data/kev-v2-public-reconstruction-20261104/generated/tool_routing.jsonl \
  --input kev_hard_v1_extra_approx=/data/kev-v2-public-reconstruction-20261104/generated/hard_v1_extra.jsonl \
  --input kev_b1v2_exact=/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/b1v2-train.jsonl \
  --input kev_devtools_v1_raw=/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/devtools-v1-train.jsonl \
  --input kev_documents_v1_raw=/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/documents-v1-train.jsonl \
  --input kev_hard_v1_exact=/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/hard-v1-train.jsonl \
  --input tasksource_pivot24k=/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource_pivot_commercial_24k_typed.jsonl \
  --output-dir "$output_dir" \
  --batch-size "$tag_batch_size" \
  --concurrency "$tag_concurrency" \
  --max-state-chars 3500
