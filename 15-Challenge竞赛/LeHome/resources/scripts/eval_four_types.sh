#!/usr/bin/env bash
set -euo pipefail

MODEL_TYPE="${1:-act}"
if [[ "$MODEL_TYPE" == "act" ]]; then
  MODEL_DIR="/root/gpufree-data/lehome-outputs/train/act_four_types/checkpoints/last/pretrained_model"
  EXTRA_ARGS=()
else
  MODEL_DIR="/root/gpufree-data/lehome-outputs/train/dp_four_types/checkpoints/last/pretrained_model"
  EXTRA_ARGS=(--policy_device cpu --policy_num_inference_steps 1)
fi

for garment_type in top_short top_long pant_short pant_long; do
  python -m scripts.eval \
    --policy_type lerobot \
    --policy_path "$MODEL_DIR" \
    --dataset_root "Datasets/example/${garment_type}_merged" \
    --garment_type "$garment_type" \
    --num_episodes 2 \
    --enable_cameras \
    --save_video \
    --video_dir "/root/gpufree-data/lehome-outputs/eval/${MODEL_TYPE}_${garment_type}" \
    --device cpu \
    "${EXTRA_ARGS[@]}"
done
