# LeHome 常用命令速查

## 下载资产

```bash
hf download lehome/asset_challenge --repo-type dataset --local-dir Assets
```

## 下载合并训练集

```bash
hf download lehome/dataset_challenge_merged --repo-type dataset --local-dir Datasets/example
```

## 训练 ACT

```bash
mkdir -p /root/gpufree-data/lehome-outputs/train/act_top_short

lerobot-train \
  --config_path /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/configs/train_act_every_embodied.yaml \
  2>&1 | tee /root/gpufree-data/lehome-outputs/train/act_top_short/train.log
```

## 训练 DP

```bash
mkdir -p /root/gpufree-data/lehome-outputs/train/dp_top_short

lerobot-train \
  --config_path /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/configs/train_dp_every_embodied.yaml \
  2>&1 | tee /root/gpufree-data/lehome-outputs/train/dp_top_short/train.log
```

## 评测 ACT

```bash
python -m scripts.eval \
  --policy_type lerobot \
  --policy_path /root/gpufree-data/lehome-outputs/train/act_top_short/checkpoints/last/pretrained_model \
  --dataset_root Datasets/example/top_short_merged \
  --garment_type top_short \
  --num_episodes 2 \
  --enable_cameras \
  --save_video \
  --video_dir /root/gpufree-data/lehome-outputs/eval/act_top_short \
  --device cpu
```

## 评测 DP

```bash
python -m scripts.eval \
  --policy_type lerobot \
  --policy_path /root/gpufree-data/lehome-outputs/train/dp_top_short/checkpoints/last/pretrained_model \
  --dataset_root Datasets/example/top_short_merged \
  --garment_type top_short \
  --num_episodes 2 \
  --enable_cameras \
  --save_video \
  --video_dir /root/gpufree-data/lehome-outputs/eval/dp_top_short \
  --device cpu \
  --policy_device cpu \
  --policy_num_inference_steps 1
```

## 解析训练日志并画图

```bash
python /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/scripts/plot_train_metrics.py \
  --log_file /root/gpufree-data/lehome-outputs/train/act_top_short/train.log \
  --out_dir /root/gpufree-data/lehome-outputs/plots/act_top_short \
  --title "ACT Top-Short Training Metrics"
```

## 比赛强化版 ACT 长训

```bash
cd /root/lehome-challenge
source .venv/bin/activate
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

lerobot-train \
  --config_path /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/configs/train_act_competition_l40.yaml \
  2>&1 | tee /root/gpufree-data/lehome-outputs/train/act_four_types_l40.log
```

## 采样 GPU 指标

```bash
/root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/scripts/sample_gpu_metrics.sh \
  /root/gpufree-data/lehome-outputs/monitor/act_four_types_l40_gpu.csv \
  10
```

## 画 GPU 曲线

```bash
python /root/gpufree-data/every-embodied/15-Challenge竞赛/LeHome/resources/scripts/plot_gpu_metrics.py \
  --csv_file /root/gpufree-data/lehome-outputs/monitor/act_four_types_l40_gpu.csv \
  --out_png /root/gpufree-data/lehome-outputs/plots/act_four_types_l40_live/gpu_metrics.png \
  --title "L40 GPU Monitor During ACT Training"
```
