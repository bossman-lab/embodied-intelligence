# 为了在 Win11 上跑具身智能 demo，我折腾 WSL 2 的完整记录

> 事情要从一个简单的需求说起：我想在手机上发一条消息，T2 就自动跑起具身智能 demo。

## 背景

我有两台主力设备：

| 设备 | 角色 | 系统 |
|:-----|:-----|:----|
| **Linux 服务器** | AI 助手 Hermes 的主场 | Linux |
| **极夜 T2** | 跑 every-embodied 具身智能课程 | **Windows 11** |
| | AMD HX370 / 96GB / Radeon 890M | |

我的 AI 助手 Hermes 日常在 Linux 服务器上运行，通过 Telegram 和我沟通。我让它做事很方便——发条消息就行。

但问题是：**T2 上跑着具身智能课程代码（MuJoCo、Genesis 仿真、LM Studio 本地推理），每次我想跑个 demo，Hermes 都得手动 SSH 连过去执行**：

```
我在 Telegram：@Hermes 跑个 cartpole demo
  → Hermes SSH 连 T2 → 执行命令 → 返回结果
```

麻烦。能不能让 Hermes 直接调度 T2？就像调度 Linux 服务器那样。

## 思路：在 T2 上也装一个 Hermes

Hermes Agent 是我每天都在用的 AI 助手框架。如果在 T2 上也装一个 Hermes，那 T2 就能自动响应命令了。

但 Hermes 需要 **Linux 环境**，而 T2 是 Windows 11。

方案很直接：**WSL 2**。在 Windows 里跑一个 Linux 子系统，里面装 Hermes。

## 第一步：WSL 2 安装 → 开 BIOS 虚拟化

在 PowerShell 里：

```powershell
wsl --install -d Ubuntu-24.04
```

结果报错：

```
请启用虚拟机平台 Windows 功能并确保在 BIOS 中启用了虚拟化。
```

**极夜 T2 的 BIOS 默认把虚拟化了。** 必须进 BIOS 手动开：

开机按 DEL → Advanced → CPU Configuration → **SVM Mode → Enabled** → F10 保存重启

这一步本身没什么。但 **Win11 的设备安全（Device Security）机制从这里开始介入**。

## 第二步：设备安全 —— 内存完整性（Memory Integrity）

在 Windows 11 上，当你启用虚拟化（Hyper-V / WSL 2），系统会触发 **内核隔离（Core Isolation）** 的相关安全策略。

具体来说，设备安全中的 **内存完整性（Memory Integrity）** 是一项基于 **虚拟化安全（Virtualization-Based Security, VBS）** 的功能。它会在 Hyper-V 之上再建立一个安全内核，对所有内核态代码进行签名校验。

```
┌──────────────────────────────────────────────┐
│            Windows 11                         │
│                                                │
│   ┌──────────┐    ┌──────────────────────┐    │
│   │ LM Studio │    │  WSL 2 (Ubuntu)      │    │
│   │ 推理服务  │    │  ┌────────────────┐  │    │
│   │ glm-4.7   │    │  │ Hermes Agent   │  │    │
│   │ ~24 tok/s │    │  │ Python 运行时   │  │    │
│   └──────────┘    │  └────────────────┘  │    │
│        │          └──────────┬───────────┘    │
│        │                     │                │
│        ▼                     ▼                │
│   ┌──────────────────────────────────────┐    │
│   │   Hyper-V / 虚拟化层                 │    │
│   │   （为 WSL 2 提供隔离）              │    │
│   └──────────────┬───────────────────────┘    │
│                  │                            │
│   ┌──────────────▼───────────────────────┐    │
│   │   内存完整性 / VBS（虚拟化安全）      │    │
│   │   对所有内核态代码进行签名校验        │    │
│   │   每次内存访问经 Hypervisor 验证      │    │
│   └──────────────────────────────────────┘    │
│                  │                            │
│                  ▼                            │
│           物理硬件 (CPU/内存)                  │
└──────────────────────────────────────────────┘
```

这个功能默认是**关闭**的，但当你启用 WSL 2（Hyper-V）后，有些系统会提示你开启内存完整性以"增强安全性"。

关键在于：**这个功能一旦开启，对内存密集型工作负载（尤其是 LLM 推理）是致命打击。**

## 第三步：配置与重启 —— 性能到谷底

如果你跟我一样：
1. 为了 WSL 2 去 BIOS 开了虚拟化（SVM Mode）
2. 系统提示你配置设备安全 → 跟着开了内存完整性
3. 重启完发现 LM Studio 炸了

