#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 CHECKPOINT RUN_NAME OUTPUT_ROOT" >&2
  exit 2
fi

checkpoint="$1"
run_name="$2"
root="$3"

cd /data/kev/benchmarks/DecisionPivot

status="$root/status.log"
server_dir="$root/server_logs"
shard_dir="$root/shards"
run_dir="$root/runs/$run_name"
result_dir="$root/results"

mkdir -p "$server_dir" "$shard_dir" "$run_dir"
: > "$status"

ports=(9730 9731 9732 9733 9734 9735 9736 9737)
task_sets=(
  "answerable_facts,record_rule"
  "clause_change,filter_match"
  "dep_resolve"
  "ledger_reconcile,log_count_check"
  "perm_inherit,policy_case"
  "sched_conflict,state_goal"
  "toolcall_valid"
  "triage_order"
)
server_pids=()
worker_pids=()

cleanup() {
  for pid in "${server_pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  for pid in "${server_pids[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

for gpu in {0..7}; do
  port="${ports[$gpu]}"
  export CUDA_VISIBLE_DEVICES="$gpu"
  export HF_HUB_OFFLINE=1
  export HF_HOME=/data/.cache/huggingface
  export TOKENIZERS_PARALLELISM=false
  /data/kev/.venv/bin/python -u -m kev.serve \
    --run "$checkpoint" --host 127.0.0.1 --port "$port" --device cuda \
    > "$server_dir/gpu${gpu}.log" 2>&1 &
  server_pids+=("$!")
  echo "$(date -Is) SERVER_START GPU=$gpu PORT=$port PID=$!" >> "$status"
done

printf '%s\n' "${server_pids[@]}" > "$root/server_pids.txt"

for gpu in {0..7}; do
  port="${ports[$gpu]}"
  ready=0
  for _ in {1..180}; do
    if curl -fsS "http://127.0.0.1:${port}/v1/models" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
  done
  if [[ "$ready" -ne 1 ]]; then
    echo "$(date -Is) SERVER_FAILED GPU=$gpu PORT=$port" >> "$status"
    exit 1
  fi
  echo "$(date -Is) SERVER_READY GPU=$gpu PORT=$port" >> "$status"
done

for gpu in {0..7}; do
  port="${ports[$gpu]}"
  tasks="${task_sets[$gpu]}"
  out="$shard_dir/gpu${gpu}"
  mkdir -p "$out"
  (
    echo "$(date -Is) WORKER_START GPU=$gpu TASKS=$tasks" >> "$status"
    /data/kev/.venv/bin/python -u runner/bench_http.py \
      --url "http://127.0.0.1:${port}" --model "$run_name" \
      --bench eval_data --out "$out" --tasks "$tasks" --workers 32 \
      > "$root/worker-gpu${gpu}.log" 2>&1
    echo "$(date -Is) WORKER_DONE GPU=$gpu TASKS=$tasks" >> "$status"
  ) &
  worker_pids+=("$!")
done

printf '%s\n' "${worker_pids[@]}" > "$root/worker_pids.txt"

failed=0
for pid in "${worker_pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "$(date -Is) WORKERS_FAILED" >> "$status"
  exit 1
fi

/data/kev/.venv/bin/python -u /data/kev/local_data/merge_decisionpivot_shards.py \
  "$shard_dir" "$run_dir" > "$root/merge.log" 2>&1

printf '%s\n' "{\"$run_name\": {\"name\": \"$run_name\", \"table\": true}}" > "$root/systems.json"
/data/kev/.venv/bin/python -u scoring/score.py \
  --all --root eval_data --runs "$root/runs" --systems "$root/systems.json" \
  --out "$result_dir" --jobs 8 \
  > "$root/score.log" 2>&1

echo "$(date -Is) ALL_DONE" >> "$status"
