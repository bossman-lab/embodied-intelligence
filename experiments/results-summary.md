# 实验记录汇总

## ✅ 已跑通实验

### UR5e 机械臂抓取
- **环境**: MuJoCo 仿真
- **实现**: 逆运动学求解 + 抓取规划
- **状态**: ✅ 运行成功
- **位置**: `examples/01_hello_every_embodied_mujoco.py`

### Cartpole 控制算法对比
| 算法 | 状态 | 说明 |
|:-----|:----:|:-----|
| PID 控制 | ✅ | 经典比例-积分-微分控制，收敛稳定 |
| LQR 控制 | ✅ | 线性二次型最优调节器 |
| MPC 控制 | ✅ | 模型预测控制，滚动时域优化 |
| PPO 强化学习 | ✅ | Stable-Baselines3 实现，策略梯度 |

### Genesis + MuJoCo 环境
| 组件 | 版本 | 状态 |
|:-----|:----:|:-----|
| Genesis | 0.4.6 | ✅ 安装配置完成 |
| MuJoCo | 3.8.0 | ✅ 兼容运行 |

### Ch07 video2robot (进行中)
| 模块 | 状态 | 说明 |
|:-----|:----:|:-----|
| PromptHMR 克隆 | ✅ | 658 files |
| GMR 下载 | ⏳ | 347MB (含权重)，传输中 |
| pip 依赖安装 | ⏳ | fastapi, viser, trimesh 等 |
| SMPL-X 模型 | ⏸️ | 需注册 smpl-x.is.tue.mpg.de |
| Seedance API | ⏸️ | 需注册 seedanceapi.org |
| Patches 应用 | ⏳ | 3 patches 待执行 |

## 🚫 经评估不推荐在 T2 上运行

| 项目 | 原因 |
|:-----|:------|
| OpenVLA 训练 | 需要 NVIDIA GPU (CUDA)，Radeon 890M 不支持 |
| 大规模 RL 训练 | CPU 推理速度慢，无法满足 RL 采样需求 |
| Genesis GPU 仿真 | 依赖 CUDA 加速 |

## 🔧 修复补丁

| 补丁 | 解决 |
|:-----|:-----|
| [`patches/cartpole_env_render.patch`](../patches/cartpole_env_render.patch) | gymnasium 0.26+ render 兼容性 |
| [`patches/font_setup.patch`](../patches/font_setup.patch) | Matplotlib 中文显示 |

## 📊 硬件性能数据 (极夜 T2, HX370)

| 任务 | CPU 利用率 | 耗时 | 备注 |
|:-----|:----------:|:----:|:-----|
| PPO Cartpole 训练 (100k steps) | ~30% | ~2min | CPU only |
| UR5e IK 求解 (单次) | <5% | <50ms | 轻量计算 |
| Genesis env 创建 | ~20% | ~3s | 首次加载 |
| git clone PromptHMR | ~10% | ~3min | 受网络影响 |

## ⚠️ 环境修复记录

### 修复 1: Gym render 模式
- **问题**: `gymnasium>=0.26` 移除了 `render(mode='rgb_array')`
- **修复**: 降级到 `gym==0.25.2` 或使用 `render_mode` 参数
- **Patch**: [`cartpole_env_render.patch`](../patches/cartpole_env_render.patch)

### 修复 2: Matplotlib 中文
- **问题**: 系统中文字体缺失，图表标签显示为方块
- **修复**: 显式指定中文字体路径
- **Patch**: [`font_setup.patch`](../patches/font_setup.patch)

### 修复 3: Conda 创建编码
- **问题**: Windows 遇到 `UnicodeDecodeError`
- **修复**: 设置 `set PYTHONUTF8=1`

### 修复 4: 金山毒霸误删
- **问题**: 毒霸将 python.exe 识别为木马
- **修复**: 添加白名单或安装时关闭实时防护
