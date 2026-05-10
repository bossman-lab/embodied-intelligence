# NVIDIA Isaac Sim 配置指南

NVIDIA Isaac Sim 是基于 NVIDIA Omniverse 的高保真机器人仿真平台，适合用于传感器仿真、ROS/ROS2 集成、合成数据生成、复杂机器人系统验证和 Sim2Real 相关实验。

本教程介绍 Isaac Sim 的基础安装方式、Python 环境配置、ROS/ROS2 集成、快速入门和常见问题。本文档此前存在整段内容重复，网页端目录会出现重复标题；本版已清理为单份内容。

## 系统要求

### 硬件要求

- CPU：Intel Core i7/i9 或 AMD Ryzen 7/9，建议 8 核或更高。
- GPU：最低建议 NVIDIA GeForce RTX 2070，推荐 RTX 3080/3090 或 RTX A4000/A5000/A6000。
- 内存：建议 32GB RAM，最低 16GB。
- 存储：至少 50GB 可用空间，推荐 SSD。

### 软件要求

- 操作系统：Windows 10/11 64 位，或 Ubuntu 20.04/22.04 LTS。
- 显卡驱动：建议使用 NVIDIA 官方推荐驱动版本。
- CUDA Toolkit：根据 Isaac Sim 版本和显卡驱动要求选择匹配版本。

## 安装方式

Isaac Sim 常见安装方式包括本地工作站安装、容器安装和云端部署。不同版本的入口可能会随 NVIDIA 官方发布方式变化，实际安装时建议以官方文档为准。

### 工作站安装

1. 访问 NVIDIA Isaac Sim 官方文档或 Omniverse 下载页面。
2. 根据当前官方推荐方式下载 Isaac Sim。
3. 登录 NVIDIA 账户并完成安装。
4. 启动 Isaac Sim，等待首次缓存和扩展初始化完成。

参考入口：

- [NVIDIA Isaac Sim 官方文档](https://docs.isaacsim.omniverse.nvidia.com/)
- [NVIDIA Omniverse 官方文档](https://docs.omniverse.nvidia.com/)

### 容器安装

适合希望在 Linux 服务器或可复现环境中运行 Isaac Sim 的用户。

```bash
# 安装 Docker 后，继续安装 NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 拉取 Isaac Sim 容器镜像，具体 tag 以官方文档为准
docker pull nvcr.io/nvidia/isaac-sim:latest
```

运行示例：

```bash
docker run --gpus all -e "ACCEPT_EULA=Y" --rm -it \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=$DISPLAY \
  nvcr.io/nvidia/isaac-sim:latest
```

如果在远程服务器上使用，通常还需要配置 X11、VNC、NICE DCV 或 WebRTC 远程访问。

### 云部署

Isaac Sim 可以部署在支持 NVIDIA GPU 的云主机上。建议选择具备 NVIDIA GPU、足够显存和稳定远程桌面能力的实例。

基本流程：

1. 创建支持 NVIDIA GPU 的云实例。
2. 安装或确认 NVIDIA 驱动。
3. 配置远程桌面、VNC、NICE DCV 或 WebRTC。
4. 按工作站或容器方式安装 Isaac Sim。

本仓库中也提供了更完整的云端部署示例：

- [阿里云部署 Isaac Lab + GR00T 完整教程](阿里云部署%20Isaac%20Lab%20%2B%20GR00T%20完整教程.md)

## Python 环境配置

Isaac Sim 通常自带 Python 环境。简单脚本可以直接使用 Isaac Sim 附带的 Python；如果要与外部训练代码联动，可以创建独立虚拟环境，并显式配置 Isaac Sim 的 Python 路径。

示例：

```bash
conda create -n isaac-sim python=3.9
conda activate isaac-sim
pip install torch torchvision numpy matplotlib
```

在脚本中临时加入 Isaac Sim Python 路径：

```python
import sys
sys.path.append("/path/to/isaac-sim/python")
```

实际路径应替换为本机 Isaac Sim 安装目录。

## ROS/ROS2 集成

Isaac Sim 支持 ROS 和 ROS2 集成，适合在仿真环境中测试机器人系统节点、传感器消息和控制链路。

### ROS2 集成

1. 安装 ROS2。
2. 在 Isaac Sim 中打开扩展管理器。
3. 搜索并启用 Omniverse Isaac ROS2 Bridge。
4. 运行 Isaac Examples 中的 ROS2 示例，验证消息发布和订阅是否正常。

### ROS 集成

ROS 集成主要面向 Linux 环境。

1. 安装 ROS。
2. 在 Isaac Sim 中启用 Omniverse Isaac ROS Bridge。
3. 运行 ROS 示例并检查话题输出。

## 快速入门

### 启动 Isaac Sim

1. 通过本地安装入口或容器启动 Isaac Sim。
2. 等待扩展加载完成。
3. 打开示例场景或新建空场景。

### 探索基本功能

1. 查看 Stage Tree、Viewport、Property Panel 和时间轴。
2. 添加基础几何体，例如 Cube。
3. 添加机器人模型，例如 UR10 或 Franka。
4. 点击 Play 运行仿真。
5. 尝试添加相机、深度传感器或 ROS2 Bridge。

### 推荐学习顺序

1. 完成 Isaac Sim 官方 Quickstart。
2. 运行一个机器人示例。
3. 学习机器人导入、关节控制和传感器配置。
4. 学习 Python API 和 OmniGraph。
5. 再进入 Isaac Lab、GR00T 或合成数据生成流程。

## 常见问题

### Isaac Sim 无法启动或崩溃

- 检查 GPU 是否满足要求。
- 检查 NVIDIA 驱动是否与 Isaac Sim 版本匹配。
- 降低渲染质量或关闭不必要扩展。
- 使用 debug 日志定位扩展加载问题。

### 渲染性能较差

- 降低场景复杂度。
- 降低渲染质量设置。
- 关闭不必要的传感器。
- 不需要真实感渲染时关闭实时光线追踪。

### 机器人导入失败

- 检查 URDF/USD 文件格式。
- 检查 mesh 路径是否正确。
- 使用 Import Wizard 查看错误日志。
- 注意关节轴、惯量、碰撞体和尺度单位。

### Python 脚本无法运行

- 确认 Python 版本与 Isaac Sim 版本兼容。
- 使用 Isaac Sim 自带 Python 先验证最小示例。
- 检查 `PYTHONPATH` 和 Isaac Sim 安装路径。

## 参考资源

- [NVIDIA Isaac Sim 官方文档](https://docs.isaacsim.omniverse.nvidia.com/)
- [NVIDIA Omniverse 官方文档](https://docs.omniverse.nvidia.com/)
- [Isaac Sim 教程视频集](https://www.youtube.com/playlist?list=PL3jK4xNnlCVfYZlv1B-eCcz1zY5WJqWTH)
- [NVIDIA 开发者论坛 Isaac Sim 板块](https://forums.developer.nvidia.com/c/omniverse/isaac-sim/69)
