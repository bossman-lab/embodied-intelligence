# RDK X5 Magicbox 教程工程（从 0 到 Demo）

本目录是一套面向 `RDK X5 Magicbox` 的中文实践教程，目标是让读者从开箱、刷机、联网开始，逐步跑通基础外设、视觉 Demo、语音与 LLM 链路，并进一步理解如何把 `OpenClaw` 接入到板端能力中。

1. 开箱与系统准备
2. 快速入门与基础外设
3. 视觉 Demo（双目深度、手势）
4. 本机语音 + LLM 原生链路
5. OpenClaw 在 Magicbox 上的部署与接入
6. FAQ/已知问题/排障

## 1. 教程总大纲

- [README_01_环境准备与刷机.md](./README_01_环境准备与刷机.md)
- [README_02_有线网口连接与登录.md](./README_02_有线网口连接与登录.md)
- [README_03_快速入门与基础外设.md](./README_03_快速入门与基础外设.md)
- [README_03_快速入门与基础外设补充材料.md](./README_03_快速入门与基础外设补充材料.md)
- [README_04_算法Demo_双目与手势.md](./README_04_算法Demo_双目与手势.md)
- [README_05_算法Demo_语音与LLM.md](./README_05_算法Demo_语音与LLM.md)
- [README_06_OpenClaw部署与接入.md](./README_06_OpenClaw部署与接入.md)
- [README_07_排障与发布建议.md](./README_07_排障与发布建议.md)
- [README_08_SSH命令执行与整段粘贴说明.md](./README_08_SSH命令执行与整段粘贴说明.md)
- [README_09_飞书控制入口.md](./README_09_飞书控制入口.md)
- [README_10_Windows主机OpenClaw语音桥接与家庭物资助手.md](./README_10_Windows主机OpenClaw语音桥接与家庭物资助手.md)

## 2. 需要了解的参考实现

本教程会多次引用下列官方或开源实现的能力边界。公开目录中不会放入完整依赖仓库，读者需要按章节说明自行获取或安装对应组件。

- `hobot_stereonet`
- `magicbox_gesture_interaction`
- `magicbox_audio_io`
- `magicbox_qwen_llm`
- `openclaw`
- `sherpa-onnx`

语音链路涉及的 ASR 模型可能需要单独准备，不能简单假设克隆仓库后所有大文件都已经就绪。OpenClaw 的 Linux 安装主线是先安装 `openclaw@latest`，再执行 `openclaw onboard --install-daemon`。

## 3. 官方资料入口（已核对）

- 在线文档首页：https://d-robotics.github.io/magicbox_doc/magicbox
- 章节：
  - 产品概述：https://d-robotics.github.io/magicbox_doc/magicbox
  - 快速入门：https://d-robotics.github.io/magicbox_doc/quickstart
  - 基础外设：https://d-robotics.github.io/magicbox_doc/basic-peripherals
  - 资源下载：https://d-robotics.github.io/magicbox_doc/resource-download
  - 算法开发：https://d-robotics.github.io/magicbox_doc/algorithm-development
  - FAQ：https://d-robotics.github.io/magicbox_doc/faq
  - 已知问题：https://d-robotics.github.io/magicbox_doc/known_issues
  - 更新日志：https://d-robotics.github.io/magicbox_doc/changelog
  - 技术支持：https://d-robotics.github.io/magicbox_doc/technical-support

## 4. 重构后的主线

为了把 `OpenClaw` 合理融入教程，当前文档按两条能力线拆开：

1. `Magicbox 原生能力线`
   - 刷机、联网、基础外设、双目、手势、语音、LLM
2. `平台扩展能力线`
   - 在 Magicbox 上部署 `OpenClaw Gateway`
   - 接入 WebChat / Telegram / Feishu 等远程入口
   - 预留和本地 ROS 动作、灯光、语音链路的桥接点

这样可以避免把 `OpenClaw` 和板端原生 ROS demo 混写，读者也能更清楚地区分“原厂能力验证”和“平台扩展接入”。

## 5. 学完后应能完成什么

读完并完成本专题后，读者应当能够：

- 完成 Magicbox 的刷机、联网和 SSH 登录；
- 跑通按钮、灯光、舵机、双目、手势、语音和 LLM 的基础验证；
- 识别每个 Demo 的预期现象、常见失败现象和基本回滚方式；
- 理解 OpenClaw Gateway 与本地 ROS、脚本动作之间的桥接位置；
- 判断哪些文件可以公开提交，哪些模型、缓存、日志和临时产物不应进入仓库。

## 6. 本地资料

- 本地 PDF：`d_robotics_rdk_x5_magicbox_zh_v1.0.pdf`
- 官方页面归档：`assets/official_pages/`
- 官方图片归档：`assets/official_images/`
- 实拍截图：`assets/image-*.png`
