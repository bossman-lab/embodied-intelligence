**特别注意最后一步配置国内代理，否则在国内无法下载包。**

------

### 方案一：使用 Conda 安装（最推荐，不需要 root 权限）

既然你经常使用 Python 环境，使用 `conda` 安装 Go 是最简单、最干净的方式，而且不需要管理员（sudo）权限。

Bash

```
# 在你的基础环境或特定环境中安装
conda install -c conda-forge go
```

- **优点**：一键安装，版本较新，不污染系统环境。
- **缺点**：只在当前 Conda 环境下有效。

------

### 方案二：Linux 服务器标准安装（官方二进制）

如果你需要全局安装（并且有 `sudo` 权限），或者不想依赖 Conda，这是最标准的做法。

1. **下载安装包**（以 Linux x86-64 为例，版本为 1.23.4）：

   Bash

   ```
   wget https://go.dev/dl/go1.23.4.linux-amd64.tar.gz
   # 如果 go.dev 访问慢，可以使用国内源：
   # wget https://mirrors.ustc.edu.cn/golang/go1.23.4.linux-amd64.tar.gz
   ```

2. **解压到安装目录**（通常是 `/usr/local`）：

   Bash

   ```
   sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.23.4.linux-amd64.tar.gz
   ```

3. 配置环境变量：

   需要将 Go 的二进制目录加到 PATH 中。

   Bash

   ```
   # 编辑 ~/.bashrc
   echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
   # 同时也把 Go 安装第三方工具的目录加进去（比如安装 s5cmd 后会在 $HOME/go/bin）
   echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
   
   # 刷新配置
   source ~/.bashrc
   ```

------

### 方案三：Windows / macOS 安装

- **Windows**: 直接去官网下载 `.msi` 安装包，双击运行，一路 Next 即可。它会自动配置环境变量。
- **macOS**: 如果装了 Homebrew，直接运行 `brew install go`。

------

### 🚨 关键步骤：配置国内加速代理（GOPROXY）

这一步非常重要！

如果不配置，在国内运行 go install github.com/... 几乎 100% 会超时失败，因为 Go 默认源被墙了。

请在终端执行以下命令开启国内代理（七牛云或阿里云源）：

Bash

```
# 启用 Go Modules 功能
go env -w GO111MODULE=on

# 配置 GOPROXY 代理 (推荐使用七牛云的 goproxy.cn，速度很稳)
go env -w GOPROXY=https://goproxy.cn,direct
```

------

### 验证是否成功

安装并配置完后，运行以下命令测试：

1. **检查版本：**

   Bash

   ```
   go version
   # 输出示例: go version go1.23.4 linux/amd64
   ```

2. **这时候你就可以安装 s5cmd 了：**

   Bash

   ```
   go install github.com/peak/s5cmd/v2@latest
   ```

   *(安装完成后，`s5cmd` 可能会在 `~/go/bin/` 下，如果前面配置了 PATH，直接输 `s5cmd` 就能用了)*





# 备注 其他下载方式



这是一个标准的 **AWS S3** 存储桶路径。要下载这个路径下的内容，通常不需要传统的“API Key”，而是使用 **AWS CLI** 命令行工具。

针对你的三个问题，简要回答如下：

1. **怎么下载：** 使用 AWS CLI 或兼容 S3 的工具（如 `s5cmd`）。
2. **需要 API 吗：** 如果是公开数据集（OpenPI 看起来像开源项目），通常**不需要**账号或密钥（使用 `--no-sign-request` 参数）。如果是私有的，则需要配置 AWS 凭证（Access Key）。
3. **可以多线程加速吗：** **可以**。AWS CLI 自带并发功能，但使用 `s5cmd` 工具通常能跑满带宽，速度更快。

以下是具体的下载方案，按推荐程度排序：

------

### 方法一：使用 `s5cmd` (推荐，速度最快)

如果你追求**极致的多线程下载速度**，强烈推荐使用 [s5cmd](https://github.com/peak/s5cmd)。它是用 Go 写的，并发性能极强，比官方 CLI 快很多。

1. **安装 s5cmd:**

   - **Linux (通过 go):** `go install github.com/peak/s5cmd/v2@latest`
   - **Linux (直接下载):** 在 release 页面下载二进制文件解压即可。
   - **Conda:** `conda install -c conda-forge s5cmd`

2. 执行下载 (假设是公开桶):

   --no-sign-request 表示匿名访问，无需登录。

   Bash

   ```
   s5cmd --no-sign-request cp --concurrency 50 "s3://openpi-assets-simeval/pi0_fast_droid_jointpos/*" ./local_folder/
   ```

   - `--concurrency 50`: 开启 50 个线程并发（可以根据你的带宽调整）。

------

### 方法二：使用官方 AWS CLI (标准做法)

这是最通用的方法。

1. **安装 AWS CLI:**

   Bash

   ```
   pip install awscli
   # 或者使用 conda
   conda install -c conda-forge awscli
   ```

2. 执行下载:

   由于这是一个目录，需要使用 sync 命令或者 cp --recursive。

   情况 A：如果是公开数据集 (Public Bucket)

   通常开源项目（如 OpenPI）的数据集是对外公开的，不需要登录 AWS 账号。

   Bash

   ```
   aws s3 sync s3://openpi-assets-simeval/pi0_fast_droid_jointpos ./local_target_folder --no-sign-request
   ```

   - 注意：`--no-sign-request` 是关键，它告诉 AWS "我没有账号，让我试试匿名下载"。

   情况 B：如果是私有数据集

   如果上面的命令报错 Access Denied，说明需要权限。你需要：

   1. 注册 AWS 账号。
   2. 获取 Access Key ID 和 Secret Access Key。
   3. 运行 `aws configure` 输入密钥。
   4. 去掉 `--no-sign-request` 参数再次运行。

3. 如何加速 AWS CLI:

   AWS CLI 默认就是多线程的，但你可以通过修改配置来压榨性能：

   Bash

   ```
   aws configure set default.s3.max_concurrent_requests 20
   aws configure set default.s3.max_queue_size 10000
   ```

------

### 方法三：使用 Python (`boto3`)

如果你想在代码里直接加载，而不是下载到硬盘，可以使用 Python 的 `boto3` 库。

Python

```
import boto3
from botocore import UNSIGNED
from botocore.config import Config

# 配置匿名访问 (对应 --no-sign-request)
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

bucket_name = 'openpi-assets-simeval'
prefix = 'pi0_fast_droid_jointpos'

# 列出文件
paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

for page in pages:
    if 'Contents' in page:
        for obj in page['Contents']:
            print(f"Found: {obj['Key']}")
            # 在这里添加下载逻辑: s3.download_file(...)
```

### 总结建议

- **首选：** 试一下 **方法二** 中的 `aws s3 sync ... --no-sign-request`。这是最快验证是否需要权限的方法。
- **如果文件很大：** 请务必使用 **方法一 (`s5cmd`)**，它在大文件和大量小文件的下载场景下，速度通常是官方 CLI 的数倍。

**是否需要我帮你写一个自动检测该 Bucket 是否公开并自动选择最快方式下载的 Python 脚本？**