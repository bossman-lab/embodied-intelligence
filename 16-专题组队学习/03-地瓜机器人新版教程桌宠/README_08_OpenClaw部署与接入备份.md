# README 06：OpenClaw 部署、接管与板端控制

完成这一章后，读者应该能够在 MagicBox 上完成四件事。第一，确认 `magicclaw.service` 和 `magicclaw-buttons.service` 是否已经正常运行。第二，理解左、中、右三个物理按键分别代表什么，以及它们可以被重新映射到哪些动作。第三，知道哪些 `magicboxctl` 命令属于纯本地硬件控制，哪些命令必须先启动 ROS 语音链路。第四，知道 OpenClaw 自带后端与本教程提供的 Lite 前端分别负责什么，以及网页前端应该如何访问。

## 一、本章完成后的验收目标

本章不是单纯把网页打开，而是要求下面几项同时成立。

- `magicclaw.service` 处于 `active (running)`，并且 `curl http://127.0.0.1:18789/health` 能返回健康状态。
- `magicclaw-buttons.service` 处于 `active (running)`，三个物理按键已经能够交给 MagicClaw 侧重新映射。
- `magicboxctl buttons show`、`magicboxctl voice ...`、`magicboxctl servo ...` 这些命令都能被正确理解，不再把需要前置服务的命令当成“随时都能独立执行”。
- 读者知道 OpenClaw 有浏览器控制相关后端，但当前稳定可用的网页入口应以本教程提供的 Lite 前端为主。

## 二、本章采用哪一套运行模式

MagicBox 接入 OpenClaw 之后，实际上存在两套不同的运行方式。

第一套是原厂模式，也就是 `magicbox-start` 模式。它仍然由 `/userdata/magicbox/launch/start.py` 接管按键逻辑。左键固定进入双目，中键固定进入手势，右键固定进入语音。它更接近原厂演示体验，灯光、提示音和按键入口都沿用原厂设计，但它并不适合“在前端聊天框里动态改键位”的教程场景。

第二套是本章采用的模式，也就是 MagicClaw 接管按键模式。在这一模式下，`magicclaw-buttons.service` 负责监听三个物理按键，`magicboxctl buttons set ...` 负责写入按键映射，`magicboxctl buttons invoke ...` 负责触发按键动作。这种方式更适合课程演示、前端对话控制和板端能力编排。

这两套模式不能同时作为按键入口使用。原因很直接：原厂 `magicbox-start` 自身就会监听按键，如果再让 `magicclaw-buttons.service` 同时监听，就会出现一次按键触发两套逻辑的问题。因此，本章默认采用 MagicClaw 接管按键模式，`magicbox-start` 不作为按键入口常驻启用。

## 三、开始之前先确认环境

本章所有命令都默认在开发板终端中执行，除非某一步明确写的是在 Windows 主机上执行。下面这些条件应当先满足。

- 开发板已经通过网线连接，板端 IP 仍然是 `192.168.127.10`。
- 可以通过 `ssh sunrise@192.168.127.10` 登录开发板。
- OpenClaw / MagicClaw bundle 已经安装到 `/userdata/magicclaw`。
- 当前板端使用的是 MagicClaw 接管按键模式，而不是原厂按键模式。

先在开发板终端中执行下面这组检查命令：

```bash
ls -ld /userdata/magicclaw
ls -l /userdata/magicclaw/runtime/bin/magicboxctl
ls -l /etc/systemd/system/magicclaw.service
ls -l /etc/systemd/system/magicclaw-buttons.service
```

如果这些路径都存在，说明板端安装结果是完整的。本章后续所有命令都以这些路径为准。

## 四、正式操作前先检查服务状态

这一组命令可以在任意目录执行，不需要先 `source` ROS 环境，因为这里检查的是 `systemd` 服务本身。

```bash
sudo systemctl status magicclaw.service --no-pager
sudo systemctl status magicclaw-buttons.service --no-pager
curl http://127.0.0.1:18789/health
```

看到下面这些结果，才说明可以继续做浏览器接入和按键控制。

- `magicclaw.service` 显示 `active (running)`。
- `magicclaw-buttons.service` 显示 `active (running)`。
- 健康检查返回类似 `{"ok":true,"status":"live"}` 的结果。

如果这一步没有通过，就不要先打开浏览器。因为旧仪表盘和 Lite 页面都只是控制入口，网关服务本身没有起来时，网页一定无法正常工作。

## 五、左、中、右三个物理按键分别怎么看

