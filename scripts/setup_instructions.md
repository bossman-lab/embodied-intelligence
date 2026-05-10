# 环境安装指南

## Conda 环境

```bash
conda create -n embodied python=3.10
conda activate embodied
pip install mujoco==3.8.0
pip install genesis-world
pip install casadi==3.7.2
pip install stable-baselines3
pip install gym==0.26.2
pip install matplotlib scipy numpy
```

## 远程访问

SSH 免密配置（Windows 管理员账户）：
1. 在 C:\ProgramData\ssh\administrators_authorized_keys 中写入公钥
2. 权限设为仅 SYSTEM 和 Administrators 可读
3. 重启 sshd 服务

## 运行实验

```bash
# 设置 headless 模式
set MPLBACKEND=Agg

# Ch01 UR5e 抓取
python examples/01_hello_every_embodied_mujoco.py --headless --autoplay --autoplay-rounds 1

# Ch02 Cartpole LQR
python chapters/cartpole-LQR.py

# Ch02 Cartpole PID
python chapters/cartpole-PID.py

# Ch02 Cartpole MPC
python chapters/cartpole_MPC.py

# Ch05 Cartpole PPO
python chapters/ppo_cartpole.py
```
