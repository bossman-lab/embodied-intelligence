# README 09：飞书控制桌宠

完成这一章后，读者应该能够把飞书当成主要入口来使用 OpenClaw，并通过飞书消息控制 MagicBox 桌宠的状态、模式和板端能力。网页前端不再是唯一入口，必要时可以只保留为备用方案。

## 一、先分清两件事

OpenClaw 的飞书能力分成两层。

第一层是 OpenClaw 自己的网关和机器人插件。它负责把飞书消息送到本地 OpenClaw，再把回复发回飞书。

第二层是板端能力，也就是 `magicboxctl` 这一组命令。它负责真正控制灯光、语音、舵机、按钮映射和 Demo。

这意味着，飞书里看到的“状态回复”本质上还是板端状态，只是由 OpenClaw 把结果转成了飞书消息。

## 二、先把飞书网关跑起来

用户在安装飞书插件之后，如果日志里出现 `Gateway service missing`，通常表示插件已经装好，但网关服务还没有启动。

在安装了 OpenClaw 的那台 Windows 电脑上，先执行：

```powershell
openclaw gateway install
openclaw gateway
openclaw gateway status
```

如果系统里已经有计划任务，也可以直接启动计划任务：

```powershell
schtasks /Run /TN "OpenClaw Gateway"
```

如果你想持续看日志，可以再执行：

```powershell
openclaw logs --follow
```

看到网关已运行、飞书机器人已完成配置之后，再去飞书里发消息测试。

如果你已经在前台手动启动过网关，想重新拉起它，直接用：

```powershell
openclaw gateway restart
```

如果你是用窗口里跑着的前台进程，`Ctrl+C` 只会停掉当前这个前台进程；它不会清空飞书里的历史会话，也不会自动把旧会话切成新会话。  
所以要分清两件事：

- `openclaw gateway restart`：重启网关进程
- `/reset`：清掉飞书里的当前会话历史

如果你想重新开始一段飞书对话，先在飞书里发：

```text
/reset
```

如果你想单独开一条新的测试会话，也可以直接换一个新的 `sessionKey`，例如：

```text
请把 sessionKey 设为 agent:main:test7。
```

## 二点一、如果你要直接查板端

有些问题不适合只靠飞书回答，尤其是当你需要确认板端服务、灯光、语音链路或者按钮映射时，直接 SSH 到板子上更快。

先登录板端：

```bash
ssh sunrise@192.168.127.10
```

如果需要 root 权限，再切到 root：

```bash
sudo -s
# 或者
sudo su -
```

板端控制统一通过：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl status
```

常用的板端检查命令还有：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
sudo /userdata/magicclaw/runtime/bin/magicboxctl fan status
```

