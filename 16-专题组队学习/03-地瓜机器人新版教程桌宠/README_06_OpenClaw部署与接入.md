# README 06：OpenClaw 部署、接入与启动

完成这一章后，读者应该能够在 MagicBox 上完成三件事。第一，知道机器重启后前后端进程如何自动起来。第二，知道如果服务没有自动恢复，应该输入什么命令手动启动。第三，知道网页前端应该访问哪个地址，哪些地址是后端接口而不是前端页面。

## 一、重启后先看什么

机器重启后，先不要急着打开浏览器。先在开发板终端执行下面三条命令，确认后端和按键守护都已经起来。

```bash
sudo systemctl status magicclaw.service --no-pager
sudo systemctl status magicclaw-buttons.service --no-pager
curl http://127.0.0.1:18789/health
```

看到下面这些结果，才说明系统已经进入可用状态。

- `magicclaw.service` 显示 `active (running)`。
- `magicclaw-buttons.service` 显示 `active (running)`。
- 健康检查返回类似 `{"ok":true,"status":"live"}` 的结果。

如果这一步没有通过，就先修服务，再看网页。因为网页只是控制入口，后端没有起来时，网页一定不能正常工作。

## 二、重启后怎么手动启动前后端

正常情况下，这两个服务已经被 `systemd` 设置为开机自启。也就是说，机器重启后它们会自动起来，不需要每次手动输入命令。

如果开机后发现服务没有起来，可以直接手动执行下面这组命令。

```bash
sudo systemctl start magicclaw.service
sudo systemctl start magicclaw-buttons.service
```

如果希望以后每次开机都自动启动，执行一次下面这组命令即可。

```bash
sudo systemctl enable magicclaw.service
sudo systemctl enable magicclaw-buttons.service
```

如果需要重新加载配置并重启服务，可以执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart magicclaw.service
sudo systemctl restart magicclaw-buttons.service
```

## 三、网页前端怎么访问

当前稳定可用的网页入口是：

```text
http://192.168.127.10:18789/
```

这个地址现在已经接管为本教程提供的 Lite 前端，适合做课程演示、网页控制和局域网调试。

如果浏览器自动跳到旧的聊天页，或者旧页出现 `device identity required`，不要把它当成主入口继续反复刷新。旧页属于历史兼容入口，当前教程不建议把它作为日常操作入口。

下面两个地址要分清楚。

- `http://192.168.127.10:18789/`：网页前端入口，优先使用。
- `http://127.0.0.1:18791/`：后端认证接口，不是给你直接打开的前端页面。

直接打开 `18791` 返回 `Unauthorized` 是正常现象，因为它需要 Bearer Token 认证，而且它本身不是前端 UI。

## 四、左中右三个按键和网页控制是什么关系

本章默认采用 MagicClaw 接管按键模式，而不是原厂按键模式。

- `left`：设备正面朝向用户时的左键。
- `middle`：中间键。
- `right`：设备正面朝向用户时的右键。

当前三个按键可以重新映射到 `stereo`、`gesture`、`voice_chat`、`voice_asr`、`yolo`、`stop_all`、`off` 这几种动作。

查看当前映射：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
```

写入一组默认映射：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set left stereo
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set middle gesture
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set right voice_chat
```

模拟按键：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons invoke right
```

## 五、哪些命令要先启动语音链路

`voice say` 和 `voice prompt` 不是独立的本地朗读命令，它们需要先有语音链路在运行。

先启动识别底座：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice asr start
```

再看状态：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
```

如果要启动完整对话链路，再执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice chat start
```

有了 `voice_asr: running` 和 `voice_chat: running` 之后，再执行下面两条才有意义。

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice say "你好，这是板端朗读测试。"
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice prompt "请只回答：测试通过。"
```

如果命令卡在 `Waiting for at least 1 matching subscription(s)...`，说明当前没有订阅者监听对应话题，不是命令写错。

## 六、舵机命令怎么用

舵机命令不依赖 ROS，直接执行即可。

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set left 15
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set right 45
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo greet 1
```

本节里的 `left` 和 `right`，指的是设备正面朝向用户时的左右支撑角。当前脚本里，左脚 PWM 引脚是 32，右脚 PWM 引脚是 33。安全角度范围应保持在 `0-90`，推荐把 `30` 作为中位。

如果命令执行后没有动作，先查权限和 GPIO 占用，再查硬件连接，不要先查 ROS。

## 七、常见故障

### 1. 页面显示 `device identity required`

这通常出现在旧聊天页，不是网关没有启动。先执行：

```bash
curl http://127.0.0.1:18789/health
```

如果健康检查正常，就直接使用主页 `http://192.168.127.10:18789/`，不要继续反复刷新旧聊天页。

### 2. 页面显示 `Unauthorized`

这是 `18791` 后端接口的正常返回。这个地址不是网页前端，不要把它当成 UI 页面打开。

### 3. `voice say` 或 `voice prompt` 一直等待

先执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
```

再确认 `voice_asr` 或 `voice_chat` 是否已经运行。如果没有，先启动对应链路。

## 八、本章最后的启动顺序

如果你只想记住最短流程，就记住下面这四步。

1. 重启后先检查服务：

```bash
sudo systemctl status magicclaw.service --no-pager
sudo systemctl status magicclaw-buttons.service --no-pager
```

2. 如果服务没起来，手动启动：

```bash
sudo systemctl start magicclaw.service
sudo systemctl start magicclaw-buttons.service
```

3. 打开网页前端：

```text
http://192.168.127.10:18789/
```

4. 需要语音时再起语音链路：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice chat start
```

## 九、如果你想改成飞书主入口

如果你后面决定不把网页前端作为主入口，而是直接用飞书来控制桌宠，那么启动顺序要换成“先把飞书网关跑起来，再让飞书消息去驱动板端能力”。

先在安装了 OpenClaw 的那台 Windows 电脑上执行：

```powershell
openclaw gateway install
openclaw gateway
openclaw gateway status
```

如果系统里已经注册了计划任务，也可以用：

```powershell
schtasks /Run /TN "OpenClaw Gateway"
```

看到安装日志里出现 `Gateway service missing`，通常表示插件已经装好，但网关还没有真正启动。这个时候不要继续重复扫码，先把网关进程拉起来，再回到飞书里测试。

飞书侧最常见的文本命令是：

```text
/status
/reset
/model
```

其中 `/status` 用来查看当前会话和运行状态，`/reset` 用来重置当前会话，`/model` 用来查看或切换模型。  
如果你要看桌宠本身的状态，就直接在飞书里发自然语言，例如：

- `请返回当前板端状态。`
- `请告诉我当前时间。`
- `请列出当前技能。`
- `请总结语音、按键、灯光、舵机和 Demo 的状态。`

飞书里能不能直接看到 CPU 数值，要看你是否额外加了一个板端工具。当前这套 `magicboxctl status` 只保证返回安装根目录、时间、磁盘占用、服务状态、模式状态和音量摘要，并不把 CPU 当成默认字段。如果你后面确实需要 CPU/内存/负载，建议再单独加一个技能或工具，不要先把它写成已经存在的能力。

如果你打算把飞书当成主入口，网页 Lite 页就退回成备用入口即可。这样课程演示时可以只保留飞书消息流，不必再依赖浏览器页面。