**重启前后对比：**

| 指标 | 重启前（正常） | 重启后（内存完整性开启） |
|:-----|:-------------:|:---------------------:|
| LM Studio 推理速度 | **~24 tok/s** | **~3-5 tok/s** |
| CPU 占用 | 30-40% | 70-80% |
| 内存延迟 | 正常 | 显著增加 |
| MuJoCo 仿真 FPS | 60+ | 30-40 |
| 系统响应 | 流畅 | 感觉卡顿 |

**为什么？**

因为 **VBS + 内存完整性** 给每次内存访问加了一层 Hypervisor 验证。对于 LLM 推理这种 **频繁读写大块连续内存** 的工作负载，这层验证的开销被无限放大。

模型权重加载到内存后，推理过程中 CPU/GPU 需要不停地读取这些权重。VBS 保证安全内核代码不被篡改的方式是：**所有内存访问都要过 Hypervisor 的验证层**。

本来直接读写内存 → 24 tok/s。加了验证层 → 每个内存操作变慢 → 3-5 tok/s。

**这不是 WSL 的资源竞争问题，而是 Windows 安全机制本身对内存带宽型负载的降维打击。**

## 第四步：尝试关闭

既然找到了问题，那就关掉它：

Windows 安全中心 → 设备安全 → 内核隔离详细信息 → **内存完整性 → 关闭**

重启......**性能回来了**。24 tok/s。

但设备安全那里始终有个黄色警告：

```
你的设备存在安全风险。
内存完整性已关闭。你的设备可能易受攻击。
```

## 第五步：两难与最终决定

现在面临一个选择：

**方案 A：留 WSL 2 + 关闭内存完整性**
- WSL 里的 Hermes 能跑 ✅
- LM Studio 恢复正常 24 tok/s ✅
- 系统安全提示永远挂在那里 ⚠️
- 核心矛盾：WSL 2 依赖虚拟化层，而虚拟化层又绑定了内存完整性

**方案 B：放弃 WSL 2，找原生方案**
- 没有 WSL → 没有虚拟化层 → 内存完整性需求消失 ✅
- LM Studio 稳定 ✅
- 但 Hermes 需要 Linux，装不了 ❌

我选了方案 B，但绕了一下——**不装 Hermes，用原生 Windows 工具替代**。

T2 上本来就在跑 **OpenClaw Gateway**（一个 Telegram Bot 网关，原生 Windows 支持）。它不需要 WSL，不需要 Linux：

```json
{
  "telegram_bot_token": "...",
  "port": 18789,
  "commands": {
    "run_demo": "python D:/eembodied/examples/01_hello_every_embodied_mujoco.py --headless"
  }
}
```

Telegram bot T2-Bot 连上，直接在 T2 上响应命令。

最终架构：

```
         Telegram
           |
     ┌─────┴──────┐
     |            |
  Hermes       T2-Bot
(Linux 服务器)  (OpenClaw/T2 原生 Windows)
     |            |
     |      ┌─────┴────────┐
     |      | 极夜 T2      |
     |      | ├ MuJoCo     |
     |      | ├ Genesis    |
     |      | ├ LM Studio  |  ← 稳定 24 tok/s
     |      | └ OpenClaw   |
     |      |              |
     └──────► SSH (备用)   |
            └──────────────┘
```

## WSL 的局限与 Windows 的落后 —— 实话实说

折腾完这一圈，有些话不吐不快。

### WSL 2 的定位出了偏差

WSL 2 刚出的时候，微软说它是"面向开发者的 Windows 最佳功能"。但用了一年多下来，我觉得它的定位很尴尬：

**WSL 2 适合跑纯 Linux 命令行工具（grep、awk、git、ssh），不适合跑真正的 Linux 工作负载（容器、GPU 计算、AI 推理）。**

为什么？

- **它不是真正的集成**。文件系统性能在 `/mnt/` 下打三折，网络要折腾桥接，GPU 只支持 NVIDIA。
- **它带来了安全冲突**。为了跑一个 Linux 子系统，你要牵动整个 Windows 的虚拟化安全体系。一个开发者工具，却要你动 BIOS、调安全策略、承担全系统的性能代价——这合理吗？
- **它对 AI/ML 开发者不友好**。2024-2026 年，AI 开发已经是主流。WSL 2 在 AMD GPU 支持上完全缺席，Intel GPU 支持也是半残。NVIDIA 用户在 WSL 里能跑 CUDA，AMD 用户？请你自己想办法。
- **它的内存管理是黑箱**。Vmmem 进程在任务管理器里是一个黑洞，你不知道内存是怎么分配的，也没法精细控制。

