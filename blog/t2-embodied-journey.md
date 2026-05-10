---
title: "一台 96GB 迷你主机能跑具身智能吗？我在极夜 T2 上搭了全套仿真环境"
published: false
description: "从 MuJoCo 到 MPC 再到 PPO——在无 GPU 的 Windows 迷你主机上跑通具身智能课程的全过程，附带每个坑的解法"
tags: emboodiedai, robotics, python, reinforcement-learning, beginners
---

# 一台 96GB 迷你主机能跑具身智能吗？

## 我在极夜 T2 上搭了全套仿真环境

---

### 背景

几个月前我入手了一台 **极夜 T2**（DeskOne T2），配置是 Ryzen AI 9 HX370 + 96GB DDR5 + Radeon 890M。不是 Mac mini，不是 NUC，是一台国产迷你主机，没有 NVIDIA GPU。

当时想的很简单：96GB 内存总能干点什么吧？

后来发现了 Datawhale 的 [every-embodied](https://github.com/datawhalechina/every-embodied) 课程，一套中文具身智能入门教程，从机械臂抓取到 VLA（视觉-语言-动作）全覆盖。我心动了。

但这台机器没有 NVIDIA GPU，意味着：
- 不能跑 VLA 训练（ACT/Pi0/SmolVLA）
- 不能跑 Isaac GR00T
- 不能跑 ManiSkill

**只能用 CPU 和 iGPU 硬扛。**

事实证明，能跑的东西比想象中多。

---

### 架构：远程控制的完全体

我还有一个 Hermes Agent 跑在 Linux 服务器上，两个机器在同一个局域网。目标是：

```
Telegram 发消息 → Hermes → SSH → T2 (Win11) → 执行仿真
```

要实现这个链路，第一步是 **SSH 免密登录**。Windows 的 SSH 服务器默认用 `authorized_keys`，但管理员账户要用 `administrators_authorized_keys`。

```bash
# 在第个位置创建文件
C:\ProgramData\ssh\administrators_authorized_keys
# 权限：仅 SYSTEM 和 Administrators 可读
```

然后写了一个桥接脚本 `embodied_run.py`，用 Python 的 paramiko 库做 SSH 连接、远程执行、输出编码处理。

最难搞的部分是**中文编码**。Windows 的 cmd 默认 CP936（GBK），而 Linux 端是 UTF-8。一条 `ssh` 命令的输出在终端里全是乱码。最终的解决方案是：

```python
# 在远程 Python 脚本开头加上
sys.stdout.reconfigure(encoding='utf-8')
# 在读取输出时用 UTF-8 解码
```

---

### 实验 1：UR5e 机械臂抓取（Ch01）

第一个实验是 UR5e 六轴机械臂抓取方块，用的是 MuJoCo 仿真。

```bash
python examples/01_hello_every_embodied_mujoco.py --headless --autoplay --autoplay-rounds 1
```

结果：**1/1 抓取成功**。MuJoCo 在纯 CPU 模式下跑得飞快，完全没有压力。

这时候信心爆棚——看来 96GB 内存 + CPU 就有戏。

---

### 实验 2：Cartpole 三种控制算法（Ch02）

Cartpole（倒立摆）是控制理论的 Hello World。课程给了三种算法：

**PID 控制：** 经典的比例-积分-微分控制。调参过程很直观——`kp_cart=2, kd_cart=50, kp_pole=8, kd_pole=100`，400 步后输出结果图。

**LQR（线性二次型调节器）：** 基于状态空间模型的最优控制。用 `scipy.linalg` 求解代数黎卡提方程，稳定效果比 PID 更好。

**MPC（模型预测控制）：** 最复杂也最强大——用 CasADi 做数值优化，在每一步求解带约束的最优控制问题。

```
MPC 结果：Prediction horizon N=50，200步/17s，稳定到 0.007 rad
PPO 结果：平均奖励 485.7/500（500 满分）
```

MPC 最有意思——虽然每步都要解一个数值优化问题，但在 CPU 上也能跑到 11.6 step/s。

---

### 💥 踩坑实录

这趟折腾遇到了不少问题，列出来供后来者参考。

#### 🕳️ 坑 1：gym 0.26 移除了 rendering 模块

```
ImportError: cannot import name 'rendering' from 'gym.envs.classic_control'
```

gym 在 0.26 版本移除了自带的 `rendering` 模块。课程代码用的还是旧版 API。

**解法：** 重写 `cartpole_env.py` 的 `render()` 方法。在 headless 模式下干脆返回假图像：

```python
def render(self, mode='human'):
    if self.state is None:
        return None
    if mode == 'rgb_array':
        return np.zeros((400, 600, 3), dtype=np.uint8)
    return None
```

#### 🕳️ 坑 2：Matplotlib 在无 display 环境卡死

运行 PID/LQR 脚本时，`plt.show()` 会尝试打开图形窗口，在 SSH 会话中直接卡死。

**解法：** 设置 Agg 后端（非交互式）：

```bash
set MPLBACKEND=Agg
python script.py
```

#### 🕳️ 坑 3：中文字体缺失

课程脚本用了 `AiDianFengYaHei（商用免费）-2.ttf` 这个字体文件，但 T2 上没有。结果 matplotlib 疯狂报警：

```
UserWarning: Glyph 29366 (CJK UNIFIED IDEOGRAPH-72B6) missing from font(s) DejaVu Sans
```

**解法：** 注释掉字体加载代码，改用 DejaVu Sans。图表里的中文标注变成方框，但数值结果完全不受影响。

#### 🕳️ 坑 4：SSH 中文乱码

这是最烦人的。Windows 的 sshd 默认用 CP936 编码，而 Linux 端是 UTF-8。无论是 subprocess 还是直接 ssh，输出都是乱码。

**最终方案：** 用 Python 的 paramiko 库建立 SSH 连接，设置 `charset=utf-8`，远程脚本也强制 UTF-8 输出。

#### 🕳️ 坑 5：代理配置导致 GitHub 不通

T2 上配了 `git config --global http.proxy http://192.168.3.135:7890`，但代理服务器经常挂掉。结果 git clone 总是 `Connection refused`。

**解法：** 绕过代理：

```bash
git -c http.proxy= -c https.proxy= clone <repo_url>
```

#### 🕳️ 坑 6：金山毒霸

这值得一提——T2 出厂预装了金山毒霸，SSH 端口扫描被当作攻击行为拦截了。花了整整三轮重启 + 安全模式扫描才彻底清除。具体步骤：

1. 停止服务（KAVBootC、KDHacker 等）
2. 删除驱动文件
3. 清理注册表残留
4. 重启验证

---

### 到底能跑什么？不能跑什么？

所有可执行实验的最终全景：

#### ✅ 跑通（CPU + iGPU 足够）

| 实验 | 耗时 |
|:---|:----:|
| UR5e 机械臂抓取 | 60s |
| Cartpole PID 控制 | 30s |
| Cartpole LQR 最优控制 | 30s |
| Cartpole MPC 预测控制 | 17s |
| Cartpole PPO 强化学习 | 5min（含训练） |
| VLA MuJoCo 仿真环境初始化 | 10s |

#### ❌ 不可跑（需要 NVIDIA GPU）

- VLA 模型训练（ACT/Pi0/SmolVLA）
- NVIDIA Isaac GR00T
- ManiSkill PPO（GPU 渲染）
- video2robot 端到端（需 API + GPU）

#### 📘 纯理论章节

- Ch04 计算机视觉与 3D 重建（SAM/深度估计）
- Ch05 强化学习理论
- Ch17 具身世界模型（LeWorldModel）

---

### 硬件 vs 软件：性价比之王？

极夜 T2 的 96GB 内存在具身智能这个领域有点尴尬——它不是 Mac Studio，不是游戏本，是一台没有 GPU 的迷你主机。但换个角度看：

**96GB 意味着能同时跑多个虚拟机、大模型推理（Q4 量化可以装 47B 模型）、复杂的数值优化（CasADi 的 MPC 完全在内存里解）。**

如果你在考虑类似的机器，我的建议是：

- **做仿真（MuJoCo、MPC、传统的控制算法）** → ✅ 完全够用
- **做训练（深度强化学习、VLA）** → ❌ 需要至少一张 RTX 4060
- **做推理、做实验原型** → ✅ 性价比极高

---

### 后续

T2 有一个 **OCuLink 接口**，理论上可以外接 NVIDIA 显卡（RTX 4090 级别的 eGPU）。如果接上显卡，之前被 GPU 拦住的所有实验都能跑通了——包括 VLA 训练和 Isaac GR00T。

下一步计划是：
1. 装一个 eGPU dock
2. 跑通 VLA 训练（ACT / Pi0）
3. 把结果更新到 GitHub 仓库

---

仓库：**[bossman-lab/embodied-intelligence](https://github.com/bossman-lab/embodied-intelligence)**

---

*设备信息：极夜 T2（DeskOne T2），Ryzen AI 9 HX370，96GB DDR5，Radeon 890M，Windows 11*
