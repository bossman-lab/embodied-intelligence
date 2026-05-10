# GEN72-EG2 机器人与稳定版PPO集成指南

本文档介绍如何在ManiSkill环境中使用GEN72-EG2机器人，并通过稳定版PPO算法进行训练。

## 一、GEN72-EG2机器人简介

GEN72-EG2是一款7自由度机械臂与EG2夹爪的组合，其主要特点包括：

- 7自由度机械臂，运动灵活
- 带有EG2双指夹爪，可用于抓取物体
- 已针对ManiSkill环境优化的物理参数和控制器
- 预设了多种适合不同任务的初始姿态

## 二、文件说明

本集成包含以下文件：

1. `register_gen72_robot.py` - 将GEN72-EG2注册到ManiSkill环境
2. `run_gen72_ppo.sh` - 用于训练和评估的脚本
3. `ppo_my.py` - 稳定版PPO实现（位于上层目录）

URDF文件位置：`/home/kewei/17robo/ManiSkill/urdf_01/GEN72-EG2.urdf`

## 三、使用步骤

### 1. 注册机器人

首先需要注册GEN72-EG2机器人到ManiSkill环境：

```bash
cd /home/kewei/17robo/ManiSkill/examples/baselines/ppo_my
python register_gen72_robot.py
```

### 2. 使用Shell脚本训练与评估

我们提供了便捷的Shell脚本用于训练和评估：

```bash
# 赋予脚本执行权限
chmod +x run_gen72_ppo.sh

# 训练PushCube任务（稳定配置）
./run_gen72_ppo.sh train PushCube-v1 stable

# 预设的快速训练PushCube任务
./run_gen72_ppo.sh push-cube

# 预设的PickCube任务（稳定配置）
./run_gen72_ppo.sh pick-cube

# 评估训练好的模型
./run_gen72_ppo.sh evaluate PushCube-v1 ./runs/PushCube-v1__ppo_my__1__1234567890/final_ckpt.pt
```

### 3. 直接使用Python脚本

如果需要更多自定义选项，可以直接使用Python脚本：

```bash
# 确保先注册了机器人
python register_gen72_robot.py

# 使用稳定版PPO训练
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

## 四、训练配置说明

提供了四种预设的训练配置：

1. **默认配置** (`default`)
   - 适合一般性训练
   - 均衡的性能和稳定性

2. **稳定配置** (`stable`)
   - 提高数值稳定性
   - 较小的学习率和梯度裁剪
   - 适合避免NaN问题

3. **超稳定配置** (`ultra-stable`)
   - 极度保守的参数设置
   - 非常小的学习率和梯度裁剪
   - 单GPU上也可以高效运行
   - 适合严重的数值不稳定问题

4. **快速配置** (`fast`)
   - 优先考虑训练速度
   - 较大的并行环境数量
   - 适合快速原型验证

## 五、物理参数配置

GEN72-EG2的物理参数经过优化，重点包括：

- **夹爪摩擦力**：设置了较高的静态和动态摩擦系数（2.0）以便于抓取物体
- **弹性系数**：设置为0以减少弹跳效果
- **控制参数**：
  - 机械臂刚度：1e3
  - 机械臂阻尼：1e2
  - 机械臂力限制：100

## 六、控制模式

支持多种控制模式：

1. `pd_joint_delta_pos` - 关节位置增量控制（推荐用于RL）
2. `pd_joint_pos` - 关节位置控制
3. `pd_ee_delta_pos` - 末端执行器位置增量控制
4. `pd_ee_delta_pose` - 末端执行器姿态增量控制

## 七、常见问题

1. **NaN问题**：如果训练过程中出现NaN，尝试使用`stable`或`ultra-stable`配置。
2. **性能问题**：调整`num_envs`参数以适应GPU内存。
3. **夹爪控制**：夹爪通过模拟关节控制，值范围为0.0（闭合）到0.04（打开）。

## 八、参考资源

- ManiSkill文档: https://maniskill.readthedocs.io/
- 原始PPO论文: https://arxiv.org/abs/1707.06347 