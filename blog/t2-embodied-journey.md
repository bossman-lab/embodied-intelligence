# 极夜T2（HX370）跑通 Every-Embodied 具身智能课程全记录

> 一台没有独立显卡的迷你主机，能跑多少具身智能？我的答案是：**远比想象的多**。

## 起点

我有一台 **极夜T2 (DeskOne T2)** 迷你主机 —— AMD Ryzen AI 9 HX370 (12C/24T)、96GB DDR5、Radeon 890M iGPU。没有 NVIDIA 显卡。

我开始学习 Datawhale 的 [every-embodied](https://github.com/datawhalechina/every-embodied) 课程，想看看这台机器能跑多远。

## 课程全景

课程从零到一覆盖具身智能全栈，共 **20 个章节，1300+ 文件**：

| # | 章节 | 核心内容 |
|:-:|:-----|:---------|
| 01 | 具身智能概述 | 发展史、技术栈 |
| 02 | 机器人控制 | UR5e、PID/LQR/MPC |
| 03 | 硬件实战 | LeRobot、RDK-X5 |
| 04 | 3D视觉 | 3D重建、NeRF |
| 05 | 强化学习 | DQN/PPO/SAC |
| 06 | VLA策略 | SmolVLA、OpenVLA、RT系列 |
| **07** | **运动控制** | **video2robot、PromptHMR、GMR** |
| 08 | 导航VLN | 视觉语言导航 |
| 10 | 仿真工具 | MuJoCo、Genesis、Isaac Sim |
| 16 | 专题学习 | 6大专题(524文件) |

完整仓库：**[bossman-lab/embodied-intelligence](https://github.com/bossman-lab/embodied-intelligence)**

## ✅ 已跑通实验

### UR5e 机械臂抓取仿真
第一个 demo — 在 MuJoCo 中运行 UR5e 机械臂的逆运动学求解与抓取。T2 的 HX370 处理这个绰绰有余。

### Cartpole 控制算法四连测
我在这台机器上完整跑了四种控制算法，对比结果一目了然：

| 算法 | 类型 | 表现 |
|:-----|:----:|:-----|
| **PID** | 经典控制 | 稳定收敛，调参简单 |
| **LQR** | 最优控制 | 比PID更平滑，有理论保证 |
| **MPC** | 预测控制 | 滚动优化，抗干扰强 |
| **PPO** | 强化学习 | 10万步训练~2分钟，零先验知识 |

PPO 能在 CPU-only 的 T2 上 2 分钟跑完 10 万步，出乎我的意料。虽然比不上 GPU（大概慢 3-5x），但对于学习和调试来说足够了。

### Genesis + MuJoCo 环境
Genesis 0.4.6 + MuJoCo 3.8.0 在 T2 上完美运行。作为物理引擎用于仿真和可视化没有任何问题。

## ⏳ Ch07 video2robot 搭建

目前正在搭建 text→video→pose→robot 端到端链路：
- ✅ PromptHMR 克隆 (658 files)
- ⏳ GMR 下载 (347MB，含权重)
- ⏳ pip 依赖安装
- ⏸️ 等待 SMPL-X 模型注册
- ⏸️ 等待 Seedance API Key

这个需要视频生成 API + 人体姿态模型 + SMPL-X body models，链路较长，但基础依赖都已就绪。

## 🐛 6 个踩坑实录

### 1️⃣ Gym render 兼容性
```
gymnasium>=0.26 移除了 render(mode='rgb_array')
→ 降级到 gym==0.25.2
```

### 2️⃣ Matplotlib 中文变方块
系统中文字体缺失，图表标签无法显示。

**解决**：显式指定字体路径，已提供 `font_setup.patch`

### 3️⃣ Conda 创建就报错
```
UnicodeDecodeError
```
Windows 编码问题，设置 `PYTHONUTF8=1` 环境变量解决。

### 4️⃣ 金山毒霸把 Python 当木马
没错，Miniconda 的 `python.exe` 被毒霸拦了。

**解决**：给毒霸加白名单，或者装的时候关实时防护。

### 5️⃣ 休眠 = 一切从头
T2 进入休眠后，所有后台进程中断、SSH 断开。pip install 到一半的依赖全部白费。

**解决**：关闭休眠，或者用 WOL 唤醒后检查进程状态。

### 6️⃣ GitHub Clone 像过山车
国内直连 GitHub 速度忽好忽坏。PrompHMR 克隆时直接失败了好几次。

**解决**：用代理（`-c http.proxy=http://127.0.0.1:7890`）或直接用 tarball + scp。

## 📊 T2 能跑 vs 不能跑

### ✅ 完全能跑
- 所有仿真环境（MuJoCo、Genesis）
- 经典控制算法（PID、LQR、MPC）
- 强化学习小规模训练（Cartpole PPO、简单环境）
- 3D 可视化（Viser、Trimesh、Open3D）
- 代码开发、调试、Notebook 实验

### ❌ 不适合
- **OpenVLA 等大模型训练** — 需要 NVIDIA GPU + CUDA
- **大规模 RL 训练** — CPU 推理速度是瓶颈
- **Genesis GPU 仿真** — 需要 CUDA 加速

### 💡 升级路径
T2 有 **OCuLink 端口**，可以外接 NVIDIA 显卡（如 RTX 4090），届时这台机器将可以跑通几乎所有内容。

## 学到的东西

1. **具身智能入门不一定要显卡** — 仿真、控制、基础 RL 都能在 CPU 上跑
2. **国产迷你主机的潜力** — HX370 的 CPU 性能足够承担多数开发和实验
3. **Windows 下做 ML 的坑是真多** — 编码、杀毒、休眠，每个都能卡你半天
4. **GitHub API push 比 git remote-https 靠谱** — 墙内开发者的生存技巧

## 仓库在这里

➡️ **[bossman-lab/embodied-intelligence](https://github.com/bossman-lab/embodied-intelligence)**

包含完整课程代码 + 所有补丁 + 硬件配置指南。欢迎 Star ⭐

---

*课程内容源自 [Datawhale every-embodied](https://github.com/datawhalechina/every-embodied)，CC BY 4.0。实战适配记录 by @bossman-lab。*