如果你要立刻试灯光，可以直接在板端执行：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl led preset red
sudo /userdata/magicclaw/runtime/bin/magicboxctl led rgb 255 0 0
```

## 二点二、如果飞书要真正控制板端

飞书这边要真正落到板端动作，通常需要满足两种方式中的一种：

1. OpenClaw 已经拿到了可用的板端工具，能直接调用 `magicboxctl`。
2. 没有板端工具时，先 SSH 到板端，再在板端执行 `magicboxctl`。

所以当飞书回复你“我目前没有控制 MagicBox 灯效的可用接口”时，不要继续只问“能不能做”。要改成下面这种路径：

先 SSH 到板端：

```bash
ssh sunrise@192.168.127.10
```

再执行板端命令：

```bash
sudo /userdata/magicclaw/runtime/bin/magicboxctl status
sudo /userdata/magicclaw/runtime/bin/magicboxctl led preset red
sudo /userdata/magicclaw/runtime/bin/magicboxctl led rgb 255 0 0
sudo /userdata/magicclaw/runtime/bin/magicboxctl buttons show
sudo /userdata/magicclaw/runtime/bin/magicboxctl voice status
sudo /userdata/magicclaw/runtime/bin/magicboxctl servo both 10 50
```

这条路径的作用是把“飞书里的意图”先落到“板端上的明确命令”。只要板端命令已经跑通，飞书后面再接工具就会顺很多。

## 三、飞书里能用哪些常见命令

OpenClaw 的飞书入口目前是“文本命令”，不是一个单独的按钮面板。最常见的内置命令是：

```text
/status
/reset
/model
```

它们分别用于：

- `/status`：查看当前会话、模型和运行状态
- `/reset`：重置当前会话
- `/model`：查看或切换模型

如果你想把飞书作为桌宠的主控入口，建议把常用需求都写成短句，而不是先去想浏览器怎么点。下面这些句式更适合直接发到飞书：

- `请返回当前板端状态。`
- `请告诉我当前时间。`
- `请列出当前技能。`
- `请启动双目模式。`
- `请启动手势模式。`
- `请启动完整语音对话。`
- `请执行 YOLO Demo。`
- `请把左键设为双目，中键设为手势，右键设为语音对话。`
- `请朗读一句：你好，我已经启动。`
- `请把左支撑角转到 15 度，右支撑角转到 45 度。`
- `请把四个灯全部设为红色。`
- `请把第1盏灯设为红色，第2盏灯设为绿色，第3盏灯设为蓝色，第4盏灯设为白色。`
- `请让灯光闪烁三次，颜色用蓝色。`

这些短句的好处是，读者不用记住底层脚本，只要记住自己的目标就行。OpenClaw 会把它们转成板端工具调用。

## 四、如果飞书回复要求你提供 sessionKey

有时你在飞书里发出控制请求后，机器人会先回你一句“当前会话还没有板端状态”或者“请先提供 sessionKey / 设备名称”。这不是灯光命令失败，而是当前这条飞书消息还没有绑定到具体的板端会话。

这类提示通常出现在两种情况：

- 你发的是一个新的飞书会话，OpenClaw 还不知道它对应哪一块板子。
- 你发的是自然语言，但当前机器人更需要明确的会话键来定位目标板端。

遇到这种情况，直接在飞书里补一句板端标识即可。最稳的写法是：

```text
请把 sessionKey 设为 agent:main:test7，然后返回当前板端状态。
```

或者：

```text
请控制 agent:main:test7 这块板子，把四个灯都设为红色。
```

如果你不想记会话键，至少要把“目标板子”说清楚，例如：

```text
请控制当前这块 MagicBox，把四个灯设为红色。
```

如果机器人仍然追问 sessionKey，说明它还没有拿到足够明确的目标绑定信息。这时不要重复发同一句灯光命令，而是先把会话键或板端名称补全，再继续发控制指令。

## 四、板端状态应该怎么回

如果你只是想知道桌宠现在怎么样，最稳的做法是让飞书机器人返回一段板端摘要，而不是直接报一堆底层日志。

当前板端已经确认可用的摘要包括：

- 安装根目录
- 当前时间
- U 盘使用情况
- `magicclaw.service` 状态
- `magicclaw-buttons.service` 状态
- 双目、手势、语音、YOLO 模式状态
- 语音链路状态
- 音量状态

也就是说，飞书里问“当前板端状态”时，回复内容应该像这样：

- 网关是否在线
- 桌宠当前在什么模式
- 语音链路是否已经启动
- 灯光和舵机是否可用

如果你要的是 CPU、内存、负载这类更细的系统指标，当前 `magicboxctl status` 还没有把它们当成默认字段。这个需求可以后续再加一个专门技能，但不要把它误写成已经内置支持。

## 五、推荐的飞书使用顺序

如果你打算把飞书作为主入口，建议按下面顺序操作。

1. 在 Windows 上启动 OpenClaw 网关。
2. 在飞书里确认机器人已经配置成功。
3. 先发 `/status`，确认网关和会话都正常。
4. 再发一条板端摘要请求，例如 `请返回当前板端状态。`
5. 然后再发控制命令，例如 `请启动语音对话`、`请执行双目模式` 或 `请调整舵机到打招呼姿态`。

这样做的好处是，先验证链路，再验证控制，定位问题更快。

## 六、常见问题

### 1. 日志里出现 `Gateway service missing`

这说明你只安装了插件，但网关没有启动。先执行：

```powershell
openclaw gateway install
openclaw gateway
```

再回到飞书测试。

### 2. 飞书里能收到机器人，但板端没动作

先确认板端的 `magicclaw.service` 和 `magicclaw-buttons.service` 是否正常运行，然后再看是否已经有对应的技能或命令映射。

### 3. 只想用飞书，不想再开网页前端

可以。飞书完全可以作为主入口，网页 Lite 页只保留为备用入口即可。

### 4. 想问 CPU/内存/负载

当前默认命令没有把这些指标单独暴露出来。建议先问板端摘要；如果后面确实需要系统指标，再新增一个专门技能。

## 七、本章最后的结论

如果你想把 OpenClaw 当成桌宠的总入口，最稳的做法不是先盯网页页面，而是先把飞书网关跑起来，再把常用板端能力收敛成少量文本命令。

这样读者只需要记住三件事：

1. 网关要启动。
2. 飞书里发短句或斜杠命令。
3. 真正的桌宠动作还是由 `magicboxctl` 完成。
