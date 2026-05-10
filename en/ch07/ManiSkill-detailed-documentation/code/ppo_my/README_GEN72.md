# GEN72-EG2 Robot and Stable PPO Integration Guide

This document describes how to use the GEN72-EG2 robot in the ManiSkill environment and train it using the stable PPO algorithm.

## 1. GEN72-EG2 Robot Introduction

GEN72-EG2 is a combination of a 7-degree-of-freedom robotic arm and an EG2 gripper, with the following main features:

- 7-degree-of-freedom robotic arm for flexible movement
- Equipped with EG2 two-finger gripper for object grasping
- Optimized physical parameters and controllers for ManiSkill environment
- Preset multiple initial poses suitable for different tasks

## 2. File Description

This integration includes the following files:

1. `register_gen72_robot.py` - Registers GEN72-EG2 to the ManiSkill environment
2. `run_gen72_ppo.sh` - Script for training and evaluation
3. `ppo_my.py` - Stable PPO implementation (located in the upper directory)

URDF file location: `/home/kewei/17robo/ManiSkill/urdf_01/GEN72-EG2.urdf`

## 3. Usage Steps

### 1. Register the Robot

First, you need to register the GEN72-EG2 robot to the ManiSkill environment:

```bash
cd /home/kewei/17robo/ManiSkill/examples/baselines/ppo_my
python register_gen72_robot.py
```

### 2. Train and Evaluate Using Shell Script

We provide a convenient shell script for training and evaluation:

```bash
# Grant execution permission to the script
chmod +x run_gen72_ppo.sh

# Train PushCube task (stable configuration)
./run_gen72_ppo.sh train PushCube-v1 stable

# Preset quick training for PushCube task
./run_gen72_ppo.sh push-cube

# Preset PickCube task (stable configuration)
./run_gen72_ppo.sh pick-cube

# Evaluate trained model
./run_gen72_ppo.sh evaluate PushCube-v1 ./runs/PushCube-v1__ppo_my__1__1234567890/final_ckpt.pt
```

### 3. Directly Use Python Script

For more custom options, you can directly use the Python script:

```bash
# Ensure the robot is registered first
python register_gen72_robot.py

# Train using stable PPO
python ppo_my.py \
    --robot_uids="gen72_eg2_robot" \
    --env_id="PushCube-v1" \
    --control_mode="pd_joint_delta_pos" \
    --num_envs=128 \
    --total_timesteps=10000000 \
    --learning_rate=5e-5 \
    --max_grad_norm=0.25 \
    --update_epochs=4 \
    --num_minibatches=4 \
    --eval_freq=10
```

## 4. Training Configuration Description

Four preset training configurations are provided:

1. **Default configuration** (`default`)
   - Suitable for general training
   - Balanced performance and stability

2. **Stable configuration** (`stable`)
   - Improved numerical stability
   - Smaller learning rate and gradient clipping
   - Suitable for avoiding NaN issues

3. **Ultra-stable configuration** (`ultra-stable`)
   - Extremely conservative parameter settings
   - Very small learning rate and gradient clipping
   - Efficient operation on single GPU
   - Suitable for severe numerical instability issues

4. **Fast configuration** (`fast`)
   - Prioritizes training speed
   - Larger number of parallel environments
   - Suitable for rapid prototype validation

## 5. Physical Parameter Configuration

The physical parameters of GEN72-EG2 have been optimized, focusing on:

- **Gripper friction**: High static and dynamic friction coefficients (2.0) for better grasping
- **Elasticity coefficient**: Set to 0 to reduce bouncing effects
- **Control parameters**:
  - Arm stiffness: 1e3
  - Arm damping: 1e2
  - Arm force limit: 100

## 6. Control Modes

Multiple control modes are supported:

1. `pd_joint_delta_pos` - Joint position delta control (recommended for RL)
2. `pd_joint_pos` - Joint position control
3. `pd_ee_delta_pos` - End effector position delta control
4. `pd_ee_delta_pose` - End effector pose delta control

## 7. Common Issues

1. **NaN issues**: If NaNs occur during training, try using `stable` or `ultra-stable` configurations.
2. **Performance issues**: Adjust the `num_envs` parameter to match your GPU memory.
3. **Gripper control**: The gripper is controlled through simulated joints, with values ranging from 0.0 (closed) to 0.04 (open).

## 8. Reference Resources

- ManiSkill documentation: https://maniskill.readthedocs.io/
- Original PPO paper: https://arxiv.org/abs/1707.06347