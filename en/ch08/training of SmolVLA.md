```Bash
git clone https://huggingface.co/datasets/aopolin-lv/libero_spatial_no_noops_lerobot_v21git clone https://github.com/huggingface/lerobotcd lerobot/srcpython lerobot/scripts/train.py \  --policy.type=smolvla \  --dataset.repo_id=/data1/DATA/libero_spatial_no_noops_lerobot_v21 \  --batch_size=128 \  --steps=20000 \  --policy.push_to_hub=false \  --policy.use_amp=false \  --num_workers=12 \  --eval_freq=2000 \  --eval.n_episodes=5 \  --eval.batch_size=1 \  --save_freq=2000 \  --save_checkpoint=true \  --log_freq=200 \  --wandb.enable=false \  --output_dir=/home/vipuser/outputs/smolvla/   TOKENIZERS_PARALLELISM=false python lerobot/scripts/train.py \  --policy.type=smolvla \  --dataset.repo_id=/data1/DATA/libero_spatial_no_noops_lerobot_v21 \  --batch_size=128 \  --steps=20000 \  --policy.push_to_hub=false \  --policy.use_amp=false \  --num_workers=8 \  --eval_freq=2000 \  --eval.n_episodes=5 \  --eval.batch_size=1 \  --save_freq=2000 \  --save_checkpoint=true \  --log_freq=200 \  --wandb.enable=false \  --output_dir=/home/vipuser/outputs/smolvla/   
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NTAwMTY3ZTdhZTkzMWM4ZjNkN2Y4NDIxZWU0MjYzZDRfZHlxRm9GOGlvbmJBNG80cmZsS1RRdTBqaWVjM1h5ZVdfVG9rZW46RGJXM2JRdDd3b3ZWanB4V3dzeWNsMlhLbnFmXzE3NTI1MDQ5NzQ6MTc1MjUwODU3NF9WNA)

训练 10小时。 
The training time is 10 hours.

修改train显示tqdm和csv日志
Modified train.py to show tqdm and csv log.

```Python
#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import time
from contextlib import nullcontext
from pprint import pformat
from typing import Any
import csv
import os

import torch
from termcolor import colored
from torch.amp import GradScaler
from torch.optim import Optimizer
from tqdm import tqdm

from lerobot.configs import parser
from lerobot.configs.train import TrainPipelineConfig
from lerobot.datasets.factory import make_dataset
from lerobot.datasets.sampler import EpisodeAwareSampler
from lerobot.datasets.utils import cycle
from lerobot.envs.factory import make_env
from lerobot.optim.factory import make_optimizer_and_scheduler
from lerobot.policies.factory import make_policy
from lerobot.policies.pretrained import PreTrainedPolicy
from lerobot.policies.utils import get_device_from_parameters
from lerobot.scripts.eval import eval_policy
from lerobot.utils.logging_utils import AverageMeter, MetricsTracker
from lerobot.utils.random_utils import set_seed
from lerobot.utils.train_utils import (
    get_step_checkpoint_dir,
    get_step_identifier,
    load_training_state,
    save_checkpoint,
    update_last_checkpoint,
)
from lerobot.utils.utils import (
    format_big_number,
    get_safe_torch_device,
    has_method,
    init_logging,
)
from lerobot.utils.wandb_utils import WandBLogger

def update_policy(
    train_metrics: MetricsTracker,
    policy: PreTrainedPolicy,
    batch: Any,
    optimizer: Optimizer,
    grad_clip_norm: float,
    grad_scaler: GradScaler,
    lr_scheduler=None,
    use_amp: bool = False,
    lock=None,
) -> tuple[MetricsTracker, dict]:
    start_time = time.perf_counter()
    device = get_device_from_parameters(policy)
    policy.train()
    with torch.autocast(device_type=device.type) if use_amp else nullcontext():
        loss, output_dict = policy.forward(batch)
        # TODO(rcadene): policy.unnormalize_outputs(out_dict)
    grad_scaler.scale(loss).backward()

    # Unscale the gradient of the optimizer's assigned params in-place **prior to gradient clipping**.
    grad_scaler.unscale_(optimizer)

    grad_norm = torch.nn.utils.clip_grad_norm_(
        policy.parameters(),
        grad_clip_norm,
        error_if_nonfinite=False,
    )

    # Optimizer's gradients are already unscaled, so scaler.step does not unscale them,
    # although it still skips optimizer.step() if the gradients contain infs or NaNs.
    with lock if lock is not None else nullcontext():
        grad_scaler.step(optimizer)
    # Updates the scale for next iteration.
    grad_scaler.update()

    optimizer.zero_grad()

    # Step through pytorch scheduler at every batch instead of epoch
    if lr_scheduler is not None:
        lr_scheduler.step()

    if has_method(policy, "update"):
        # To possibly update an internal buffer (for instance an Exponential Moving Average like in TDMPC).
        policy.update()

    train_metrics.loss = loss.item()
    train_metrics.grad_norm = grad_norm.item()
    train_metrics.lr = optimizer.param_groups[0]["lr"]
    train_metrics.update_s = time.perf_counter() - start_time
    return train_metrics, output_dict

