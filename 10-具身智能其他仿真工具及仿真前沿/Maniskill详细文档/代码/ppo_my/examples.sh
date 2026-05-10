#!/bin/bash
# 这是一个稳定版PPO算法的示例命令集合
# 以下命令针对数值稳定性进行了优化

### 稳定版状态空间PPO ###

# PushCube - 最简单的任务，通常只需几分钟就能在GPU上训练
python ppo_my.py --env_id="PushCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=2_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25 --eval_freq=10 --num-steps=20

# PickCube - 稍复杂，通常需要5-10分钟在GPU上训练
python ppo_my.py --env_id="PickCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=10_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PushT - 推T形物体任务
python ppo_my.py --env_id="PushT-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --num-steps=100 --num_eval_steps=100 --gamma=0.99 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# StackCube - 堆叠方块任务
python ppo_my.py --env_id="StackCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PickSingleYCB - 抓取单个YCB对象
python ppo_my.py --env_id="PickSingleYCB-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PegInsertionSide - 插入钉子任务
python ppo_my.py --env_id="PegInsertionSide-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=250_000_000 --num-steps=100 --num-eval-steps=100 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# 使用双机器人的任务
python ppo_my.py --env_id="TwoRobotPickCube-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=20_000_000 --num-steps=100 --num-eval-steps=100 \
   --learning_rate=1e-4 --max_grad_norm=0.25

python ppo_my.py --env_id="TwoRobotStackCube-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=40_000_000 --num-steps=100 --num-eval-steps=100 \
   --learning_rate=1e-4 --max_grad_norm=0.25

# 三指机器人任务
python ppo_my.py --env_id="TriFingerRotateCubeLevel0-v1" \
   --num_envs=128 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=50_000_000 --num-steps=250 --num-eval-steps=250 \
   --learning_rate=1e-4 --max_grad_norm=0.25

# PokeCube - 轻推方块任务
python ppo_my.py --env_id="PokeCube-v1" --update_epochs=4 --num_minibatches=32 \
  --num_envs=1024 --total_timesteps=5_000_000 --eval_freq=10 --num-steps=20 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# CartPole平衡任务
python ppo_my.py --env_id="MS-CartpoleBalance-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=4_000_000 --num-steps=250 --num-eval-steps=1000 \
   --gamma=0.99 --gae_lambda=0.95 --learning_rate=1e-4 --max_grad_norm=0.25 \
   --eval_freq=5

# CartPole摆动上升任务
python ppo_my.py --env_id="MS-CartpoleSwingUp-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=10_000_000 --num-steps=250 --num-eval-steps=1000 \
   --gamma=0.99 --gae_lambda=0.95 --learning_rate=1e-4 --max_grad_norm=0.25 \
   --eval_freq=5

# Ant行走任务
python ppo_my.py --env_id="MS-AntWalk-v1" --num_envs=1024 --eval_freq=10 \
  --update_epochs=4 --num_minibatches=32 --total_timesteps=20_000_000 \
  --num_eval_steps=1000 --num_steps=200 --gamma=0.97 --ent_coef=1e-3 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# Ant奔跑任务
python ppo_my.py --env_id="MS-AntRun-v1" --num_envs=1024 --eval_freq=10 \
  --update_epochs=4 --num_minibatches=32 --total_timesteps=20_000_000 \
  --num_eval_steps=1000 --num_steps=200 --gamma=0.97 --ent_coef=1e-3 \
  --learning_rate=1e-4 --max_grad_norm=0.25

### 评估命令示例 ###

# 评估PushCube任务
python ppo_my.py --env_id="PushCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000

# 评估PickCube任务
python ppo_my.py --env_id="PickCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000
