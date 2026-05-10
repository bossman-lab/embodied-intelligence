# 机器人仿真教程

本目录包含机器人仿真平台的选型说明、环境配置教程、平台实践文档和挑战赛资料。

## 入口文档

- [仿真平台选型与目录导览](01仿真配置文档.md) - 对比 MuJoCo、Isaac Sim、ManiSkill、Habitat、GenieSim、Genesis、AirSim 等平台的定位和适用任务。
- [ManiSkill 环境仿真配置](02Maniskill环境仿真配置.md) - ManiSkill 仿真环境搭建教程。
- [Isaac Sim 配置](03issac-sim配置.md) - NVIDIA Isaac Sim 配置说明。
- [家务机器人环境配置](04家务机器人环境配置.md) - 家务机器人仿真环境配置。
- [SIM1 柔体仿真与数据生成](09SIM1柔体仿真与数据生成/01SIM1环境配置与运行.md) - 双臂布料操作的遥操作、replay、扩散轨迹生成与过滤流程。

## 平台专题

- [ManiSkill 详细文档](Maniskill详细文档/) - ManiSkill 仿真平台的详细使用文档。
- [Isaac Sim 5.0 安装](01Isaac-sim5.0安装/isaac-sim安装.md) - Isaac Sim 5.0 安装记录。
- [Isaac Lab + GR00T 云部署教程](阿里云部署%20Isaac%20Lab%20%2B%20GR00T%20完整教程.md) - 阿里云环境下的 Isaac Lab 和 GR00T 部署流程。
- [Genesis 环境配置](Genesis仿真环境配置/01环境配置和测试.md) - Genesis 仿真平台环境配置。
- [Genesis 可视化和渲染](Genesis仿真环境配置/02可视化和渲染.md) - Genesis 可视化和渲染实践。
- [GenieSim 配置](07GenieSim配置.md) - GenieSim 环境配置。
- [GenieSim3 配置](08GenieSim3配置.md) - GenieSim3 环境配置。

## 仿真资源

- [资源文件](assets/) - 仿真相关图片和资源文件。
- [仿真挑战赛](challenge竞赛/) - 机器人仿真相关竞赛资料。

## 推荐学习路径

1. 先阅读 [仿真平台选型与目录导览](01仿真配置文档.md)，确定自己的任务属于操作、导航、系统部署还是前沿平台调研。
2. 操作与强化学习方向：学习 [ManiSkill 环境仿真配置](02Maniskill环境仿真配置.md)，再进入 [ManiSkill 详细文档](Maniskill详细文档/)。
3. 高保真渲染与系统集成方向：学习 [Isaac Sim 配置](03issac-sim配置.md)，再进入 [Isaac Sim 5.0 安装](01Isaac-sim5.0安装/isaac-sim安装.md) 或 [Isaac Lab + GR00T 云部署教程](阿里云部署%20Isaac%20Lab%20%2B%20GR00T%20完整教程.md)。
4. 家务任务与复杂交互方向：学习 [家务机器人环境配置](04家务机器人环境配置.md)。
5. 柔体操作方向：学习 [SIM1 柔体仿真与数据生成](09SIM1柔体仿真与数据生成/01SIM1环境配置与运行.md)。

## 环境要求

不同平台的要求差异很大，建议以各配置文档为准。一般需要：

- Python 3.8+ 或平台指定版本。
- CUDA 和 NVIDIA 驱动，用于 GPU 仿真或高质量渲染。
- MuJoCo、Isaac Sim、ManiSkill、Habitat 等平台对应依赖。
- NVIDIA GPU，复杂渲染和大规模并行仿真建议使用更高显存配置。