@parser.wrap()
def train(cfg: TrainPipelineConfig):
    cfg.validate()
    logging.info(pformat(cfg.to_dict()))

    if cfg.wandb.enable and cfg.wandb.project:
        wandb_logger = WandBLogger(cfg)
    else:
        wandb_logger = None
        logging.info(colored("Logs will be saved locally.", "yellow", attrs=["bold"]))

    if cfg.seed is not None:
        set_seed(cfg.seed)

    # Check device is available
    device = get_safe_torch_device(cfg.policy.device, log=True)
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True

    logging.info("Creating dataset")
    dataset = make_dataset(cfg)

    # Create environment used for evaluating checkpoints during training on simulation data.
    # On real-world data, no need to create an environment as evaluations are done outside train.py,
    # using the eval.py instead, with gym_dora environment and dora-rs.
    eval_env = None
    if cfg.eval_freq > 0 and cfg.env is not None:
        logging.info("Creating env")
        eval_env = make_env(cfg.env, n_envs=cfg.eval.batch_size, use_async_envs=cfg.eval.use_async_envs)

    logging.info("Creating policy")
    policy = make_policy(
        cfg=cfg.policy,
        ds_meta=dataset.meta,
    )

    logging.info("Creating optimizer and scheduler")
    optimizer, lr_scheduler = make_optimizer_and_scheduler(cfg, policy)
    grad_scaler = GradScaler(device.type, enabled=cfg.policy.use_amp)

    step = 0  # number of policy updates (forward + backward + optim)

    if cfg.resume:
        step, optimizer, lr_scheduler = load_training_state(cfg.checkpoint_path, optimizer, lr_scheduler)

    num_learnable_params = sum(p.numel() for p in policy.parameters() if p.requires_grad)
    num_total_params = sum(p.numel() for p in policy.parameters())

    logging.info(colored("Output dir:", "yellow", attrs=["bold"]) + f" {cfg.output_dir}")
    if cfg.env is not None:
        logging.info(f"{cfg.env.task=}")
    logging.info(f"{cfg.steps=} ({format_big_number(cfg.steps)})")
    logging.info(f"{dataset.num_frames=} ({format_big_number(dataset.num_frames)})")
    logging.info(f"{dataset.num_episodes=}")
    logging.info(f"{num_learnable_params=} ({format_big_number(num_learnable_params)})")
    logging.info(f"{num_total_params=} ({format_big_number(num_total_params)})")

    # create dataloader for offline training
    if hasattr(cfg.policy, "drop_n_last_frames"):
        shuffle = False
        sampler = EpisodeAwareSampler(
            dataset.episode_data_index,
            drop_n_last_frames=cfg.policy.drop_n_last_frames,
            shuffle=True,
        )
    else:
        shuffle = True
        sampler = None

    # Adjust num_workers to avoid system warnings
    actual_num_workers = min(cfg.num_workers, 8)  # System suggested max is 8
    if actual_num_workers != cfg.num_workers:
        logging.info(f"Adjusted num_workers from {cfg.num_workers} to {actual_num_workers} to match system recommendation")

    dataloader = torch.utils.data.DataLoader(
        dataset,
        num_workers=actual_num_workers,
        batch_size=cfg.batch_size,
        shuffle=shuffle,
        sampler=sampler,
        pin_memory=device.type != "cpu",
        drop_last=False,
    )
    dl_iter = cycle(dataloader)

    policy.train()

    train_metrics = {
        "loss": AverageMeter("loss", ":.3f"),
        "grad_norm": AverageMeter("grdn", ":.3f"),
        "lr": AverageMeter("lr", ":0.1e"),
        "update_s": AverageMeter("updt_s", ":.3f"),
        "dataloading_s": AverageMeter("data_s", ":.3f"),
    }

    train_tracker = MetricsTracker(
        cfg.batch_size, dataset.num_frames, dataset.num_episodes, train_metrics, initial_step=step
    )

    logging.info("Start offline training on a fixed dataset")

    # Create output directory if it doesn't exist
    os.makedirs(cfg.output_dir, exist_ok=True)

    # Create CSV file for detailed logging
    csv_log_file = cfg.output_dir / "training_metrics.csv"
    csv_fieldnames = ['step', 'loss', 'grad_norm', 'lr', 'update_s', 'data_s', 'samples', 'episodes', 'epochs']
    csv_file_exists = csv_log_file.exists()

    # Initialize or append to CSV file
    csv_file = open(csv_log_file, 'a', newline='')
    csv_writer = csv.DictWriter(csv_file, fieldnames=csv_fieldnames)
    if not csv_file_exists:
        csv_writer.writeheader()
        logging.info(f"Created detailed metrics CSV: {csv_log_file}")
    else:
        logging.info(f"Appending to existing metrics CSV: {csv_log_file}")

    # Create progress bar for training
    progress_bar = tqdm(
        range(step, cfg.steps),
        initial=step,
        total=cfg.steps,
        desc="Training",
        unit="step",
        ncols=120,
        dynamic_ncols=True,
        leave=True
    )

    for current_step in progress_bar:
        start_time = time.perf_counter()
        batch = next(dl_iter)
        train_tracker.dataloading_s = time.perf_counter() - start_time

        for key in batch:
            if isinstance(batch[key], torch.Tensor):
                batch[key] = batch[key].to(device, non_blocking=True)

        train_tracker, output_dict = update_policy(
            train_tracker,
            policy,
            batch,
            optimizer,
            cfg.optimizer.grad_clip_norm,
            grad_scaler=grad_scaler,
            lr_scheduler=lr_scheduler,
            use_amp=cfg.policy.use_amp,
        )

        # Note: eval and checkpoint happens *after* the `step`th training update has completed, so we
        # increment `step` here.
        step += 1
        train_tracker.step()
        is_log_step = cfg.log_freq > 0 and step % cfg.log_freq == 0
        is_saving_step = step % cfg.save_freq == 0 or step == cfg.steps
        is_eval_step = cfg.eval_freq > 0 and step % cfg.eval_freq == 0

        # Update progress bar with current metrics
        if hasattr(train_tracker, 'loss') and train_tracker.loss.val is not None:
            progress_bar.set_postfix({
                'loss': f"{train_tracker.loss.val:.3f}",
                'lr': f"{train_tracker.lr.val:.1e}",
                'grad_norm': f"{train_tracker.grad_norm.val:.3f}"
            })

        # Write detailed metrics to CSV for every step
        csv_writer.writerow({
            'step': step,
            'loss': train_tracker.loss.val if hasattr(train_tracker, 'loss') else 0.0,
            'grad_norm': train_tracker.grad_norm.val if hasattr(train_tracker, 'grad_norm') else 0.0,
            'lr': train_tracker.lr.val if hasattr(train_tracker, 'lr') else 0.0,
            'update_s': train_tracker.update_s.val if hasattr(train_tracker, 'update_s') else 0.0,
            'data_s': train_tracker.dataloading_s.val if hasattr(train_tracker, 'dataloading_s') else 0.0,
            'samples': train_tracker.samples,
            'episodes': train_tracker.episodes,
            'epochs': train_tracker.epochs
        })
        csv_file.flush()  # Ensure data is written immediately

        if is_log_step:
            logging.info(train_tracker)
            if wandb_logger:
                wandb_log_dict = train_tracker.to_dict()
                if output_dict:
                    wandb_log_dict.update(output_dict)
                wandb_logger.log_dict(wandb_log_dict, step)
            train_tracker.reset_averages()

        if cfg.save_checkpoint and is_saving_step:
            logging.info(f"Checkpoint policy after step {step}")
            checkpoint_dir = get_step_checkpoint_dir(cfg.output_dir, cfg.steps, step)
            save_checkpoint(checkpoint_dir, step, cfg, policy, optimizer, lr_scheduler)
            update_last_checkpoint(checkpoint_dir)
            if wandb_logger:
                wandb_logger.log_policy(checkpoint_dir)

        if cfg.env and is_eval_step:
            step_id = get_step_identifier(step, cfg.steps)
            logging.info(f"Eval policy at step {step}")
            with (
                torch.no_grad(),
                torch.autocast(device_type=device.type) if cfg.policy.use_amp else nullcontext(),
            ):
                eval_info = eval_policy(
                    eval_env,
                    policy,
                    cfg.eval.n_episodes,
                    videos_dir=cfg.output_dir / "eval" / f"videos_step_{step_id}",
                    max_episodes_rendered=4,
                    start_seed=cfg.seed,
                )

            eval_metrics = {
                "avg_sum_reward": AverageMeter("∑rwrd", ":.3f"),
                "pc_success": AverageMeter("success", ":.1f"),
                "eval_s": AverageMeter("eval_s", ":.3f"),
            }
            eval_tracker = MetricsTracker(
                cfg.batch_size, dataset.num_frames, dataset.num_episodes, eval_metrics, initial_step=step
            )
            eval_tracker.eval_s = eval_info["aggregated"].pop("eval_s")
            eval_tracker.avg_sum_reward = eval_info["aggregated"].pop("avg_sum_reward")
            eval_tracker.pc_success = eval_info["aggregated"].pop("pc_success")
            logging.info(eval_tracker)
            if wandb_logger:
                wandb_log_dict = {**eval_tracker.to_dict(), **eval_info}
                wandb_logger.log_dict(wandb_log_dict, step, mode="eval")
                wandb_logger.log_video(eval_info["video_paths"][0], step, mode="eval")

    # Close progress bar and CSV file
    progress_bar.close()
    csv_file.close()
    logging.info(f"Training metrics saved to: {csv_log_file}")

    if eval_env:
        eval_env.close()
    logging.info("End of training")

    if cfg.policy.push_to_hub:
        policy.push_model_to_hub(cfg)

