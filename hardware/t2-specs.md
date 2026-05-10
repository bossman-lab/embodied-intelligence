# 极夜 T2 (DeskOne T2) 硬件规格

## 核心配置

| 组件 | 规格 |
|:-----|:-----|
| **CPU** | AMD Ryzen AI 9 HX370 (12C/24T, 5.1GHz boost) |
| **GPU** | AMD Radeon 890M iGPU (RDNA 3.5, 16CU) |
| **RAM** | 96GB DDR5 (双通道) |
| **存储** | 1TB+ NVMe SSD |
| **网络** | 千兆以太网 (192.168.3.x) |
| **扩展** | OCuLink 端口 (支持外接 NVIDIA eGPU) |
| **系统** | Windows 11 Pro |
| **尺寸** | 迷你主机 (手掌大小) |

## 网络信息

- **IP**: `192.168.3.175` (DHCP，可能变动)
- **MAC**: `00:1f:05:78:a5:a6` (WOL 唤醒用)
- **SSH**: 端口 22，用户 `qlp`，密码认证已启用
- **局域网**: 与 Hermes 服务器同一 192.168.3.x 网段

## 软件环境

| 组件 | 版本/路径 |
|:-----|:----------|
| **OS** | Windows 11 Pro |
| **Python** | Miniconda at `C:\Users\qlp\miniconda3` |
| **Conda Env** | `embodied` (Python 3.10) |
| **GitHub Push** | 通过 API (无 git-remote-https) |
| **代理** | `http://127.0.0.1:7890` (clash，国内环境) |

## 安装的 ML 框架 (embodied env)

| 框架 | 版本 | 状态 |
|:-----|:----:|:----:|
| PyTorch | 2.11.0 (CPU) | ✅ |
| MuJoCo | 3.8.0 | ✅ |
| Genesis | 0.4.6 | ✅ |
| Gymnasium | 1.1.1 | ✅ |
| Stable-Baselines3 | — | ✅ |
| FastAPI | 0.136.1 | ✅ |
| Uvicorn | 0.46.0 | ✅ |
| Viser | 1.0.27 | ✅ |
| Trimesh | — | ✅ |
| Open3D | — | ✅ |
| Manifold3D | — | ✅ |
| YourDFPY | — | ✅ |

## 已知问题

1. **休眠**：T2 进入休眠后所有 SSH 连接和后台进程中断，需通过 WOL 唤醒
2. **GPU 加速**：Radeon 890M iGPU 对 PyTorch CUDA 不可用（仅支持 ROCm），ML 训练依赖 CPU
3. **金山毒霸**：误报 Miniconda 的 python.exe 为木马，需添加白名单
4. **GitHub 访问**：国内直连不稳定，建议代理或 tarball 方案
5. **OCuLink 待用**：OCuLink 端口可用但未连接 eGPU，后续可扩展 NVIDIA 显卡

## WOL 唤醒命令

```bash
# Linux (etherwake)
sudo etherwake -i eth0 00:1f:05:78:a5:a6

# Linux (wakeonlan)
wakeonlan 00:1f:05:78:a5:a6
```

唤醒后等待约 10 秒即可 SSH 连接。
