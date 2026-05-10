# README 08：SSH 命令执行与整段粘贴说明

这一章只解决一个很具体、但非常容易误导初学者的问题：为什么同样一组命令，整段粘贴过去会出问题，逐条执行却正常。这个现象在 Magicbox 的 ROS2 启动命令里尤其常见，因为很多启动流程都包含 `sudo su -`、`source` 和 `ros2 launch`，而这三类命令恰好都对当前 shell 环境非常敏感。

## 一、先说结论

如果一组命令里包含 `sudo su -`，不要把它和后续所有命令一起无脑整段粘贴。更稳妥的做法有两种。

第一种做法，是先单独执行：

```bash
sudo su -
```

确认提示符已经切换为 root 之后，再把后续命令整段粘贴进去。

第二种做法，是完全避免交互式切 shell，直接用一条 `sudo bash -lc '...'` 把整套命令包进同一个 root shell。对于需要反复复制和远程执行的教程命令，这通常是更推荐的写法。

## 二、为什么整段粘贴会失败

问题不在 Magicbox 本身，而在 shell 切换。

`sudo su -` 的作用，不是简单提权，而是启动一个新的 root 登录 shell。新的 shell 会重新加载自己的环境，并接管后续命令输入。问题在于，很多 Windows 终端、SSH 客户端或网页终端在整段粘贴时，会把后续几行命令很快连续发出去。这样一来，后面的命令并不一定都落在你以为的那个 shell 里。

最常见的结果有三种。

第一种，前半段命令在旧 shell 里执行，后半段命令在新 shell 里执行。  
第二种，`source /opt/tros/humble/setup.bash` 生效在一个 shell 里，但后面的 `ros2 launch` 实际跑在另一个 shell 里。  
第三种，命令本身没有写错，但环境没有完整留下来，所以表现得像“整段没反应”或者“`ros2` 找不到”。

这就是为什么你会看到一种很像玄学的现象：逐条执行没问题，整段粘贴反而失败。

## 三、哪些命令最容易受这个问题影响

在这套教程里，下面三类命令最容易受影响。

第一类是会切换 shell 的命令，例如：

```bash
sudo su -
sudo -i
```

第二类是只对当前 shell 生效的命令，例如：

```bash
source /opt/tros/humble/setup.bash
source /userdata/magicbox/app/ros_ws/install/local_setup.bash
export ROS_LOG_DIR=/userdata/magicbox/log
```

第三类是强依赖前两类结果的命令，例如：

```bash
ros2 launch gesture_interaction gesture_interaction.launch.py
ros2 launch hobot_stereonet stereonet_model_web_visual_v2.4_int16.launch.py
```

所以，只要一段命令里同时出现了“切 shell”“source 环境”“启动 ROS2”这三步，就不应该把它当成一个完全无条件可整段粘贴的命令块。

## 四、教程里推荐哪种执行方式

如果你是在手动调试，推荐采用“两段式”。

第一段，单独进入 root：

```bash
sudo su -
```

第二段，再执行真正的启动命令。例如手势交互可以写成：

```bash
cd /userdata/magicbox
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export LD_LIBRARY_PATH=/userdata/magicbox/app/ros_ws/install/qwen_llm/lib:$LD_LIBRARY_PATH
export HOME=/userdata/magicbox
export ROS_LOG_DIR=/userdata/magicbox/log
mkdir -p /userdata/magicbox/log
source /opt/tros/humble/setup.bash
source /userdata/magicbox/app/ros_ws/install/local_setup.bash
ros2 launch gesture_interaction gesture_interaction.launch.py
```

如果需要反复复制同一条命令，推荐采用“一段式单命令”。

```bash
sudo bash -lc '
cd /userdata/magicbox
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export LD_LIBRARY_PATH=/userdata/magicbox/app/ros_ws/install/qwen_llm/lib:$LD_LIBRARY_PATH
export HOME=/userdata/magicbox
export ROS_LOG_DIR=/userdata/magicbox/log
mkdir -p /userdata/magicbox/log
source /opt/tros/humble/setup.bash
source /userdata/magicbox/app/ros_ws/install/local_setup.bash
exec ros2 launch gesture_interaction gesture_interaction.launch.py
'
```

这条命令的优势是，所有操作都发生在同一个 root shell 里，不存在“前面 source 的环境跑到别的 shell 去了”的问题。

## 五、如果已经失败了，先看什么

不要先怀疑仓库或 launch 文件，先检查当前 shell 是否真的保留了需要的环境。

先检查 `ros2` 是否在当前 PATH 里：

```bash
command -v ros2
```

如果这里没有输出，说明当前 shell 并没有加载完整 ROS2 环境。

再检查关键日志目录是否可写：

```bash
ls -ld /userdata/magicbox/log /userdata/.roslog
```

如果目录权限不对，即使 `ros2 launch` 命令本身存在，也可能在启动前先因为创建日志目录失败而退出。

## 六、这条规则对哪些章节都适用

这条规则并不只适用于手势交互。凡是本教程里带有下面结构的命令，都应优先按本章执行。

```text
sudo / root shell
-> source ROS2 环境
-> source 工作区环境
-> ros2 launch
```

因此，第四章里的双目深度、手势交互，以及后续任何需要 root 环境的 ROS2 应用，都应遵循同样的执行原则。

## 七、本章结束后，读者应掌握什么

读完这一章后，读者应该明确三件事。

第一，整段粘贴失败而逐条执行成功，并不说明板子“玄学不稳定”，而往往只是 shell 切换与环境继承的问题。  
第二，只要命令里包含 `sudo su -`、`source` 和 `ros2 launch`，就要优先考虑它们是否运行在同一个 shell 里。  
第三，如果需要一条可重复、可复制的稳定命令，优先使用 `sudo bash -lc '...'` 这种单命令封装方式。
