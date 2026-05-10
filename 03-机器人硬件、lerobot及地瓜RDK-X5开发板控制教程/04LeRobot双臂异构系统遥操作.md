# LeRobot 双臂远程控制系统（Windows 主臂 + Linux 从臂）

本项目提供一个基于 Web 的 SO-101 双臂远程遥操作系统：主臂（Leader）连接在 Windows 电脑上，本地从臂（Follower）连接在 Linux 服务器上。系统复用了 HuggingFace LeRobot 官方驱动，支持端口检测、相机选择、CLI 校准、远程主臂数据上传与网页端遥操作。

---

## 目录
1. [系统组成与依赖](#系统组成与依赖)
2. [Linux 服务器环境配置](#linux-服务器环境配置)
3. [Windows 主臂环境配置](#windows-主臂环境配置)
4. [启动与网页操作流程](#启动与网页操作流程)
5. [校准说明](#校准说明)
6. [远程主臂数据上传](#远程主臂数据上传)
7. [遥操作步骤](#遥操作步骤)
8. [常用 API](#常用-api)
9. [常见问题与排查](#常见问题与排查)

---

## 系统组成与依赖

| 角色 | 内容 |
| ---- | ---- |
| Linux 服务器 | 连接两只 SO-101 从臂；运行 FastAPI + LeRobot；需要 Python 环境（建议 mamba/conda）。 |
| Windows 主机 | 连接两只主臂；运行 LeRobot CLI 校准/数据上传脚本；需 Python3 + LeRobot 源码。 |
| 网络 | Windows 与 Linux 需同网段或可互通；网页通过 `http://<Linux_IP>:8000` 访问。 |
| 相机 | 可选 3 路（左腕/右腕/头部），使用 OpenCV 读取。 |

> **注意**：由于主臂实际连在 Windows 上，若标记为 Remote，Windows 端需要单独配置 LeRobot 环境并运行校准与数据推送脚本。

---

## Linux 服务器环境配置

1. **准备 LeRobot 源码**
   ```bash
   git clone https://github.com/huggingface/lerobot.git /home/sunrise/17robo/250602/lerobot
   pip install -e ".[feetech]"
   # 或使用已有版本，注意与 Windows 侧保持一致
   ```
   
2. **创建并激活 Python 环境**（示例使用 mamba）
   ```bash
   mamba create -n lerobot-latest python=3.10 -y
   mamba activate lerobot-latest
   pip install -r requirements.txt  # 本仓库依赖
   ```

3. **启动服务器脚本**
   ```bash
   cd /home/sunrise/lerobot_bimanual_remote
   export LEROBOT_SRC=/home/sunrise/17robo/250602/lerobot  # 如路径不同请自行修改
   ./start_server.sh
   
   #可以先找到bus位置，需要修改配置文件
   #python lerobot/scripts/find_motors_bus_port.py
   python lerobot/scripts/control_robot.py \
     --robot.type=so101 \
     --robot.cameras='{}' \
     --control.type=calibrate \
     --control.arms='["main_follower"]'
     
   
   ```
   - 脚本会询问校准文件夹（默认 `.cache/calibration/so101_bimanual`）。
   - 自动把 `LEROBOT_SRC` 添加到 `PYTHONPATH`，确保可以导入 LeRobot。
   - 启动后终端会显示访问地址，例如 `http://192.168.1.100:8000`。

---

## Windows 主臂环境配置

1. 安装 Python 3.10+，建议使用 Anaconda / Miniconda。
2. 克隆与 Linux 侧一致的 LeRobot 源码：
   ```powershell
   git clone https://github.com/huggingface/lerobot.git C:\lerobot
   # 可以考虑git checkout user/michel-aractingi/2025-06-02-docs-for-hil-serl
   cd C:\lerobot
   pip install -e ".[feetech]"
   ```
3. 根据实际串口（`COM3`, `COM4` 等）准备好主臂连接。
4. 校准和数据推送脚本都在 Windows 本地执行（详见下文）。

---

## 启动与网页操作流程

1. **访问网页**：在任意浏览器打开 `http://<Linux_IP>:8000`。
2. **端口识别**：
   - Windows 主臂：使用设备管理器或 PowerShell `Get-WmiObject Win32_SerialPort` 查到 `COMx`。
   - Linux 从臂：在网页 “🔍 USB Port Detection” 中执行拔插识别。
3. **手动配置**：在 “Manual Configuration” 中填写四个串口并点击 `Configure Ports`。
4. **相机**：如需使用，点击 `Scan Cameras`，选择对应索引并 `Configure Cameras`。

状态栏会展示连接状态、校准目录和当前主臂来源（Local / Remote）。

---

## 校准说明

系统内置 LeRobot 官方标定流程，网页按钮仅触发 CLI 命令。

1. **Linux 从臂**：
   - 在网页 “Calibration” 区域点击 `CLI: Left Follower` / `CLI: Right Follower`。
   - 立即切换到运行 `start_server.sh` 的终端，按提示移动并回车确认（Middle → Zero → Rotated → Rest 等）。
   - 完成后会在 `CALIBRATION_DIR` 生成 `left_follower.json` 等文件，并自动加载至总线。

2. **Windows 主臂（Remote 模式）**：
   
   - 在 Windows 终端运行：
   - 
   - 这个时候需要修改代码：
   - 每次校准修改代码之后，不用重新pip install 一次：
   - ![image-20251022190858804](C:\Users\kewei\Documents\2025\04资料整理\03具身教程编写\ai-hardware-robotics\03-机器人硬件、lerobot及地瓜RDK-X5开发板控制教程\assets\image-20251022190858804.png)
   
   ![image-20251022185552329](C:\Users\kewei\Documents\2025\04资料整理\03具身教程编写\ai-hardware-robotics\03-机器人硬件、lerobot及地瓜RDK-X5开发板控制教程\assets\image-20251022185552329.png)
   
   这里我们两个主臂，左COM3右COM4，因此需要改两次
   
   我的配置是：
   
   ***左COM3，右COM4***
   ***从臂左/dev/ttyACM1右/dev/ttyACM0***
   
   
   
   - ![image-20251022185152146](C:\Users\kewei\Documents\2025\04资料整理\03具身教程编写\ai-hardware-robotics\03-机器人硬件、lerobot及地瓜RDK-X5开发板控制教程\assets\image-20251022185152146.png)
   - 
   - ![image-20251023160947944](C:\Users\kewei\Documents\2025\04资料整理\03具身教程编写\ai-hardware-robotics\03-机器人硬件、lerobot及地瓜RDK-X5开发板控制教程\assets\image-20251023160947944.png)
   - 
   - 
   - 
   
     ```powershell
     1 file changed
     +24
     -4
     control_configs.py
     +24
     -4
     
     # See the License for the specific language governing permissions and
     # limitations under the License.
     - from dataclasses import dataclass, field
     + import json
     + from dataclasses import dataclass
     from pathlib import Path
     import draccus
     @ControlConfig.register_subclass("calibrate")
     @dataclass
     - class CalibrateControlConfig(ControlConfig):
     -     # List of arms to calibrate (e.g. `--arms='["left_follower","right_follower"]' left_leader`)
     -     arms: list[str] | None = field(default=None, metadata={"nargs": "*"})
     class CalibrateControlConfig(ControlConfig):
         # List of arms to calibrate (e.g. `--arms='["left_follower","right_follower"]' left_leader`)
         arms: list[str] | str | None = None
         def __post_init__(self):
             if self.arms is None:
                 return
             if isinstance(self.arms, str):
                 arm_spec = self.arms.strip()
                 if arm_spec.startswith("[") and arm_spec.endswith("]"):
                     try:
                         parsed = json.loads(arm_spec)
                     except json.JSONDecodeError:
                         items = [s.strip().strip('"').strip("'") for s in arm_spec[1:-1].split(",")]
                     else:
                         items = parsed if isinstance(parsed, list) else [parsed]
                     self.arms = [str(item) for item in items if str(item)]
                 else:
                     self.arms = [arm_spec]
             else:
                 self.arms = list(self.arms)
     @ControlConfig.register_subclass("teleoperate")
     
     ```
   - 按提示完成标定后，将生成的 `main_leader.json` 拷贝到 Linux 服务器的 `CALIBRATION_DIR`（名称需对应 `left_leader.json` / `right_leader.json`）。
   - 若主臂标记为本地（非 Remote），可直接在 Linux 侧运行对应按钮。

> **总结**：只要主臂实际接在 Windows，上述 Windows CLI 校准就必不可少；否则从臂无法正确跟随主臂的零位。

---

## 远程主臂数据上传

遥操作时需要持续上传主臂的实时关节角度（单位：度）。常见做法：

1. **HTTP 循环推送**
   
   ```python
   import requests
   
   LINUX_SERVER = "http://192.168.1.100:8000"
   
   def push_leader(side, positions):
       requests.post(
           f"{LINUX_SERVER}/api/leader/update",
           json={"arm": f"{side}_leader", "positions": positions},
           timeout=1.0,
       )
   
   # 示例（请替换为实际编码器读取值）
   push_leader("left", {
       "shoulder_pan": 10.5,
       "shoulder_lift": -20.3,
       "elbow_flex": 45.0,
       "wrist_flex": 5.0,
       "wrist_roll": 0.0,
       "gripper": 20.0,
   })
   ```
   
2. **WebSocket 推送**（连接 `ws://<Linux_IP>:8000/ws/control`）：
   ```json
   {"type": "leader_state", "arm": "left_leader", "positions": {"shoulder_pan": 10.5, ...}}
   ```

无论使用哪种方式，都需要与主臂硬件保持同步读取。建议在 Windows 侧参考 `control_robot.py --control.type=teleoperate` 的实现，直接获取 `Present_Position`。

---

## 遥操作步骤

1. 完成四只手臂的校准（并确认校准文件存在于 `CALIBRATION_DIR`）。
2. 在 Windows 上启动主臂数据推送脚本（HTTP 或 WebSocket）。
3. 在网页点击 `Connect Robot` → `Start Teleoperation`。
4. 状态改为 “Teleoperation: Active” 后，移动主臂即可观察从臂同步动作；视频区域显示三路相机画面。
5. 结束时点击 `Stop Teleoperation`，再 `Disconnect Robot`。

---

## 常用 API

```http
# 相机
GET  /api/list_cameras              # 扫描可用相机
POST /api/configure/cameras         # 设置相机索引

# 端口检测
POST /api/detect_port/start
POST /api/detect_port/check_unplug
POST /api/detect_port/check_plug
POST /api/detect_port/cancel

# 校准
POST /api/calibrate/{arm}           # 触发 CLI 校准（阻塞直到完成）
GET  /api/motor_positions/{arm}     # 查询当前关节角（用于调试）

# 机器人控制
POST /api/connect
POST /api/disconnect
POST /api/teleoperate/start
POST /api/teleoperate/stop
GET  /api/status                    # 查询连接/校准/主臂来源状态

# 主臂数据接入
POST /api/leader/update             # HTTP 推送主臂角度
WS   /ws/control                    # WebSocket（支持 teleoperate_step、leader_state、get_state）
```

---

## 常见问题与排查

| 问题 | 处理建议 |
| ---- | -------- |
| `ImportError: No module named lerobot` | 确认 `LEROBOT_SRC` 路径正确，并在 `start_server.sh` 启动前 `export LEROBOT_SRC=/path/to/lerobot`。 |
| 网页校准无响应 | 网页提示已弃用——请改用 CLI 按钮并在终端按照提示操作。 |
| 主臂动作从臂不动 | 检查：是否完成四臂校准？主臂推送脚本是否在运行？`/api/status` 是否显示 `Leader Source: Left Remote` 等信息？ |
| 数据推送异常 | 查看服务器日志中 `/api/leader/update` 或 WebSocket 错误，确认 JSON 字段 `arm`/`positions` 正确。 |
| 摄像头黑屏 | 确认相机索引、分辨率以及 USB 带宽；必要时仅启用必需摄像头。 |
| 端口拒绝访问 | Linux 端执行 `sudo chmod 666 /dev/ttyACM*` 或添加到 dialout 组；Windows 端确保串口未被其他程序占用。 |

如需进一步调试，可直接运行 LeRobot CLI 命令（例如 `control_robot.py --control.type=teleoperate`）验证硬件通信是否正常。

---

完成以上步骤，即可使用网页完成 SO-101 双臂远程遥操作：Windows 主臂负责采集并推送状态，Linux 从臂通过 LeRobot 驱动实时跟随。