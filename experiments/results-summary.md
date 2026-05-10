# 实验结果汇总

## Ch01 - UR5e 抓取
- 脚本: examples/01_hello_every_embodied_mujoco.py
- 结果: 1/1 (100%) 成功抓取
- 耗时: ~60s

## Ch02 - Cartpole PID
- 脚本: chapters/cartpole-PID.py
- 参数: kp_cart=2, kd_cart=50, kp_pole=8, kd_pole=100
- 结果: 400步完成后保存 PID.png (507KB)

## Ch02 - Cartpole LQR
- 脚本: chapters/cartpole-LQR.py
- 方法: 求解代数黎卡提方程 (scipy.linalg)
- 结果: 完成后保存 LQR.png (654KB)

## Ch02 - Cartpole MPC
- 脚本: chapters/cartpole_MPC.py
- 求解器: CasADi + Ipopt
- 参数: Prediction horizon N=50
- 结果: 200步/17s, 稳定到 0.007 rad

## Ch05 - Cartpole PPO
- 训练: stable-baselines3 PPO
- 结果: 平均奖励 485.7/500
- 安装: pip install stable-baselines3 tensorboard

## Ch06 - VLA 仿真环境
- MuJoCo Franka 7-DOF 臂 + 红色方块
- 650步仿真引擎就绪
- 训练需 NVIDIA GPU
