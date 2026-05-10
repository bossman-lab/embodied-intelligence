# 极夜T2 折腾 WSL 2 血泪史：为什么我最后投奔了原生 Windows

> 一台 Windows 迷你主机 + 具身智能课程，WSL 2 到底行不行？我的答案是：**理论上很美，实际上很痛。**

## 起点

我有一台 **极夜T2 (DeskOne T2)** 迷你主机：
- AMD Ryzen AI 9 HX370 (12C/24T)
- 96GB DDR5 内存
- Radeon 890M iGPU（≈GTX 1650 水平）
- Windows 11 家庭中文版

我想跑 [every-embodied](https://github.com/datawhalechina/every-embodied) 课程 —— 20 章、1300+ 文件的具身智能全栈教程。

一开始，我的直觉是：**这玩意儿是给 Linux 写的吧？装 WSL 2。**

然后开始了整整两天的 "WSL 折腾"。

---

## 第一章：WSL 2 安装 —— 第一个坑

### 看似简单

```powershell
wsl --install -d Ubuntu-24.04
```

一切顺利。WSL 2 启动，Ubuntu 终端跳出来了。

### 隐藏的坑

Windows 11 **家庭中文版**默认没有开启"虚拟机平台"。虽然 `wsl --install` 会自动启用，但重启后：

```
请启用虚拟机平台 Windows 功能并确保在 BIOS 中启用了虚拟化。
```

在 BIOS 里找了一圈，才发现 极夜T2 的 BIOS 默认 VT（虚拟化技术）是**关闭**的。

**解决**：进 BIOS → Advanced → CPU Configuration → SVM Mode → Enabled → F10 保存重启。

耗时：30 分钟。踩坑 1。

---

## 第二章：网络黑洞 —— WSL 2 的 NAT 噩梦

WSL 2 默认使用 **NAT 网络**（Hyper-V 虚拟交换机）。这意味着：

1. WSL 的 IP 和宿主机不在同一网段
2. 从局域网其他机器（比如我的 Hermes 服务器）**不能直接 SSH 进 WSL**
3. `localhost` 映射只能从宿主机访问，局域网不可达

### 尝试 1：端口转发

```powershell
netsh interface portproxy add v4tov4 listenport=2222 connectaddress=127.0.0.1 connectport=22
```

能工作，但每次 WSL 重启 IP 会变，portproxy 也得重配。烦。

### 尝试 2：WSL 桥接网络

WSL 2 原生不支持桥接模式。社区方案是：

```powershell
# 创建外部虚拟交换机
New-VMSwitch -Name "WSL-Bridge" -NetAdapterName "Wi-Fi" -AllowManagementOS $true
```

然后在 `%USERPROFILE%\\.wslconfig` 里指定交换机：

```ini
[wsl2]
networkingMode=bridged
vmSwitch=WSL-Bridge
```

**结果**：配置后 WSL 获取了和宿主机同网段的 IP（192.168.3.x），SSH 可达了。

但代价是：每次切换 WiFi 网络（带到公司/咖啡厅）都要重配虚拟交换机。

踩坑 2。耗时：1 小时。

---

## 第三章：内存幽灵 —— WSL 的默认内存限制

WSL 2 默认最多使用宿主机 **50% 的内存**，在 96GB 的机器上就是 48GB —— 看起来很多，但：

- Genesis + MuJoCo 同时运行 + 加载模型权重 ≈ 8-16GB
- 再加 VLA 模型推理（比如 OpenVLA 量化版 ≈ 4-8GB）
- 再加系统缓存...

实际上并不紧张，但真正让我不爽的是：**WSL 的 Vmmem 进程在宿主机任务管理器里是一个黑洞** —— 你不知道它怎么分配的内存，也不知道谁会先 OOM。

**解决**：在 `.wslconfig` 里手动限制：

```ini
[wsl2]
memory=64GB
processors=12
swap=8GB
```

踩坑 3。这个不算致命，但膈应。

---

## 第四章：GPU 之殇 —— AMD iGPU 在 WSL 2 里的处境

这是**最致命的坑**。

### WSL 2 的 GPU 支持现状

| GPU 类型 | WSL 2 支持 | 说明 |
|:---------|:----------:|:-----|
| NVIDIA CUDA | ✅ 官方支持 | 通过 CUDA on WSL 驱动 |
| Intel GPU | ⚠️ 有限支持 | Intel GPU compute runtime |
| **AMD GPU** | **❌ 不支持** | **没有官方驱动支持 iGPU 计算** |

极夜 T2 的 Radeon 890M 在 WSL 2 里：
- `nvidia-smi` → 查不到（不是 NVIDIA）
- `rocm-smi` → 不支持（AMD ROCm 不支持 WSL）
- `OpenCL` → 不可用（AMD OpenCL 只对宿主机生效）
- `Vulkan` → 能用一点点（但 Genesis/MuJoCo 不依赖这个）

这意味着在 WSL 里：
- MuJoCo CPU 仿真 ✅ 可以跑
- Genesis CPU 模式 ✅ 可以跑
- **Genesis GPU 模式 ❌ 跑不了**（需要 CUDA 或 Vulkan compute）
- **任何 VLA 模型推理 ❌ 慢到无法接受**
- **Matplotlib 显示 ❌**（WSL 本身的 GUI 问题）

### 开源项目直接抛弃你

`genesis-world` 在 WSL 里安装后，运行 GPU 加速时报错：

```
RuntimeError: Genesis GPU mode requires CUDA or Vulkan compute support.
```

看官方文档：Genesis 0.4.6 的 Windows 支持是**原生 Windows**，不是 WSL。

踩坑 4。耗时：2 小时尝试各种 workaround，全部失败。

---

## 第五章：GUI 的噩梦 —— WSLg 是好东西，但不是你的

WSL 2 在 Windows 11 上带有 WSLg（Windows Subsystem for Linux GUI），理论上可以跑 GUI 应用。

现实中：

### MuJoCo 可视化窗口

```bash
python 01_hello_every_embodied_mujoco.py
```

WSLg 确实弹出了窗口...... **在本机显示器上**。

但我是**通过 SSH 远程控制 T2 的**，WSLg 的窗口弹在 T2 的桌面上，我看不到，X11 forwarding 也接不住。

### 尝试各种转发

1. **X11 forwarding**：`export DISPLAY=:0` → 不行，WSLg 不走普通 X11
2. **VNC**：在 WSL 里跑 VNC server → 慢，卡顿
3. **RDP 到 T2 桌面**：能用但体验极差，每次都得远程桌面进去看窗口

### 最终方案

凡是需要显示的东西，要么加 `--headless` 参数，要么干脆不在 WSL 里跑。

但课程脚本默认没有 `--headless`，而且国产课程脚本里一堆 `matplotlib` 中文绘图......改了 WSL 的字体又有一堆编码问题。

踩坑 5。耗时：3 小时。

---

## 第六章：文件系统 —— ext4 很快，但你不一定在用

WSL 2 有两种文件系统体验：
- **`/home/` 等 ext4 分区**：飞快
- **`/mnt/c/` 等 Windows 挂载**：**慢 10 倍**

课程代码在 `D:\eembodied\` 上（Windows 的 D 盘），在 WSL 里通过 `/mnt/d/eembodied/` 访问。

```
/mnt/d/eembodied/ 下
git status 耗时：45 秒
find . -name "*.py" 耗时：12 秒
```

同样的操作在 ext4 分区里 1 秒完成。

把代码复制到 WSL 的 ext4 里 → 占双倍空间，而且和 Windows 版本不同步，改了一处另一处忘了。

踩坑 6。虽然没有"解决方案"，但这个割裂感让人很不舒服。

---

## 终章：放弃 WSL，回归原生 Windows

### 最后一根稻草

当我发现 every-embodied 课程的 Ch06（VLA）和 Ch07（video2robot）的依赖在 WSL 里装好了也跑不动——因为 GPU 算力和 GUI 的双重限制——我就知道 WSL 在这里是死胡同。

### 决策

**WSL 2 不适合这个场景**，原因总结：

| 需求 | WSL 2 | 原生 Windows |
|:-----|:-----:|:------------:|
| Genesis/MuJoCo 仿真 | ✅ CPU only | ✅ 完美运行 |
| GPU 加速仿真 | ❌ AMD iGPU 不支持 | ❌ 同样不支持 |
| VLA 模型训练 | ❌ 无 CUDA | ❌ 无 CUDA |
| SSH 远程控制 | ⚠️ 需要桥接/端口转发 | ✅ OpenSSH Server 原生支持 |
| GUI 可视化窗口 | ⚠️ 远程不可见 | ✅ 本地桌面可见 |
| 文件操作效率 | ⚠️ /mnt/ 慢 | ✅ 原生 NTFS |
| conda 工具链 | ✅ 能用 | ✅ 完美运行 |
| 中文编码/字体 | ⚠️ 到处是坑 | ⚠️ 也有坑但好处理 |

### 迁移回原生

```powershell
# 1. 在 Windows 上装 Miniconda
# 2. 创建 embodied 环境
conda create -n embodied python=3.10 pip -y

# 3. 装 PyTorch、Genesis、MuJoCo
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install genesis-world

# 4. 远程管理？Windows OpenSSH Server 直接连
```

全部在 30 分钟内搞定。之前的 WSL 折腾了两天。

---

## 最后说几句

**WSL 2 本身是个好产品**。它适合：

- 在 Windows 上跑 Linux 命令行工具
- 跑 Docker 容器（WSL 2 backend 比 Hyper-V 快）
- 做 Web 开发、后端开发
- 需要 Linux-only 工具链的场景

但 **如果你的工作负载涉及 GPU 计算（尤其是非 NVIDIA）、图形界面远程访问、或者大量跨文件系统操作**——WSL 2 会让你怀疑人生。

对于极夜 T2 这个硬件组合（AMD iGPU + 96GB RAM + 国产系统），**原生 Windows 环境 + SSH 远程控制** 是目前最稳的路线。

课程代码、模型文件全部放在 **Z 盘（SMB 共享）**，T2 运行从 Z 盘挂载访问，不直接存储——这样以后无论换哪台机器跑，数据都在。

---

我的完整课程仓库：[bossman-lab/embodied-intelligence](https://github.com/bossman-lab/embodied-intelligence)

之前的踩坑总结：[t2-embodied-journey.md](./t2-embodied-journey.md)

---
*极夜 T2 + every-embodied + WSL 2 → 血泪史完整记录。如果你也在 Windows 上折腾具身智能，希望你看到这篇文章时少走弯路。*
