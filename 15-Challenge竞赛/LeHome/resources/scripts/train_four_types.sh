#!/usr/bin/env bash
set -euo pipefail

mkdir -p /root/gpufree-data/lehome-outputs/train/act_four_types
mkdir -p /root/gpufree-data/lehome-outputs/train/dp_four_types

lerobot-train \
  --config_path /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/configs/train_act_four_types_every_embodied.yaml \
  2>&1 | tee /root/gpufree-data/lehome-outputs/train/act_four_types/train.log

lerobot-train \
  --config_path /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/configs/train_dp_four_types_every_embodied.yaml \
  2>&1 | tee /root/gpufree-data/lehome-outputs/train/dp_four_types/train.log
