#!/usr/bin/env bash
set -euo pipefail

SMOKE_PID_FILE=/data/kev/runs/h20-27b-v2-custom114627-fullft8-smoke-20261107.pid
SMOKE_RUN=/data/kev/runs/h20-27b-v2-custom114627-fullft8-smoke-20261107
SMOKE_LOG=/data/kev/logs/h20-27b-v2-custom114627-fullft8-smoke-20261107.log
FULL_RUN=/data/kev/runs/h20-27b-v2-custom114627-fullft8-20261107
FULL_LOG=/data/kev/logs/h20-27b-v2-custom114627-fullft8-20261107.log
LAUNCH=/data/kev-v2-custom-115047-20261107/scripts/launch_custom_v2_fullft8.sh

pid="$(cat "$SMOKE_PID_FILE")"
while kill -0 "$pid" 2>/dev/null; do
  sleep 30
done

if grep -Eq "FAILED|Traceback|out of memory|CUDA error|NaN" "$SMOKE_LOG"; then
  echo "SMOKE_FAILED: failure marker found in $SMOKE_LOG" >&2
  exit 10
fi

/data/kev/.venv/bin/python -c '
import json, math
p="/data/kev/runs/h20-27b-v2-custom114627-fullft8-smoke-20261107/checkpoint/training_metrics.json"
m=json.load(open(p))
assert m["optimizer_steps"] == 2, m
assert m["world_size"] == 8, m
assert m["weights"] == "full", m
for g in m.get("grad_norm", []):
    assert math.isfinite(float(g["mean"])) and math.isfinite(float(g["max"])), g
print(json.dumps({k:m.get(k) for k in ("optimizer_steps","world_size","weights","truncated_records","rejected_records","peak_device_bytes")}, sort_keys=True))
'

if [[ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | sed '/^$/d')" ]]; then
  echo "PROMOTION_ABORTED: GPU compute process present after smoke" >&2
  exit 11
fi

nohup "$LAUNCH" full > "$FULL_LOG" 2>&1 &
full_pid=$!
echo "$full_pid" > /data/kev/runs/h20-27b-v2-custom114627-fullft8-20261107.pid
echo "FULL_STARTED pid=$full_pid run=$FULL_RUN log=$FULL_LOG"
