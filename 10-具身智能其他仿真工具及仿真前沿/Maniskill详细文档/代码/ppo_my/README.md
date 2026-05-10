# 稳定版 PPO 算法实现

这个目录包含了一个针对ManiSkill环境优化的稳定版PPO算法实现。该实现基于原始PPO实现（来自[CleanRL](https://github.com/vwxyzjn/cleanrl/)和[LeanRL](https://github.com/pytorch-labs/LeanRL/)），但增加了许多数值稳定性的改进。

## 关键特性

相比原始PPO实现，稳定版PPO具有以下改进：

1. **增强数值稳定性**
   - 自动检测和处理训练过程中的NaN值
   - 梯度范数监控和限制
   - 行动和值函数的边界限制
   - 降低学习率和更保守的网络初始化
   - 更小的更新轮次（4而不是8）以减少过拟合

2. **自动错误恢复**
   - 当检测到大量NaN值时进行紧急检查点保存
   - 异常梯度检测与处理
   - 自动在日志中记录稳定性指标

3. **易用性增强**
   - 中文注释和更详细的参数说明
   - 默认参数针对稳定性进行了优化
   - 更加清晰的日志输出

## 使用方法

以下是几个常见任务的使用示例：

### PushCube 任务（最简单的任务）

```bash
python ppo_my.py --env_id="PushCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=2_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25 --eval_freq=10 --num-steps=20
```

### 评估训练好的模型

```bash
python ppo_my.py --env_id="PushCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000
```

### 使用稳定性参数

为了获得最佳稳定性，推荐使用以下参数：

- `--learning_rate=1e-4`：较低的学习率提高稳定性
- `--max_grad_norm=0.25`：更严格的梯度裁剪阈值
- `--update_epochs=4`：减少过拟合
- `--detect_anomaly=True`：开启PyTorch梯度异常检测（会略微降低性能）

更多示例命令可以在`examples.sh`文件中找到。

## 注意事项

- 由于增加了稳定性检查，训练速度可能比原始实现略慢
- 对于特别复杂的任务，可能需要进一步调整参数
- 如果遇到持续的NaN问题，可以尝试进一步降低学习率或减小网络规模

## 支持的环境

稳定版PPO支持所有ManiSkill环境，包括：

- 推/拾取方块类任务：PushCube, PickCube, StackCube
- 机械臂任务：PegInsertionSide
- 多机器人任务：TwoRobotPickCube, TwoRobotStackCube
- 运动控制任务：MS-AntWalk, MS-CartpoleBalance
- 以及其他ManiSkill环境

## 引用

如果使用这个稳定版PPO实现，请引用原始PPO论文：

```
@article{DBLP:journals/corr/SchulmanWDRK17,
  author       = {John Schulman and
                  Filip Wolski and
                  Prafulla Dhariwal and
                  Alec Radford and
                  Oleg Klimov},
  title        = {Proximal Policy Optimization Algorithms},
  journal      = {CoRR},
  volume       = {abs/1707.06347},
  year         = {2017},
  url          = {http://arxiv.org/abs/1707.06347},
  eprinttype    = {arXiv},
  eprint       = {1707.06347},
  timestamp    = {Mon, 13 Aug 2018 16:47:34 +0200},
  biburl       = {https://dblp.org/rec/journals/corr/SchulmanWDRK17.bib},
  bibsource    = {dblp computer science bibliography, https://dblp.org}
}
```