### Windows 在 AI 时代的落后是结构性的

这件事让我看清了一个更大的问题：**Windows 在 AI 基础设施上已经严重落后了。**

Linux 生态处理 AI/ML 工作负载的方式是：
1. 装 NVIDIA 驱动 → `nvidia-smi` → 装 CUDA → 装 PyTorch → 跑起来
2. 全过程没有"设备安全"、"内核隔离"、"虚拟化安全"的干扰
3. Docker 原生支持 GPU 穿透

Windows 生态是：
1. 装 NVIDIA 驱动（如果用的是 AMD GPU，对不起）
2. 决定用 WSL 还是原生还是 Docker Desktop（哪个都有坑）
3. 如果走 WSL，需要开虚拟化 → 触发 Hyper-V → 触发内存完整性
4. 性能降级 → 关安全功能 → 系统弹警告
5. 告诉自己"就这样吧"

**问题不在技术细节，在微软的产品策略。**

微软这几年在 AI 上喊得很大声（Copilot、Azure AI），但 Windows 作为 AI 开发者平台的体验几乎没有进步。2026 年了，一个开发者想在 Windows 上跑 LLM 推理 + 仿真，需要：

- 进 BIOS 开虚拟化
- 配置内存完整性
- 关掉安全功能恢复性能
- 容忍系统弹安全警告
- 用第三方工具（OpenClaw）做自动化

这些坑本不该由开发者来踩。

### WSL 的未来方向？

WSL 如果要真正成为 AI 开发者的选择，我认为需要：

1. **解耦虚拟化和安全**。WSL 不需要强制启用 VBS/内存完整性。
2. **原生 GPU 支持脱离 CUDA 绑定**。AMD 和 Intel 用户在 WSL 里也应该有平等的 GPU 加速能力。
3. **精细的资源控制**。给用户一个面板，直接设置 WSL 的 CPU/内存上限，实时可见，而不是靠 `.wslconfig` 黑魔法。
4. **网络模型可选**。NAT 模式下就做好端口转发的自动化，不要每次重启 IP 都变。

但说实话，经过这次折腾，我对 WSL 的信心已经消耗完了。它给我的感觉是：**微软自己做了一个好东西，却被 Windows 自身的安全体系架空了。**

## 最终总结

```
需求：手机遥控 T2 跑具身智能 demo
  ↓
方案：在 T2 上装 Hermes Agent（可自动响应命令）
  ↓
阻碍：Hermes 需要 Linux，T2 是 Windows 11
  ↓
尝试：WSL 2
  ↓
遇阻①：BIOS 默认关闭虚拟化 → 进 BIOS 开 SVM Mode
  ↓
遇阻②：Win11 设备安全 → 内存完整性 → VBS
        重启后 LM Studio 从 24 tok/s → 3-5 tok/s
  ↓
尝试关闭内存完整性 → 恢复正常
  ↓
纠结：开着 WSL 就开着虚拟化层
       关着 WSL → 装不了 Hermes
  ↓
决策：放弃 WSL + Hermes
       用 OpenClaw Gateway（原生 Windows）
       配合 Hermes 做上层调度
  ↓
现状：手机一条消息 → T2 自动跑 demo → LM Studio 稳定 24 tok/s
```

**几点实在的教训：**

1. **Win11 的内存完整性 / VBS 对 LLM 推理是性能杀手**。不是资源不够，是 Hypervisor 验证层给每次内存操作加了巨大开销。
2. **WSL 2 不适合跑需要 GPU + 高内存带宽的工作负载**。它的定位就是命令行工具，不是 AI 计算平台。
3. **Windows AI 生态还没准备好**。2026 年了，跑个具身智能 demo 要过五关斩六将——这不该是常态。
4. **原生方案 > 嵌套方案**。OpenClaw 原生 Windows，没有中间层，没有性能损耗，一直都能用——只是我一开始没往这个方向想。

---

**仓库：[bossman-lab/embodied-intelligence](https://github.com/bossman-lab/embodied-intelligence)**

姊妹篇：[极夜T2 跑通 Every-Embodied 课程全记录](./t2-embodied-journey.md)

> 最后说一句：这篇文章不是黑 Windows。我每天都用 Windows，极夜 T2 作为一台迷你主机，硬件体验很好。但微软在 AI 开发者体验上的投入，和这个时代的需求之间，有一个巨大的鸿沟。希望 Windows 12 能填上。
