#!/usr/bin/env bash
set -euo pipefail

MODEL_ROOT="${1:-/root/gpufree-data/lehome-outputs/train/act_four_types_l40}"
GARMENT_TYPE="${2:-top_short}"
NUM_EPISODES="${3:-1}"
OUT_ROOT="${4:-/root/gpufree-data/lehome-outputs/eval/manual_latest}"
POLICY_DEVICE="${5:-cpu}"

if [[ -d "${MODEL_ROOT}/checkpoints/last/pretrained_model" ]]; then
  POLICY_PATH="${MODEL_ROOT}/checkpoints/last/pretrained_model"
else
  LATEST_STEP="$(find "${MODEL_ROOT}/checkpoints" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | rg '^[0-9]+$' | sort -n | tail -n 1)"
  POLICY_PATH="${MODEL_ROOT}/checkpoints/${LATEST_STEP}/pretrained_model"
fi

MODEL_NAME="$(basename "${MODEL_ROOT}")"
VIDEO_DIR="${OUT_ROOT}/${MODEL_NAME}/${GARMENT_TYPE}"
DATASET_ROOT="/root/lehome-challenge/Datasets/example/${GARMENT_TYPE}_merged"

cd /root/lehome-challenge
export PYTHONPATH="/root/lehome-challenge:${PYTHONPATH:-}"

./third_party/IsaacLab/isaaclab.sh -p -m scripts.eval \
  --policy_type lerobot \
  --policy_path "${POLICY_PATH}" \
  --dataset_root "${DATASET_ROOT}" \
  --garment_type "${GARMENT_TYPE}" \
  --num_episodes "${NUM_EPISODES}" \
  --enable_cameras \
  --save_video \
  --video_dir "${VIDEO_DIR}" \
  --device cpu \
  --policy_device "${POLICY_DEVICE}" \
  --headless
