# 具身智能学习与实践 🦾

> 从零开始在 Windows 迷你主机上搭建具身智能（Embodied AI）实验环境，跑通 every-embodied 课程全部可执行实验

## 📋 概述

本项目记录在 **极夜 T2（Ryzen AI 9 HX370 / 96GB / Radeon 890M）** 上搭建具身智能开发环境的完整过程，包含：

- every-embodied 课程的全部实验代码与结果
- 环境搭建中的踩坑记录与解决方案
- 从 MuJoCo 仿真到 MPC 最优控制、PPO 强化学习的实战

## 🏗 环境架构

```
Telegram → OpenClaw Gateway → embodied_run.py → SSH → T2 (Win11)
                                                          ├── MuJoCo 3.8.0
                                                          ├── Genesis 0.4.6
                                                          ├── CasADi 3.7.2
                                                          ├── stable-baselines3
                                                          ├── LM Studio (GLM-4.7-Flash ~24 tok/s)
                                                          └── gym 0.26.2
```

## 📊 实验结果

| 章节 | 实验 | 结果 |
|:----|:----|:----:|
| Ch01 | UR5e 机械臂抓取 UR5e 机械臂抓取 | ✅ **1/1 (100%)** |
| Ch02 | Cartpole LQR 控制 | ✅ 完成 |
| Ch02 | Cartpole PID 控制 | ✅ 完成 |
| Ch02 | Cartpole MPC 最优控制 | ✅ **稳定到 0.007 rad** |
| Ch05 | Cartpole PPO 强化学习 | ✅ **平均奖励 485.7/500** |
| Ch06 | VLA MuJoCo 仿真环境 | ✅ 650步仿真引擎就绪 |

## 🎯 可运行实验

| 章节 | 路径 | 描述 |
|:----|:----|:-----|
| Ch01 | `examples/01_hello_every_embodied_mujoco.py` | UR5e 机械臂抓取方块 |
| Ch02 | `chapters/cartpole-LQR.py` | 线性二次型最优调节器 |
| Ch02 | `chapters/cartpole-PID.py` | 比例积分微分控制 |
| Ch02 | `chapters/cartpole_MPC.py` | 模型预测控制 |
| Ch05 | `chapters/ppo_cartpole.py` | PPO 强化学习训练 |
| Ch06 | `chapters/mujoco_env/` | VLA 仿真环境 |

## 🔧 环境搭建

### 硬件环境

| 组件 | 参数 |
|:----|:----|
| CPU | AMD Ryzen AI 9 HX370 (12核/24线程) |
| RAM | 96GB DDR5 |
| GPU | AMD Radeon 890M (iGPU) |
| 系统 | Windows 11 |
| 网络 | 192.168.3.x LAN |

### 软件环境

```bash
conda create -n embodied python=3.10
conda activate embodied
pip install mujoco==3.8.0
pip install genesis-world
pip install casadi
pip install stable-baselines3
pip install gym==0.26.2
```

### 远程访问

SSH 免密登录（管理员授权密钥）：
```
C:\ProgramData\ssh\administrators_authorized_keys
```

桥接脚本 `embodied_run.py` 通过 SSH key + paramiko 实现 Hermes 服务器 → T2 的代码执行。

## 🐛 踩坑记录

详见 [T2 具身智能环境搭建全记录](./blog/t2-embodied-journey.md)

核心问题：
- 🔴 中文乱码（GBK vs UTF-8）
- 🔴 Matplotlib 无 display（设 MPLBACKEND=Agg）
- 🔴 gym 0.26 移除 rendering 模块（重写 render 方法）
- 🔴 中文字体缺失（注释掉 font_manager.addfont）
- 🔴 代理配置导致 GitHub 克隆失败

## 📝 许可证

MIT