本章统一采用下面的方向定义，避免“左右到底是从人看还是从板子看”的歧义。

- `left`：从设备正面朝向用户时的左键。
- `middle`：中间键。
- `right`：从设备正面朝向用户时的右键。

当前按键守护进程监听的 GPIO 定义如下。

| 教程术语 | GPIO(BCM) | 说明 |
| --- | --- | --- |
| `left` | 22 | 设备正面朝向用户时的左键 |
| `middle` | 16 | 中间键 |
| `right` | 26 | 设备正面朝向用户时的右键 |

如果要看当前映射关系，可以直接执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
```

执行成功后，应当返回一段 JSON，例如：

```json
{
  "left": "stereo",
  "middle": "gesture",
  "right": "voice_chat"
}
```

这说明左、中、右三个物理键当前分别绑定到了哪一种动作。

## 六、七种按钮动作分别是什么意思

当前可写入按键映射的动作一共有七种：`stereo`、`gesture`、`voice_chat`、`voice_asr`、`yolo`、`stop_all`、`off`。这些动作不是抽象名称，而是 `magicboxctl` 中已经实现好的执行分支。

### 1. `stereo`

`stereo` 用于启动双目 Demo。按下后会执行双目链路，同时把灯光切成红色，并把活动模式写成 `stereo`。如果再次按下同一个已经处于活动状态的 `stereo` 键，会关闭当前双目模式。

### 2. `gesture`

`gesture` 用于启动手势 Demo。按下后会把灯光切成绿色，并把活动模式写成 `gesture`。如果再次按下同一个已经处于活动状态的 `gesture` 键，会关闭当前手势模式。

### 3. `voice_chat`

`voice_chat` 用于启动完整的本地语音对话链路。当前实现已经按原厂右键语音模式对齐：先确保 `audio_io` 语音底座存在，再单独启动 `qwen_llm`，不再重复拉起第二个 `audio_io`。按下后灯光切成蓝色，并把活动模式写成 `voice_chat`。如果再次按下同一个已经处于活动状态的 `voice_chat` 键，会关闭当前语音对话模式。

### 4. `voice_asr`

`voice_asr` 只启动语音识别与播报底座，也就是 `audio_io` 这一条链路，不会把完整的本地 LLM 对话一起拉起来。它会把灯光切成青色，并把活动模式写成 `voice_asr`。本章不把它写成“再次按同一键一定等价于关闭”，如果要明确关闭，直接执行 `magicboxctl voice asr stop` 更可靠。

### 5. `yolo`

`yolo` 用于启动 YOLO Demo。按下后会把灯光切成洋红色，并把活动模式写成 `yolo`。如果再次按下同一键，会按普通模式切换逻辑把它关闭。

### 6. `stop_all`

`stop_all` 的作用是停止当前所有模式。它会清空活动状态，并尝试把灯熄灭。这个动作适合作为“紧急停止”或“回到空闲态”的专用按键映射。

### 7. `off`

`off` 的意思不是“关机”，而是“保留这个按键，但按下时不启动任何模式”。如果某一个键位暂时不希望分配功能，可以把它映射成 `off`。

下面给出汇总表。

| 动作 | 实际作用 | 灯光 | 是否写入 active | 再按同键是否关闭 |
| --- | --- | --- | --- | --- |
| `stereo` | 启动双目 Demo | 红色 | 是 | 是 |
| `gesture` | 启动手势 Demo | 绿色 | 是 | 是 |
| `voice_chat` | 先确保 `audio_io` 存在，再启动 `qwen_llm` | 蓝色 | 是 | 是 |
| `voice_asr` | 只启动 `audio_io` | 青色 | 是 | 教程里不写死为“是” |
| `yolo` | 启动 YOLO Demo | 洋红 | 是 | 是 |
| `stop_all` | 停止所有模式 | 熄灯 | 清空 | 不适用 |
| `off` | 不执行动作 | 不变 | 否 | 不适用 |

## 七、如何查看、修改和触发三个按键

下面这组命令默认在任意目录执行即可，不依赖 ROS 环境。

先看当前映射：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
```

再写入一组接近原厂体验的默认映射：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set left stereo
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set middle gesture
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons set right voice_chat
```

执行成功后，终端通常会分别返回：

- `left mapped to stereo`
- `middle mapped to gesture`
- `right mapped to voice_chat`

如果要在不按物理键的前提下直接模拟按键动作，可以执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons invoke right
```

如果当前 `right` 已经映射到 `voice_chat`，预期结果是：

```text
right triggered voice_chat
```

