#!/usr/bin/env bash
set -euo pipefail

OUT_FILE="${1:-/root/gpufree-data/lehome-outputs/monitor/gpu_metrics.csv}"
INTERVAL="${2:-10}"

mkdir -p "$(dirname "$OUT_FILE")"
echo "timestamp,index,name,utilization_gpu,memory_used_mb,memory_total_mb,temperature_gpu,power_draw_w" > "$OUT_FILE"

while true; do
  nvidia-smi \
    --query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
    --format=csv,noheader,nounits >> "$OUT_FILE"
  sleep "$INTERVAL"
done
