#!/bin/bash
# Stable PPO commands optimized for numerical stability
# All commands below are tuned for stable training on state-space tasks

### Stable State-Space PPO ###

# PushCube – simplest task; usually converges in minutes on a GPU
python ppo_my.py --env_id="PushCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=2_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25 --eval_freq=10 --num-steps=20

# PickCube – slightly harder; 5–10 min on a GPU
python ppo_my.py --env_id="PickCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=10_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PushT – push a T-shaped object
python ppo_my.py --env_id="PushT-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --num-steps=100 --num_eval_steps=100 --gamma=0.99 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# StackCube – stack cubes
python ppo_my.py --env_id="StackCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PickSingleYCB – pick a single YCB object
python ppo_my.py --env_id="PickSingleYCB-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=25_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25

# PegInsertionSide – peg-in-hole task
python ppo_my.py --env_id="PegInsertionSide-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=250_000_000 --num-steps=100 --num-eval-steps=100 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# Dual-arm tasks
python ppo_my.py --env_id="TwoRobotPickCube-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=20_000_000 --num-steps=100 --num-eval-steps=100 \
   --learning_rate=1e-4 --max_grad_norm=0.25

python ppo_my.py --env_id="TwoRobotStackCube-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=40_000_000 --num-steps=100 --num-eval-steps=100 \
   --learning_rate=1e-4 --max_grad_norm=0.25

# TriFinger cube-rotation tasks
python ppo_my.py --env_id="TriFingerRotateCubeLevel0-v1" \
   --num_envs=128 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=50_000_000 --num-steps=250 --num-eval-steps=250 \
   --learning_rate=1e-4 --max_grad_norm=0.25

# PokeCube – gentle nudges
python ppo_my.py --env_id="PokeCube-v1" --update_epochs=4 --num_minibatches=32 \
  --num_envs=1024 --total_timesteps=5_000_000 --eval_freq=10 --num-steps=20 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# CartPole balance
python ppo_my.py --env_id="MS-CartpoleBalance-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=4_000_000 --num-steps=250 --num-eval-steps=1000 \
   --gamma=0.99 --gae_lambda=0.95 --learning_rate=1e-4 --max_grad_norm=0.25 \
   --eval_freq=5

# CartPole swing-up
python ppo_my.py --env_id="MS-CartpoleSwingUp-v1" \
   --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
   --total_timesteps=10_000_000 --num-steps=250 --num-eval-steps=1000 \
   --gamma=0.99 --gae_lambda=0.95 --learning_rate=1e-4 --max_grad_norm=0.25 \
   --eval_freq=5

# Ant locomotion – walk
python ppo_my.py --env_id="MS-AntWalk-v1" --num_envs=1024 --eval_freq=10 \
  --update_epochs=4 --num_minibatches=32 --total_timesteps=20_000_000 \
  --num_eval_steps=1000 --num_steps=200 --gamma=0.97 --ent_coef=1e-3 \
  --learning_rate=1e-4 --max_grad_norm=0.25

# Ant locomotion – run
python ppo_my.py --env_id="MS-AntRun-v1" --num_envs=1024 --eval_freq=10 \
  --update_epochs=4 --num_minibatches=32 --total_timesteps=20_000_000 \
  --num_eval_steps=1000 --num_steps=200 --gamma=0.97 --ent_coef=1e-3 \
  --learning_rate=1e-4 --max_grad_norm=0.25

### Evaluation Examples ###

# Evaluate PushCube
python ppo_my.py --env_id="PushCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000

# Evaluate PickCube
python ppo_my.py --env_id="PickCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000