if __name__ == "__main__":
    init_logging()
    train()
```

python lerobot/scripts/eval_LIBERO.py --policy_path=/home/vipuser/outputs/smolvla/checkpoints/last/pretrained_model/

ls /home/vipuser/outputs/smolvla/checkpoints/last/pretrained_model/

差不多15000 steps收敛
It takes about 15000 steps to converge.

```Bash
INFO 2025-07-11 04:31:07 ts/train.py:301 Checkpoint policy after step 14000Training:  71%|▋| 14199/20000 [8:19:11<3:02:49,  1.89s/step, loss=0.023, lr=5.5eINFO 2025-07-11 04:37:33 ts/train.py:292 step:14K smpl:2M ep:15K epch:34.31 loss:0.021 grdn:0.186 lr:5.6e-05 updt_s:1.884 data_s:0.024Training:  72%|▋| 14399/20000 [8:25:29<2:56:10,  1.89s/step, loss=0.020, lr=5.4eINFO 2025-07-11 04:43:51 ts/train.py:292 step:14K smpl:2M ep:15K epch:34.80 loss:0.021 grdn:0.184 lr:5.5e-05 updt_s:1.887 data_s:0.000Training:  73%|▋| 14599/20000 [8:31:51<2:49:49,  1.89s/step, loss=0.019, lr=5.3eINFO 2025-07-11 04:50:13 ts/train.py:292 step:15K smpl:2M ep:15K epch:35.28 loss:0.021 grdn:0.188 lr:5.4e-05 updt_s:1.885 data_s:0.021Training:  74%|▋| 14799/20000 [8:38:09<2:44:12,  1.89s/step, loss=0.017, lr=5.2eINFO 2025-07-11 04:56:31 ts/train.py:292 step:15K smpl:2M ep:15K epch:35.76 loss:0.020 grdn:0.182 lr:5.3e-05 updt_s:1.886 data_s:0.000Training:  75%|▋| 14999/20000 [8:44:33<2:37:19,  1.89s/step, loss=0.020, lr=5.1eINFO 2025-07-11 05:02:55 ts/train.py:292 step:15K smpl:2M ep:16K epch:36.25 loss:0.020 grdn:0.181 lr:5.2e-05 updt_s:1.884 data_s:0.032Training:  76%|▊| 15199/20000 [8:50:51<2:30:57,  1.89s/step, loss=0.020, lr=5.0eINFO 2025-07-11 05:09:13 ts/train.py:292 step:15K smpl:2M ep:16K epch:36.73 loss:0.020 grdn:0.184 lr:5.1e-05 updt_s:1.886 data_s:0.000Training:  77%|▊| 15399/20000 [8:57:14<2:24:53,  1.89s/step, loss=0.017, lr=4.9eINFO 2025-07-11 05:15:35 ts/train.py:292 step:15K smpl:2M ep:16K epch:37.21 loss:0.020 grdn:0.181 lr:5.0e-05 updt_s:1.885 data_s:0.025Training:  78%|▊| 15599/20000 [9:03:32<2:18:53,  1.89s/step, loss=0.021, lr=4.8eINFO 2025-07-11 05:21:53 ts/train.py:292 step:16K smpl:2M ep:16K epch:37.70 loss:0.020 grdn:0.180 lr:4.9e-05 updt_s:1.887 data_s:0.000Training:  79%|▊| 15799/20000 [9:09:56<2:12:52,  1.90s/step, loss=0.018, lr=4.7eINFO 2025-07-11 05:28:17 ts/train.py:292 step:16K smpl:2M ep:16K epch:38.18 loss:0.019 grdn:0.178 lr:4.8e-05 updt_s:1.887 data_s:0.027Training:  80%|▊| 15999/20000 [9:16:13<2:06:07,  1.89s/step, loss=0.020, lr=4.6eINFO 2025-07-11 05:34:35 ts/train.py:292 step:16K smpl:2M ep:17K epch:38.66 loss:0.019 grdn:0.179 lr:4.7e-05 updt_s:1.885 data_s:0.000INFO 2025-07-11 05:34:35 ts/train.py:301 Checkpoint policy after step 16000Training:  81%|▊| 16199/20000 [9:22:40<1:59:34,  1.89s/step, loss=0.016, lr=4.5eINFO 2025-07-11 05:41:01 ts/train.py:292 step:16K smpl:2M ep:17K epch:39.15 loss:0.019 grdn:0.174 lr:4.6e-05 updt_s:1.885 data_s:0.031Training:  82%|▊| 16399/20000 [9:28:58<1:53:22,  1.89s/step, loss=0.017, lr=4.4eINFO 2025-07-11 05:47:19 ts/train.py:292 step:16K smpl:2M ep:17K epch:39.63 loss:0.018 grdn:0.175 lr:4.5e-05 updt_s:1.886 data_s:0.000Training:  83%|▊| 16599/20000 [9:35:21<1:47:11,  1.89s/step, loss=0.019, lr=4.3eINFO 2025-07-11 05:53:42 ts/train.py:292 step:17K smpl:2M ep:17K epch:40.11 loss:0.018 grdn:0.172 lr:4.4e-05 updt_s:1.885 data_s:0.025Training:  84%|▊| 16799/20000 [9:41:38<1:40:42,  1.89s/step, loss=0.020, lr=4.2eINFO 2025-07-11 06:00:00 ts/train.py:292 step:17K smpl:2M ep:18K epch:40.60 loss:0.018 grdn:0.171 lr:4.3e-05 updt_s:1.886 data_s:0.000Training:  85%|▊| 16999/20000 [9:48:02<1:34:39,  1.89s/step, loss=0.015, lr=4.1eINFO 2025-07-11 06:06:24 ts/train.py:292 step:17K smpl:2M ep:18K epch:41.08 loss:0.018 grdn:0.167 lr:4.2e-05 updt_s:1.887 data_s:0.029Training:  86%|▊| 17199/20000 [9:54:20<1:28:03,  1.89s/step, loss=0.021, lr=4.0eINFO 2025-07-11 06:12:42 ts/train.py:292 step:17K smpl:2M ep:18K epch:41.56 loss:0.018 grdn:0.178 lr:4.1e-05 updt_s:1.886 data_s:0.000Training:  87%|▊| 17399/20000 [10:00:43<1:23:31,  1.93s/step, loss=0.017, lr=3.9INFO 2025-07-11 06:19:04 ts/train.py:292 step:17K smpl:2M ep:18K epch:42.05 loss:0.018 grdn:0.169 lr:4.0e-05 updt_s:1.885 data_s:0.025Training:  88%|▉| 17599/20000 [10:07:01<1:15:46,  1.89s/step, loss=0.017, lr=3.8INFO 2025-07-11 06:25:22 ts/train.py:292 step:18K smpl:2M ep:18K epch:42.53 loss:0.018 grdn:0.170 lr:3.9e-05 updt_s:1.886 data_s:0.000Training:  89%|▉| 17799/20000 [10:13:19<1:09:10,  1.89s/step, loss=0.017, lr=3.7INFO 2025-07-11 06:31:41 ts/train.py:292 step:18K smpl:2M ep:19K epch:43.01 loss:0.018 grdn:0.171 lr:3.8e-05 updt_s:1.888 data_s:0.000Training:  90%|▉| 17999/20000 [10:19:42<1:02:58,  1.89s/step, loss=0.016, lr=3.6INFO 2025-07-11 06:38:03 ts/train.py:292 step:18K smpl:2M ep:19K epch:43.50 loss:0.017 grdn:0.166 lr:3.7e-05 updt_s:1.884 data_s:0.027INFO 2025-07-11 06:38:03 ts/train.py:301 Checkpoint policy after step 18000Training:  91%|▉| 18199/20000 [10:26:03<56:41,  1.89s/step, loss=0.017, lr=3.5e-INFO 2025-07-11 06:44:25 ts/train.py:292 step:18K smpl:2M ep:19K epch:43.98 loss:0.017 grdn:0.165 lr:3.6e-05 updt_s:1.889 data_s:0.000Training:  92%|▉| 18399/20000 [10:32:27<50:29,  1.89s/step, loss=0.016, lr=3.4e-INFO 2025-07-11 06:50:48 ts/train.py:292 step:18K smpl:2M ep:19K epch:44.46 loss:0.017 grdn:0.163 lr:3.5e-05 updt_s:1.885 data_s:0.028Training:  93%|▉| 18599/20000 [10:38:45<44:06,  1.89s/step, loss=0.017, lr=3.3e-INFO 2025-07-11 06:57:06 ts/train.py:292 step:19K smpl:2M ep:19K epch:44.95 loss:0.017 grdn:0.164 lr:3.4e-05 updt_s:1.886 data_s:0.000Training:  94%|▉| 18799/20000 [10:45:08<37:47,  1.89s/step, loss=0.018, lr=3.2e-INFO 2025-07-11 07:03:29 ts/train.py:292 step:19K smpl:2M ep:20K epch:45.43 loss:0.017 grdn:0.161 lr:3.3e-05 updt_s:1.886 data_s:0.025Training:  95%|▉| 18999/20000 [10:51:25<31:27,  1.89s/step, loss=0.016, lr=3.1e-INFO 2025-07-11 07:09:47 ts/train.py:292 step:19K smpl:2M ep:20K epch:45.91 loss:0.017 grdn:0.159 lr:3.2e-05 updt_s:1.885 data_s:0.000Training:  96%|▉| 19199/20000 [10:57:48<25:15,  1.89s/step, loss=0.014, lr=3.0e-INFO 2025-07-11 07:16:10 ts/train.py:292 step:19K smpl:2M ep:20K epch:46.40 loss:0.016 grdn:0.158 lr:3.1e-05 updt_s:1.884 data_s:0.026Training:  97%|▉| 19399/20000 [11:04:06<18:57,  1.89s/step, loss=0.018, lr=3.0e-INFO 2025-07-11 07:22:28 ts/train.py:292 step:19K smpl:2M ep:20K epch:46.88 loss:0.017 grdn:0.163 lr:3.0e-05 updt_s:1.887 data_s:0.000Training:  98%|▉| 19599/20000 [11:10:30<12:36,  1.89s/step, loss=0.017, lr=2.9e-INFO 2025-07-11 07:28:52 ts/train.py:292 step:20K smpl:3M ep:20K epch:47.36 loss:0.016 grdn:0.160 lr:2.9e-05 updt_s:1.888 data_s:0.028Training:  99%|▉| 19799/20000 [11:16:48<06:19,  1.89s/step, loss=0.016, lr=2.8e-INFO 2025-07-11 07:35:10 ts/train.py:292 step:20K smpl:3M ep:21K epch:47.85 loss:0.016 grdn:0.155 lr:2.8e-05 updt_s:1.886 data_s:0.000Training: 100%|▉| 19999/20000 [11:23:11<00:01,  1.89s/step, loss=0.016, lr=2.7e-INFO 2025-07-11 07:41:32 ts/train.py:292 step:20K smpl:3M ep:21K epch:48.33 loss:0.016 grdn:0.156 lr:2.7e-05 updt_s:1.885 data_s:0.024INFO 2025-07-11 07:41:32 ts/train.py:301 Checkpoint policy after step 20000Training: 100%|█| 20000/20000 [11:23:14<00:00,  2.05s/step, loss=0.016, lr=2.7e-INFO 2025-07-11 07:41:36 ts/train.py:344 Training metrics saved to: /home/vipuser/outputs/smolvla/training_metrics.csvINFO 2025-07-11 07:41:36 ts/train.py:348 End of training
```
