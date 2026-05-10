```

# create conda env
conda create -n py310-robosuite python=3.10
conda activate py310-robosuite

# install robosuite
git clone https://github.com/box2ai-robotics/robosuite-joycon.git
cd robosuite-joycon
pip3 install -r requirements.txt
pip3 install -r requirements-extra.txt

# install joycon-robotics
cd ..
git clone https://github.com/box2ai-robotics/joycon-robotics.git
cd joycon-robotics # 需要修改setup.py
pip install -e .
```

![image-20251026122304744](C:\Users\kewei\Documents\2025\04资料整理\03具身教程编写\ai-hardware-robotics\12-传感器配置\01joycon控制\assets\image-20251026122304744.png)

```
# sudo apt install dkms
# make install

---

cd ..
cd robosuite-joycon
pip install -r robosuite-joycon/requirements-extra.txt

# defualt for keyboard control
python robosuite/demos/demo_device_control.py 


sudo apt install libhidapi-dev
# Single joycon(R) controller
python robosuite/demos/demo_device_control_joycon_single.py

# Bimanual with two joycon controller
python robosuite/demos/demo_device_control_joycon_bimanual.py
````

键盘控制方案

### 机械臂末端执行器（夹爪）控制

#### 位置移动 (Position)

- 前后移动 (X轴):

- ↑ (上箭头): 沿 X 轴负方向移动 (向前)

- ↓ (下箭头): 沿 X 轴正方向移动 (向后)

- 左右移动 (Y轴):

- ← (左箭头): 沿 Y 轴负方向移动 (向左)

- → (右箭头): 沿 Y 轴正方向移动 (向右)

- 上下移动 (Z轴):

- . (句号): 沿 Z 轴负方向移动 (向下)

- ; (分号): 沿 Z 轴正方向移动 (向上)

#### 姿态旋转 (Rotation)

- 滚转 (Roll):

- e: 绕 X 轴正方向旋转

- r: 绕 X 轴负方向旋转

- 俯仰 (Pitch):

- y: 绕 Y 轴正方向旋转

- h: 绕 Y 轴负方向旋转

- 偏航 (Yaw):

- o: 绕 Z 轴负方向旋转

- p: 绕 Z 轴正方向旋转

### 夹爪控制 (Gripper)

- spacebar (空格键): 切换夹爪的开合状态。按一下闭合，再按一下张开。

### 仿真与环境控制

- Ctrl + q: 重置当前的仿真环境。

- s: (仅在多臂机器人环境中生效) 切换当前控制的手臂。

- =: (仅在多机器人环境中生效) 切换当前控制的机器人。

- b: (仅在移动底盘机器人中生效) 切换手臂/底盘控制模式。

当你启动脚本后，请确保仿真窗口是当前激活的窗口，这样键盘输入才会被程序接收。希望这份详细的说明能帮助你顺利操作！







```
sudo snap install bun-js
```









# 问题排查

1、如果缺少相关依赖



Python 的 `hid` 包（也叫 `hidapi`）无法在你的系统里找到它需要调用的核心库文件。

简单来说，这分两层：

1. **Python 包 (`hid`)**: 这是你在 `micromamba` 环境里安装的一个 Python 库。它本身不直接和硬件通信，而是作为一个“翻译官”或“遥控器”。
2. **系统库 (`libhidapi-\*.so`)**: 这是在你的操作系统层面安装的一个 C 语言库。它才是真正负责和 USB HID 设备（比如 Joy-Con）沟通的“引擎”。

报错信息 `Unable to load any of the following libraries: libhidapi-hidraw.so ...` 明确地告诉你，Python 这个“遥控器”找不到可以控制的“引擎”。

------



### **解决方案** 🛠️



你需要为你的操作系统安装这个缺失的 `hidapi` 引擎库。

**1. 安装 `hidapi` 开发库**

这个库的包名在不同 Linux 发行版上不一样。打开你的终端，执行以下命令：

- 对于 **Debian / Ubuntu** (以及 WSL 里的 Ubuntu):

  Bash

  ```
  sudo apt update
  sudo apt install libhidapi-dev
  ```

  *安装 `-dev` 版本通常会把运行库 (`libhidapi-hidraw0` 等) 作为依赖一起装上，并且包含了编译时可能需要的头文件，是最稳妥的选择。*

- 对于 **Arch Linux**:

  Bash

  ```
  sudo pacman -S hidapi
  ```

- 对于 **Fedora / CentOS**:

  Bash

  ```
  sudo dnf install hidapi-devel
  ```

**2. (重要) 配置 `udev` 规则**

安装好库之后，通常你还需要给 Joy-Con 设置一下设备权限，否则普通用户可能无法访问它，导致 Python 程序即使能找到库也连不上手柄。

- **创建 udev 规则文件**: 这条命令会为所有任天堂设备 (Vendor ID `057e`) 设置权限，让所有用户都能读写。

  Bash

  ```
  echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="057e", MODE="0666"' | sudo tee /etc/udev/rules.d/99-joycon.rules
  ```

- **重新加载 udev 规则**: 让规则立即生效。

  Bash

  ```
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  ```

**3. 重新连接你的 Joy-Con** 🎮

断开 Joy-Con 的蓝牙连接，然后重新配对连接一次，以确保新的 `udev` 规则应用到它上面。

**4. 再次运行你的 Python 程序**

完成以上步骤后，回到你的 `micromamba` 环境，再次运行你的 Python 脚本，这次应该就能成功导入 `hid` 模块并找到设备了。

Bash

```
python /home/kewei/17robo/robosuite-joycon/robosuite/demos/demo_device_control_joycon_bimanual.py
```



2. mujoco未安装

好的，安装 `mujoco` 非常简单。你只需要在你的 `py310-robosuite` conda 环境中使用 `pip` 来安装。

我可以直接为你执行安装命令。这个命令会使用 `pip` 将 `mujoco` 包安装到你当前激活的 Python 环境中。

[1 tool called]

好的，安装 `mujoco` 非常简单。你只需要在你的 `(py310-robosuite)` 环境中使用 `pip` 这个 Python 包管理器来安装。

我已经为你执行了安装命令 `pip install mujoco`。

从输出结果来看，`mujoco` 已经成功安装了。

现在 `mujoco` 已经安装好了，我们回到之前解决方案的第二步和第三步：找到 `mujoco.dll` 并把它复制到正确的位置。

我将执行一小段 Python 代码来帮你找到 `mujoco.dll` 的确切路径。

[1 tool called]

很好，我们已经成功找到了 `mujoco.dll` 文件！它的路径是：

`C:\Users\kewei\micromamba\envs\py311\Lib\site-packages\mujoco\mujoco.dll`

现在，我将把它复制到 `robosuite` 需要它的地方：

`C:\Users\kewei\17robo\robosuite-joycon\robosuite\utils\`

我将为你执行复制操作。

[1 tool called]

好了，`mujoco.dll` 文件已经复制到目标位置了。

现在，根本的依赖问题应该已经解决了。请你重新运行之前的命令，看看是否还会报错。

```powershell
python robosuite/demos/demo_device_control.py
```

如果还有其他问题，随时可以再向我提问！
