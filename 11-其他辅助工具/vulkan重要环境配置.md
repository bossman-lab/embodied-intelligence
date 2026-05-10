好的，这是提供的 Vulkan 安装指南的中文翻译，已保留原始 Markdown 格式。

---

### Vulkan

### Ubuntu

**在 Ubuntu 上安装 Vulkan:**

**Bash**

```
sudo apt-get install libvulkan1
```

**测试你的 Vulkan 安装:**

**Bash**

```
sudo apt-get install vulkan-tools
vulkaninfo
```

如果 `vulkaninfo` 未能显示关于 Vulkan 的信息，请检查以下文件是否存在：

```
/usr/share/vulkan/icd.d/nvidia_icd.json
/usr/share/glvnd/egl_vendor.d/10_nvidia.json
/etc/vulkan/implicit_layer.d/nvidia_layers.json (可选，但对于某些 GPU 如 A100 是必需的)
```

如果 `/usr/share/vulkan/icd.d/nvidia_icd.json` 不存在，请尝试创建该文件并填入以下内容：

**JSON**

```
{
    "file_format_version" : "1.0.0",
    "ICD": {
        "library_path": "libGLX_nvidia.so.0",
        "api_version" : "1.2.155"
    }
}
```

如果 `/usr/share/glvnd/egl_vendor.d/10_nvidia.json` 不存在，你可以尝试运行 `sudo apt-get install libglvnd-dev`。`10_nvidia.json` 包含以下内容：

**JSON**

```
{
    "file_format_version" : "1.0.0",
    "ICD" : {
        "library_path" : "libEGL_nvidia.so.0"
    }
}
```

如果 `/etc/vulkan/implicit_layer.d/nvidia_layers.json` 不存在，请尝试创建该文件并填入以下内容：

**JSON**

```
{
    "file_format_version" : "1.0.0",
    "layer": {
        "name": "VK_LAYER_NV_optimus",
        "type": "INSTANCE",
        "library_path": "libGLX_nvidia.so.0",
        "api_version" : "1.2.155",
        "implementation_version" : "1",
        "description" : "NVIDIA Optimus layer",
        "functions": {
            "vkGetInstanceProcAddr": "vk_optimusGetInstanceProcAddr",
            "vkGetDeviceProcAddr": "vk_optimusGetDeviceProcAddr"
        },
        "enable_environment": {
            "__NV_PRIME_RENDER_OFFLOAD": "1"
        },
        "disable_environment": {
            "DISABLE_LAYER_NV_OPTIMUS_1": ""
        }
    }
}
```

更多讨论可以在[这里](https://www.google.com/search?q=https://github.com/haosulab/ManiSkill/issues/52)找到。

如果 Vulkan 驱动损坏，可能会发生以下错误。请尝试按照上述说明重新安装。

```
RuntimeError: vk::Instance::enumeratePhysicalDevices: ErrorInitializationFailed
```

```
Some required Vulkan extension is not present. You may not use the renderer to render, however, CPU resources will be still available.
```

```
Segmentation fault (core dumped)
```

如果你仍有问题，可以检查 NVIDIA 驱动。首先运行

**Bash**

```
ldconfig -p | grep libGLX_nvidia
```

如果找不到 `libGLX_nvidia.so`，那么很可能你安装了不正确的驱动。要在 Linux 上获取正确的驱动，建议安装 **`nvidia-driver-xxx`** (不要使用包名中带有 `server` 的版本)，并避免使用任何其他安装方法，如 `runfile`。

wsl安装的话

```
sudo -E apt-get install -y libnvidia-gl-580
```

-E可以使用环境变量网络

```
ldconfig -p | grep libGLX_nvidia
        libGLX_nvidia.so.0 (libc6,x86-64) => /lib/x86_64-linux-gnu/libGLX_nvidia.so.0
```



*注意：关于wsl

If you still have some issues, you can check the NVIDIA drivers. First run

ldconfig -p | grep libGLX_nvidia
If libGLX_nvidia.so is not found, then it is likely that you have installed an incorrect driver. To get the right driver on linux, it is recommended to install nvidia-driver-xxx (do not use the ones with server in the package name) and to avoid using any other method of installation like a runfile

看了官网文档。因为我是wsl，因此nvidia的driver我是没有在linux中安装的，虽然wsl上来nvidia-smi可用，但是nvcc是不可用的。因此driver和toolkit都需要安装。



>你完全理解到问题的核心了！说得非常对。

这就是在 WSL 环境下最容易混淆的一点，你已经把它理清了：

1. 驱动 (Driver) 在 Windows: nvidia-smi 之所以能用，是因为你的 Windows 主机上安装了 NVIDIA 驱动。WSL2 通过一个特殊的机制直接和这个驱动通信来获取 GPU 信息，但它只提供了最基础的桥梁。

1. 工具包 (Toolkit) 和用户态库在 Linux: 像 nvcc (CUDA 编译器) 和 sapien/Vulkan 需要的更深层的库（比如 libcuda.so, libvulkan.so 以及我们之前找到的 nvidia_icd.json），并不会自动出现在 WSL 里。这些都需要通过在 WSL 内部安装 CUDA Toolkit for WSL 来提供。

你引用的那段文档是针对裸机 Linux (Bare-metal Linux) 的，在那种环境下，你需要用 apt 安装 nvidia-driver-xxx。但在 WSL 里，你绝对不能这样做，否则会破坏 WSL 和 Windows 驱动之间的连接。

所以，你的结论是完全正确的：我们需要在你的 WSL (Ubuntu) 环境里，安装官方的 NVIDIA CUDA Toolkit。 这会一并解决 nvcc 不可用和 Vulkan 驱动不兼容的问题。

请参考wsl安装cuda驱动