如果要看按键守护服务是否仍在运行，可以执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons daemon status
```

这一节的成功标准不是只有“命令能回显”，而是要能回答两个问题：当前三个物理键分别绑定到什么动作，以及模拟按下其中一个键后，能不能得到与映射一致的结果。

## 八、哪些命令属于纯本地硬件控制，哪些命令需要先启动链路

`magicboxctl` 的命令并不都属于同一类。

第一类是纯本地硬件控制命令，例如 `led pixel`、`led pattern`、`servo set`、`servo greet`。这类命令直接调用本地硬件脚本，不依赖 ROS 话题订阅者，也不要求先启动语音链路。

第二类是需要本地 ROS 链路已经存在的命令，例如 `voice say` 和 `voice prompt`。这两条命令本质上不是“直接播放一句话”，而是向特定 ROS 话题发布一条 `std_msgs/String` 消息。

- `voice say` 发布到 `/tts_text`
- `voice prompt` 发布到 `/prompt_text`

如果当前没有对应的订阅者，它们就会等待，并出现下面这种提示：

```text
Waiting for at least 1 matching subscription(s)...
```

这不是死机，而是当前没有消费者在监听这两个话题。

第三类是模式切换命令，例如 `buttons set`、`buttons invoke`、`voice asr start`、`voice chat start`。这类命令会拉起或关闭某条模式链路，并改变板端当前的活动状态。

## 九、语音链路应该怎样启动，为什么 `voice say` 会卡住

如果目标只是让板子先进入语音识别与播报底座状态，可以执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice asr start
```

执行成功后，再查看状态：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
```

理想结果应当至少看到：

```text
voice_asr: running
```

如果希望启动完整语音对话链路，而不是只拉起 `audio_io`，应当执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice chat start
```

再查看状态：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
```

理想结果是：

```text
voice_asr: running
voice_chat: running
```

当前 `magicboxctl voice chat start` 已经按原厂右键模式对齐：先拉起 `audio_io`，再启动 `qwen_llm`，并使用与板端节点一致的 ROS 中间件配置。因此它比“在一条命令里重复启动第二个 `audio_io`”更稳定，也能避免音频设备冲突。

只有在上面的状态已经存在时，再执行下面这些文本注入命令才有意义：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice say "你好，这是板端朗读测试。"
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice prompt "请只回答：测试通过。"
```

这两条命令都已经按板端实机验证通过。其中 `voice prompt` 会把文本送入本地 `qwen_llm`，再由 `/tts_text` 交给 `audio_io` 播报。

## 十、舵机命令如何工作，以及左右应该怎样理解

本节默认在任意目录执行，不需要先 `source` ROS 环境。当前舵机控制走的是本地 PWM 脚本，而不是 ROS 节点。

教程中的 `left` 和 `right`，指的是设备正面朝向用户时的左右支撑角。当前脚本中，左脚 PWM 引脚是 32，右脚 PWM 引脚是 33。安全角度范围应当保持在 `0-90` 之间，推荐把 `30` 作为中位。

首次测试建议先执行下面这组命令：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set left 15
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set right 45
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo greet 1
```

如果执行成功，应当在板端看到左右支撑角分别产生动作，最后 `servo greet 1` 会做一次简短的打招呼动作。当前这套控制已经按官方 `/userdata/magicbox/basic_function_demo/servo.py` 的起舵方式修正过，使用的是更接近官方示例的 PWM 启动和保持时间，因此已经通过实机验证。

这里还要明确一个实现边界：当前 `servo set` 并不是“持续保持角度”的锁定控制，而是“发出一次动作脉冲，保持一小段时间后释放 GPIO”。脚本内部会在动作结束后执行 `GPIO.cleanup()`。因此，如果读者期待的是“下完命令后一直锁死在那个角度”，那并不符合当前实现。这一点必须理解清楚，避免把“没有持续锁定”误判成“命令没有生效”。

如果命令执行后完全没有反应，排障顺序应当是：先查权限，再查 GPIO 是否被占用，最后再查硬件连接；不要先去查 ROS，因为这一部分本来就不依赖 ROS。

## 十一、网页前端应该怎么访问

这一节要先讲清楚一个容易混淆的问题：OpenClaw 自带的是浏览器控制相关后端，不等于当前环境里一定有一个可以直接远程打开的官方前端页面。

当前板端上，已经确认有两类与网页相关的入口：

- `ws://0.0.0.0:18789`：网关 WebSocket，对局域网开放。
- `http://127.0.0.1:18791`：browser control 后端接口，只监听板端本机，并且要求 Bearer Token 认证。

