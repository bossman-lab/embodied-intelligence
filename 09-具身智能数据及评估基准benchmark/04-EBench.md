# EBench / GenManip 复现记录：从环境配置到最小视频渲染

## 1 概述

EBench 是面向具身操作任务的评估基准，本次复现先不追求完整 benchmark 跑分，而是验证一条最小链路：安装 Isaac Sim 4.1 运行环境，启动 GenManip 的 `Minimal_Banana` 任务，完成规划、轨迹生成、RGB 渲染，并导出可播放视频。

本章记录的是一次 smoke test 级别复现。它能证明仿真、规划和渲染链路已经打通，但不代表完整 EBench 评测已经完成。

## 2 本次验证环境

远端机器使用 Ubuntu 22.04，GPU 为 RTX 4090。环境实际安装在数据盘，避免把大体积 Python 包和 Isaac 缓存写到共享盘。

| 项目 | 本次使用 |
| --- | --- |
| Python | 3.10 |
| Isaac Sim | 4.1.0.0 |
| NumPy | 1.26.4 |
| PyTorch | 2.4.0+cu121 |
| cuRobo | v0.7.8 |
| 任务入口 | `GenManip/configs/tasks/minimal.yml` |
| 输出任务 | `Minimal_Banana` |

关键结论是：如果只是跑 EBench/GenManip 的最小 smoke test，一张 24GB 显存的卡就足够。完整数据生成、批量评测或大模型 policy 部署会额外占用显存和存储，需要按任务规模重新估算。

## 3 环境配置要点

工作目录如下：

```bash
/root/gpufree-share/ebench_repro/GenManip
```

Python 环境放在数据盘：

```bash
/root/gpufree-data/ebench_repro/venv_ebench
```

基础依赖安装完成后，需要显式接受 Omniverse EULA，否则首次启动 Isaac Sim 会卡在交互提示：

```bash
export OMNI_KIT_ACCEPT_EULA=YES
export HF_HOME=/root/gpufree-data/hf_home
export TMPDIR=/root/gpufree-data/tmp
```

Isaac Sim 4.1 的 PyPI 包要求 Python 3.10。若使用 Python 3.11，会出现类似下面的版本不匹配：

```text
isaacsim 4.1.0.0 Requires-Python ==3.10.*
```

cuRobo 需要固定到旧版 API。GenManip 代码会导入：

```python
from curobo.geom.sdf.world import CollisionCheckerType
```

当前 cuRobo 主分支已经调整了包结构，因此本次固定为：

```bash
cd saved/envs/curobo
git checkout v0.7.8
pip install -e . --no-build-isolation
```

## 4 运行最小任务

进入 GenManip 根目录并激活环境：

```bash
cd /root/gpufree-share/ebench_repro/GenManip
source /root/gpufree-data/ebench_repro/venv_ebench/bin/activate
export OMNI_KIT_ACCEPT_EULA=YES
export HF_HOME=/root/gpufree-data/hf_home
export TMPDIR=/root/gpufree-data/tmp
```

先跑最小规划任务：

```bash
python demogen.py \
  --config configs/tasks/minimal.yml \
  --record minimal_planning
```

本次生成了 10 条 `Minimal_Banana` trajectory。单条 trajectory 目录中包含 `lmdb/data.mdb`、`info.json`、`meta_info.pkl` 等文件。

## 5 渲染视频

默认相机配置会开启 depth、semantic segmentation、2D/3D bbox 和 motion vector。该配置在本次 Isaac Sim 4.1 + 双 4090 环境中触发过 CUDA/Hydra 渲染错误：

```text
CUDA error 700: an illegal memory access was encountered
HydraEngine::render failed
Rendering failed
```

为了完成 smoke test，本次使用 RGB-only 渲染配置，并显式关闭 Isaac 多 GPU：

```python
simulation_app = SimulationApp(
    {
        "headless": True,
        "active_gpu": 0,
        "physics_gpu": 0,
        "multi_gpu": False,
        "max_gpu_count": 1,
    }
)
```

相机配置中关闭非 RGB annotator：

```yaml
with_distance: false
with_semantic: false
with_bbox2d: false
with_bbox3d: false
with_motion_vector: false
```

完整渲染命令：

```bash
python render_single_gpu.py \
  --config configs/tasks/minimal_rgb_only.yml \
  --without_depth \
  --record rgb_only_single_gpu_full
```

本次渲染结果为 316 帧 RGB，随后从 LMDB 解码成 MP4。三路相机视频如下。

<video controls muted preload="metadata" width="100%">
  <source src="assets/ebench/ebench_minimal_banana_obs_camera.mp4" type="video/mp4">
</video>

<video controls muted preload="metadata" width="100%">
  <source src="assets/ebench/ebench_minimal_banana_obs_camera_2.mp4" type="video/mp4">
</video>

<video controls muted preload="metadata" width="100%">
  <source src="assets/ebench/ebench_minimal_banana_realsense.mp4" type="video/mp4">
</video>

渲染时同步保存了一张俯视图：

<p align="center">
  <img src="./assets/ebench/ebench_minimal_banana_overhead.jpg" width="80%" />
  <br>
  <b>图1：Minimal_Banana 渲染俯视图</b>
</p>

## 6 已验证结果

本次 smoke test 已完成以下检查：

- Isaac Sim 4.1 可以在远端环境中启动。
- GenManip `Minimal_Banana` 任务可以完成 cuRobo 规划。
- 轨迹数据成功写入 LMDB。
- RGB-only 渲染可生成 316 帧图像。
- 三路相机视频均已导出为 MP4，分辨率为 640×480，帧率为 30 FPS。

## 7 常见问题

### 7.1 EULA 输入卡住

设置环境变量：

```bash
export OMNI_KIT_ACCEPT_EULA=YES
```

### 7.2 找不到 `curobo.geom`

使用 cuRobo `v0.7.8`，不要直接使用当前主分支。

### 7.3 默认渲染出现 CUDA/Hydra 错误

先关闭多 GPU，并把相机配置改成 RGB-only。对于 smoke test，先保证视频链路跑通；如果要完整导出语义分割、bbox、depth，再单独排查 Isaac 版本、驱动、Vulkan/CUDA interop 和 Replicator 配置。

### 7.4 只跑 `--without_planning` 后无法渲染完整视频

`--without_planning` 只适合验证场景加载和保存最小轨迹信息。`render.py` 需要规划结果，因此要生成动作视频，应先跑不带 `--without_planning` 的 `demogen.py`。

## 8 小结

这次复现已经打通了 EBench/GenManip 的最小闭环：环境安装、最小任务规划、RGB 渲染和视频导出。后续如果要做正式 benchmark，需要补齐完整 EBench assets、选择 baseline policy，并按官方任务集批量运行评测。
