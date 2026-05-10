```
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak && sudo tee /etc/apt/sources.list > /dev/null <<'EOF'
# 默认注释了源码镜像以提高 apt update 速度，如有需要可自行取消注释
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
# deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
# deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
# deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse

deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
# deb-src http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
EOF
```

```
sudo apt update

sudo apt install -y xfce4 xfce4-goodies
sudo apt install -y xrdp


echo "xfce4-session" > ~/.xsession

# 编辑 xrdp 启动脚本
sudo sed -i 's/^test -x \/etc\/X11\/Xsession && exec \/etc\/X11\/Xsession$/startxfce4/' /etc/xrdp/startwm.sh

# 或者手动编辑 /etc/xrdp/startwm.sh，在文件末尾添加：
# startxfce4

# 默认端口是 3389，如需修改可编辑配置文件
sudo nano /etc/xrdp/xrdp.ini
# 找到 port=3389 这行，可以修改为其他端口

sudo service xrdp start

# 检查服务状态
sudo service xrdp status

# 在 WSL2 中，可以在 ~/.bashrc 或 ~/.zshrc 末尾添加：
# sudo service xrdp start
```





详细步骤如下

# WSL 使用 xrdp 启动图形界面教程



## 1. 安装图形界面环境

首先，需要选择并安装一个桌面环境。这里提供两个常用选项：

### 选项A：安装 Xfce（轻量级，推荐）

```bash
sudo apt update
sudo apt install -y xfce4 xfce4-goodies
```

### 选项B：安装 Ubuntu Desktop（完整桌面）

```bash
sudo apt update
sudo apt install -y ubuntu-desktop
```

## 2. 安装 xrdp

```bash
sudo apt install -y xrdp
```

## 3. 配置 xrdp

```bash
# 配置 xrdp 使用 Xfce
echo "xfce4-session" > ~/.xsession

# 编辑 xrdp 启动脚本
sudo sed -i 's/^test -x \/etc\/X11\/Xsession && exec \/etc\/X11\/Xsession$/startxfce4/' /etc/xrdp/startwm.sh

# 或者手动编辑 /etc/xrdp/startwm.sh，在文件末尾添加：
# startxfce4
```

## 4. 配置 xrdp 端口（可选）

```bash
# 默认端口是 3389，如需修改可编辑配置文件
sudo nano /etc/xrdp/xrdp.ini
# 找到 port=3389 这行，可以修改为其他端口
```

## 5. 启动 xrdp 服务

```bash
sudo service xrdp start

# 检查服务状态
sudo service xrdp status
```

## 6. 设置开机自启动（可选）

```bash
# 在 WSL2 中，可以在 ~/.bashrc 或 ~/.zshrc 末尾添加：
# sudo service xrdp start
```

## 7. 连接到图形界面

**在 Windows 上：**

1. 按 `Win + R` 打开运行窗口
2. 输入 `mstsc` 并回车，打开远程桌面连接
3. 在计算机名称处输入：`localhost:3389` 或 `127.0.0.1:3389`
4. 点击连接
5. 输入WSL用户名和密码

## 8. 故障排除

### 黑屏或无法连接

```bash
# 重启 xrdp 服务
sudo service xrdp restart

# 检查端口是否被占用
netstat -an | grep 3389

# 查看 xrdp 日志
cat /var/log/xrdp.log
cat /var/log/xrdp-sesman.log
```

### 优化配置

在 `/etc/xrdp/xrdp.ini` 中可以调整：

```ini
# 颜色深度（提高性能）
max_bpp=16

# 压缩设置
compression_level=9
```

## 9. 额外提示

**性能优化：**
- 如果遇到性能问题，考虑使用 Xfce 而不是 GNOME 或 KDE
- 降低颜色深度可以提高响应速度

**安全建议：**
```bash
# 只允许本地连接
sudo ufw allow from 127.0.0.1 to any port 3389
```

**启动脚本（在 Windows PowerShell 中）：**
```powershell
# 创建一个启动脚本
wsl -d Ubuntu sudo service xrdp start
```

## 10. 替代方案

如果 xrdp 遇到问题，也可以考虑：

- **VcXsrv** 或 **X410**：使用 X Server
- **WSLg**：WSL2 内置的图形支持（需要 Windows 11 或 Windows 10 最新版本）