这意味着 OpenClaw 本身确实带有网页控制相关后端能力，但它并没有在你当前这块板子上提供一个“直接远程访问就稳定可用”的官方前端页面。尤其是 `18791` 这个地址，本质上是后端接口，不是给读者直接点开的网页 UI。直接浏览器打开它，出现 `Unauthorized`，是符合后端设计的正常结果。

因此，本教程的结论非常明确：

- 如果只是研究 OpenClaw 自带后端，关注的是 `18789` 和 `18791` 这两个接口。
- 如果希望有一个稳定、适合课程截图、适合对话控制、适合局域网调试的网页入口，应当以本教程提供的 Lite 前端为主。

## 十二、旧仪表盘为什么不适合作为当前主入口

旧仪表盘地址通常写成：

```text
http://192.168.127.10:18789/chat?session=main
```

它在某些环境里可以工作，但在你当前这种：

- 网线直连
- HTTP 非安全上下文
- 不是板端 localhost
- 浏览器直接从局域网地址访问

的场景下，很容易报出：

```text
device identity required
```

这不是“板子没启动”，也不是“端口没转发过来”。更准确的理解是：旧控制页仍然带着设备身份校验相关的握手逻辑，而当前访问环境没有满足它的要求。

因此，本教程不再把旧 `18789/chat` 页写成主入口。它可以作为历史接口和排障对象保留，但不再作为推荐的日常操作入口。

## 十三、Lite 前端为什么是当前推荐入口

当前稳定可用的网页入口是本教程提供的 Lite 前端。原因很简单：它是为 MagicBox 这块板子的局域网 bring-up、教程截图和调试控制专门准备的，绕开了旧 OpenClaw 网页 bundle 在设备身份校验上的不稳定因素。

Lite 前端更适合做下面这些事：

- 在局域网环境下直接连接板端网关。
- 配合 `magicboxctl` 做对话式控制和排障。
- 用于截图、演示和读者复现。

本章的使用建议因此很明确：

- 需要稳定、直接、可复现的网页控制时，用 Lite 前端。
- 研究 OpenClaw 自带后端时，再分别查看 `18789` 和 `18791`。
- 不建议把旧 `18789/chat` 当成当前主入口。

## 十四、常见故障与恢复方法

### 1. `Waiting for at least 1 matching subscription(s)...`

这通常出现在 `voice say` 或 `voice prompt` 中。原因不是命令语法错了，而是当前没有订阅者监听 `/tts_text` 或 `/prompt_text`。处理方法是先执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice asr start
```

或者：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice chat start
```

然后再执行文本注入命令。

### 2. `device identity required`

如果旧仪表盘出现这一错误，先不要把问题归因到板子或服务本身。先执行：

```bash
curl http://127.0.0.1:18789/health
```

如果健康检查正常，说明问题是旧控制页的设备身份握手，不是网关没有启动。此时应直接切换到 Lite 前端继续控制。

### 3. 按钮改了，但按下没有反应

先检查服务：

```bash
sudo systemctl status magicclaw-buttons.service --no-pager
```

再检查映射：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
```

最后直接模拟按键：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons invoke left
```

如果 `invoke` 能工作而实体按键无反应，问题优先落在按键监听层，而不是映射层。

### 4. 舵机命令执行后没有动作

先确认执行的是：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set left 15
```

或：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo set right 45
```

如果没有动作，先查权限和 GPIO 占用，再查硬件连接。不要先查 ROS，因为舵机命令本来就不依赖 ROS。

## 十五、本章验收清单

完成本章后，读者应该能够用下面这组清单自检。

- 我已经知道当前教程采用的是 MagicClaw 接管按键模式，而不是原厂按键模式。
- 我能够说清楚 `stereo`、`gesture`、`voice_chat`、`voice_asr`、`yolo`、`stop_all`、`off` 七种动作分别代表什么。
- 我能够通过 `buttons show` 查看当前映射，并通过 `buttons set` 修改左、中、右三个物理按键。
- 我知道 `voice say` 和 `voice prompt` 不是独立的本地朗读命令，而是依赖 ROS 订阅者的消息注入命令。
- 我知道 `servo set` 属于纯本地 PWM 动作，不依赖 ROS，并且当前实现不会持续锁定角度。
- 我知道 OpenClaw 本身带有浏览器控制相关后端，但在当前环境下稳定可用的网页入口应以 Lite 前端为主，而不是旧 `18789/chat` 页。
