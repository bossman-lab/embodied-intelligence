# Stable PPO Algorithm Implementation

This directory contains a stable implementation of the PPO algorithm optimized for ManiSkill environments. Based on the original PPO implementations from [CleanRL](https://github.com/vwxyzjn/cleanrl/) and [LeanRL](https://github.com/pytorch-labs/LeanRL/), this version includes numerous numerical stability improvements.

## Key Features

Compared to the original PPO implementation, the stable version offers:

1. **Enhanced Numerical Stability**
   - Automatic detection and handling of NaN values during training
   - Gradient norm monitoring and clipping
   - Action and value function boundary constraints
   - Reduced learning rate and more conservative network initialization
   - Fewer update epochs (4 instead of 8) to reduce overfitting

2. **Automatic Error Recovery**
   - Emergency checkpoint saving when excessive NaNs are detected
   - Abnormal gradient detection and handling
   - Automatic logging of stability metrics

3. **Improved Usability**
   - Chinese comments and detailed parameter explanations
   - Default parameters optimized for stability
   - Clearer log output

## Usage

Here are examples for common tasks:

### PushCube Task (Simplest Task)

```bash
python ppo_my.py --env_id="PushCube-v1" \
  --num_envs=1024 --update_epochs=4 --num_minibatches=32 \
  --total_timesteps=2_000_000 --learning_rate=1e-4 \
  --max_grad_norm=0.25 --eval_freq=10 --num-steps=20
```

### Evaluate Trained Model

```bash
python ppo_my.py --env_id="PushCube-v1" \
   --evaluate --checkpoint=path/to/model.pt \
   --num_eval_envs=1 --num-eval-steps=1000
```

### Using Stability Parameters

For optimal stability, we recommend the following parameters:

- `--learning_rate=1e-4`: Lower learning rate improves stability
- `--max_grad_norm=0.25`: More strict gradient clipping threshold
- `--update_epochs=4`: Reduces overfitting
- `--detect_anomaly=True`: Enables PyTorch gradient anomaly detection (slightly reduces performance)

More example commands can be found in the `examples.sh` file.

## Notes

- Training speed may be slightly slower than the original implementation due to added stability checks
- For particularly complex tasks, further parameter adjustments may be needed
- If persistent NaN issues occur, try further reducing the learning rate or network size

## Supported Environments

The stable PPO supports all ManiSkill environments, including:

- Push/Pick cube tasks: PushCube, PickCube, StackCube
- Manipulator tasks: PegInsertionSide
- Multi-robot tasks: TwoRobotPickCube, TwoRobotStackCube
- Motion control tasks: MS-AntWalk, MS-CartpoleBalance
- And other ManiSkill environments

## Citation

If you use this stable PPO implementation, please cite the original PPO paper:

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