Genie Sim 是 AgiBot 推出的仿真框架，为开发者提供高效的数据生成能力和评估基准，以加速具身智能的开发。Genie Sim 建立了一个全面的闭环流程，包括轨迹生成、模型训练、基准测试和部署验证。用户可以通过这个高效的仿真工具链快速验证算法性能并优化模型。无论是简单的抓取任务还是复杂的远程操作，Genie Sim 都能提供高度逼真的仿真环境和精确的评估指标，助力开发者高效完成机器人技术的开发和迭代。
Genie Sim Benchmark 作为 Genie Sim 的开源评估版本，致力于为具身 AI 模型提供精确的性能测试和优化支持。
可以最开始先下载资产

```Bash
sudo apt install git-lfsgit lfs install# When prompted for a password, use an access token with write permissions.# Generate one from your settings: https://huggingface.co/settings/tokensgit clone https://huggingface.co/datasets/agibot-world/GenieSimAssets
```

```Bash
# Configure the repositorycurl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \    && \    sudo apt-get update# Install the NVIDIA Container Toolkit packagessudo apt-get install -y nvidia-container-toolkitsudo systemctl restart docker# Configure the container runtimesudo nvidia-ctk runtime configure --runtime=dockersudo systemctl restart docker# Verify NVIDIA Container Toolkitdocker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

> [https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)

### [2.2 从 Huggingface 下载场景和资产](https://agibot-world.com/sim-evaluation/docs/#/?id=_22-download-scenes-amp-assets-from-huggingface)

请访问 [https://huggingface.co/datasets/agibot-world/GenieSimAssets](https://huggingface.co/datasets/agibot-world/GenieSimAssets) 并按照说明操作。

### [2.3 安装](https://agibot-world.com/sim-evaluation/docs/#/?id=_23-installation)

#### [2.3.1 Docker 容器 (推荐)](https://agibot-world.com/sim-evaluation/docs/#/?id=_231-docker-container-recommended)

1. 使用 Docker 容器进行开发
   - 按照 [Isaac Sim 文档](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html) 安装 Docker
2. 准备 Docker 镜像
   
   ```bash
   
   ```

```Plain
# 进入 genie_sim 根目录并从 Dockerfile 创建 Docker 镜像docker build -f ./scripts/dockerfile -t registry.agibot.com/genie-sim/open_source:latest .
```

如果遇到网络问题，我的方法是：

```bash
ip addr show docker0 | grep "inet\s" | awk '{print $2}' | cut -d/ -f1DOCKER_HOST_IP="172.17.0.1" docker build \  --add-host=host.docker.internal:"$DOCKER_HOST_IP" \  --build-arg http_proxy="http://host.docker.internal:7890" \  --build-arg https_proxy="http://host.docker.internal:7890" \  --build-arg no_proxy="localhost,127.0.0.1" \  -f ./scripts/dockerfile \  -t registry.agibot.com/genie-sim/open_source:latest .
```

- 运行 Docker 容器并启动服务器

```Bash
# 在主目录中启动一个新容器# 你需要将 ~/assets 更改为 GenieSimAssets 文件夹SIM_ASSETS=~/17robo/GenieSimAssets/ ./scripts/start_gui.sh./scripts/into.sh# 启动服务器omni_python server/source/genie.sim.lab/raise_standalone_sim.py --enable_curobo True  # 此演示的抓取轨迹由 Curobo 生成
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MzY4NDA5OGE2NjYyYjE5NzVmMzg0OTE3Y2YxNjlhNDNfWGdRcUQ4dXdIV3k0aVh1UFY2UnM5dmpZYTRnRWJYQnRfVG9rZW46WEFxS2JnbWdtb3A5Uk14VlRQZ2Mycm9Vbk5lXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

App ready之后再执行下一句

然后我们就看到，如果超市演示执行完成，就会这边的仿真器也退出。

```Bash
# start container in main directory./scripts/into.sh# start client in containeromni_python benchmark/task_benchmark.py --task_name=curobo_restock_supermarket_items --env_class=DemoEnvomni_python benchmark/task_benchmark.py --task_name=iros_open_drawer_and_store_items --env_class=DemoEnv  （暂时有报错）omni_python benchmark/task_benchmark.py --task_name=genie_task_home_microwave_food --env_class=DemoEnv （这个也是用不了的，只有输出step）geniesim2.1和2.0一样只给了一个curobo跑任务的示例，开源部分只配置了上货任务，其他iros任务需要模型推理或者遥操作
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MzAwYTRmNWY2OGZmZWExZGQ1ZmIyNTczMzMyNzM5ZTlfUWxFalpScE8zNzFWVUJGN2JQb1JINkJ3YjhEeXhhNkNfVG9rZW46U0tJRWJtMU93b1BCWER4SDhQbGNpckp1bkdoXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

先回出现这个绿色的info

然后等大概1min

如果遇到了gRPC相关的报错，请参考issue修改即可

https://github.com/AgibotTech/genie_sim/issues/11

注意命令行不能设置任何代理！同时sudo ufw allow 50051

```Bash
make sure your server is running (launched by omni_python server/source/genie.sim.lab/raise_standalone_sim.py --enable_curobo True in same container)make sure your port 50051 is not be used. You must kill other process on 50051 by sudo lsof -i :50051 and sudo kill -9 .
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NTIxZGI3ZjllNThiMzUwODg4NmFkMzIxZTE2ZWMyNjRfWWZWaGZEd0tIWm9PM1NXSGtPMFJqZklFMVdIT3hDVnRfVG9rZW46UndCWGJkWUdFb3JBeFB4RkdFYWNXa1BRbmRmXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NjM0YTRiNjlmYjc0MTcyOWNjZTQ4ZjM5NTVhMGU4YjVfaUFwRWFtOElyVHcwaDRCY2FvRmlRYXFrWFp1WGVicXpfVG9rZW46TUpCcmJMYzA4b2FqRFV4M1dqcWNTUVZNbklkXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

我这里遇到了卡在这里的问题

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MTg1YmE4M2YzYzFmNDVkM2Y5NDczNjE1N2YxYTg4ZDJfSTdrYUcxdjNTSFRkQ3ZPSnAybks4VXdZWjRLMHFjRzFfVG9rZW46WFNsd2JFaDBEb1plNWt4d3BHWGNFempabjdjXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

从远程pull一下最新代码。

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NmM3ODdlZDIxZWMyMWEwZjdiZDQ0Y2YyOTA1YzNmNTRfTXFaalo0cWVGT051REtXOXdwRGxhelZjcEtNVUExQVRfVG9rZW46RUdZeGJ2YVpSbzY1Um14bXJXeGNzbVp1bkdlXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

就不会卡住。

同时，如果有对应大文件更改，可以到assets下面：

git lfs pull *# 确保所有LFS文件是最新的*

https://github.com/AgibotTech/genie_sim/issues/29

#### [2.3.2 主机](https://agibot-world.com/sim-evaluation/docs/#/?id=_232-host-machine)

1. 我们建议开发者使用我们统一的 Docker 容器环境。

2. 如果希望使用自己的环境，请参考我们提供的 `dockerfile` 并安装我们列出的依赖项。

#### [2.3.3 开发者指南](https://agibot-world.com/sim-evaluation/docs/#/?id=_233-developer-guide)

#### [2.3.4 启用 pre-commit 钩子 (可选)](https://agibot-world.com/sim-evaluation/docs/#/?id=_234-enable-pre-commit-hooks-optional)

1. 安装并设置 `pre-commit` 以启用自动文件格式化程序，适用于 Python / JSON / YAML 等。

```Bash
# 将 pre-commit 安装到你的 Python 环境sudo apt install python3-pippip3 install pre-commit# 在仓库中启用预定义的 pre-commit 钩子pre-commit install
```

2. 对所有跟踪的文件触文件格式化程序

```Bash
pre-commit run --all-files
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MGRhOTM4N2Y3YTI2YWFmN2I2ZjE4OGIyNzAzOWEwNzRfS1FLalM5dllzS3hiV1RnOVFyUm5EOTNkMFdSbDY4UjNfVG9rZW46RUhpNWJ0NlRHb3VFdXF4bWh2V2NNUlhwbkVnXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

### [2.4 基准测试任务](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_24-benchmark-tasks)#### [2.4.1 运行基准测试](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_241-run-benchmark)1. 运行 docker 容器

```Plain
# 在主目录中启动一个新容器# 需要将 ~/assets 更改为 GenieSimAssets 文件夹SIM_ASSETS=~/17robot/GenieSimAssets ./scripts/start_gui.sh
```

2. 运行基准测试

在 docker 容器外的 `genie_sim` 根目录下执行以下命令

Auto run是挺好用的。不过需要infer参数

```Plain
./scripts/autorun.sh genie_task_home_pour_water infer
```

https://github.com/AgibotTech/genie_sim/issues/34

支持以下任务名称

**任务名称**

genie_task_cafe_espresso

genie_task_cafe_toast

genie_task_home_clean_desktop

genie_task_home_collect_toy

genie_task_home_microwave_food

genie_task_home_open_drawer

genie_task_home_pass_water

genie_task_home_pour_water

genie_task_home_wipe_dirt

genie_task_supermarket_cashier_packing

genie_task_supermarket_stock_shelf

genie_task_supermarket_pack_fruit

---

#### [2.4.2 基准评估框架](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_242-benchmark-evaluation-framework)

配置

使用 ADER (Action Domain Evaluation Rule) 进行评估配置

**示例**

JSON

```Plain
{  "Acts": [    {      "ActionList": [        {          "ActionSetWaitAny": [            {              "Follow": "beverage_bottle_002|[0.2,0.2,0.2]|right"            },            {              "Timeout": 120            },            {              "Onfloor": "beverage_bottle_002|0.0"            }          ]        },        {          "ActionSetWaitAny": [            {              "PickUpOnGripper": "beverage_bottle_002|right"            },            {              "Timeout": 120            },            {              "Onfloor": "beverage_bottle_002|0.0"            }          ]        },        {          "ActionSetWaitAny": [            {              "Follow": "handbag_000|[0.4,0.4,0.4]|right"            },            {              "Timeout": 120            }          ]        },        {          "ActionSetWaitAny": [            {              "Inside": "beverage_bottle_002|handbag_000|1"            },            {              "StepOut": 1000            }          ]        }      ]    }  ],  "Init": [],  "Objects": [    {      "bottle": [        "beverage_bottle_002"      ],      "handbag": [        "handbag_000"      ]    }  ],  "Problem": "pack_in_the_supermarket"}
```

**当前评估能力**

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|                   |                                                   |                  |                                 |
| ----------------- | ------------------------------------------------- | ---------------- | ------------------------------- |
| 动作                | 描述                                                | 基类               | 语法                              |
| 通用 (COMMON)       |                                                   |                  |                                 |
| ActionList        | 队列动作：内部动作按顺序执行。                                   | ActionBase       | "ActionList":[]                 |
| ActionSetWaitAny  | 条件队列动作：当任何一个内部动作完成时，该动作完成。                        | ActionBase       | "ActionSetWaitAny":[]           |
| ActionWaitForTime | 时间等待动作：类似于 sleep，但不会阻塞线程。                         | ActionBase       | "ActionWaitForTime": 3.0        |
| TimeOut           | 超时验证动作：检查是否发生超时。                                  | ActionCancelBase | "Timeout": 60                   |
| StepOut           | 步数限制验证动作：检查是否已达到步数限制。                             | ActionCancelBase | "StepOut": 100                  |
| ActionSetWaitAll  | 所有条件都满足时退出。                                       | ActionBase       | "ActionSetWaitAll":[]           |
| 自定义 (CUSTOM)      |                                                   |                  |                                 |
| Ontop             | 一个物体在另一个物体上方。                                     | EvaluateAction   | "Ontop": "active_obj            |
| Inside            | 一个物体在另一个物体内部。                                     | EvaluateAction   | "Inside": "active_obj           |
| PushPull          | 检查关节体对象的滑动关节是否在阈值 [min, max] 内——用于确定抽屉状物体是打开还是关闭。 | EvaluateAction   | "PushPull": "obj_id             |
| Follow            | 检查左/右夹爪是否正在跟随特定物体，在由边界框定义的范围 [x, y, z] 内。         | EvaluateAction   | "Follow": "obj_id               |
| PickUpOnGripper   | 夹爪抓住一个物体。                                         | EvaluateAction   | "PickUpOnRightGripper": "object |
| OnShelf           | 物体在特定区域内。                                         | EvaluateAction   |                                 |
| Onfloor           | 检查指定物体是否掉落到参考高度 ref_z 以下；如果是，则退出。                 | ActionCancelBase | `"Inside": "obj_id              |
| Cover             | 物体A覆盖物体B。                                         | EvaluateAction   | "Cover": "active_obj            |

**评估输出数据结构**

JSON

```Plain
//输出[  {    "task_type": "benchmark",    "model_path": "",    "task_uid": "13513cf3-2d88-421e-b3e5-dc0998a60970",    "task_name": "genie_task_supermarket",    "stage": "",    "result": {      "code": -1,      "step": 0,      "msg": "",      "progress": [],      "scores":[]    },    "start_time": "2025-06-05 15:04:31",    "end_time": "2025-06-05 15:05:40"  }]
```

**错误码**

Python

```Plain
from enum import Enumclass ErrorCode(Enum):    INIT_VALUE = -1    SUCCESS = 0    ABNORMAL_INTERRUPTION = 1    OUT_OF_MAX_STEP = 2    UNKNOWN_ERROR = 500
```

---

### [2.5 AgiBot World 挑战赛操作任务](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_25-agibot-world-challenge-manipulation-tasks)

#### [2.5.1 运行基线模型推理](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_251-run-baseline-model-inference)

1. 从以下地址下载 Agibot World 仓库和基线模型

2. a. [GitHub - OpenDriveLab/AgiBot-World at manipulation-challenge](https://github.com/OpenDriveLab/AgiBot-World/tree/manipulation-challenge)

下载后，只要docker不更新build，之前的agibot-world还是在docker的main下的

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=Y2M2YTkzMDM3ZmYzNTJiOTYyNTc1YjQ4Njc1MDIyMzBfN1RIc1ppWENYR0M2SFpoMnRRRzZtTGJTS0xZcWg1WFJfVG9rZW46SmRDaGJWckJTb1JudGh4ZnoxcmNRb1FxbnZkXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

```Plain
# 初始化 Agibot World 仓库以运行基线模型git clone -b git submodule update --init --recursive
```

后面每次可以拉取一下更新：

```TypeScript
root@ubuntu22:~/workspace/main/AgiBot-World# lsexperiments       InternVL             __pycache__       scriptsgenie_sim_ros.py  latent_action_model  README.mdhubconf.py        prismatic            requirements.txtroot@ubuntu22:~/workspace/main/AgiBot-World# git pullfatal: detected dubious ownership in repository at '/root/workspace/main/AgiBot-World'To add an exception for this directory, call:        git config --global --add safe.directory /root/workspace/main/AgiBot-Worldroot@ubuntu22:~/workspace/main/AgiBot-World# 需要git config --global --add safe.directory /root/workspace/main/AgiBot-World然后git pullgit submodule update --init --recursive
```

FileNotFoundError: [Errno 2] No such file or directory: 'checkpoints/finetuned/action_decoder.pt'

There was an error running python

这个是因为需要添加基线模型

3. 将所有基线模型文件和代码移动到 Agibot-World 目录下

```Bash
cp -r UniVLA/latent_action_model/ ./latent_action_model/cp -r UniVLA/scripts/ ./scripts/cp -r UniVLA/prismatic/ ./prismatic/cp -r UniVLA/experiments/ ./experiments/mkdir -p checkpoints/finetunedcd checkpoints/finetunedgit lfs clone https://huggingface.co/qwbu/univla-iros-manipulation-challenge-baselinemv univla-iros-manipulation-challenge-baseline/* ./
```

为了保持最新

```Bash
git clone -b manipulation-challenge https://github.com/OpenDriveLab/AgiBot-World.git AgiBot-World-manipulation-challengecp -r AgiBot-World-manipulation-challenge/UniVLA/* AgiBot-World/
```

```Plain
main├── AgiBot-World│   ├── InternVL│   ├── experiments/robot│   ├── latent_action_model│   ├── prismatic│   ├── robot│   ├── scripts│   │   └── infer.py│   │   └── ...│   │   └── ...│   ├── checkpoints│   │   └── finetuned│   │       └── readme.txt│   ├── genie_sim_ros.py│   ├── hubconf.py│   └── requirements.txt
```

有个需要修改的地方infer.py的第五行：

后续有空我提个PR，也欢迎有空的小伙伴去提(目前该问题已修复，不用管这个了)

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=ZGZiZmRhOWY4MzRkNGI2MDk1OTcxMzQ0YjFlMjI3NGJfc01FTEhJZ1NWVzd6Ym4xWUNOTGI5ZU5RdzdqWDhBcGRfVG9rZW46Sm5USWJUZjd0b0JEUTZ4RnJ2eGNGS21WbnhmXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

4. 运行 docker 容器

```Plain
# 在主目录中启动一个新容器# 需要将 ~/assets 更改为本地 assets 文件夹SIM_ASSETS=~/17robo/GenieSimAssets ./scripts/start_gui.sh
```

4. 运行基线模型推理

在 docker 容器外的 `genie_sim` 根目录下执行以下命令

```Plain
./scripts/autorun.sh iros_open_drawer_and_store_items infer./scripts/autorun.sh iros_clear_the_countertop_waste infer
```

支持以下任务名称

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|                                        |
| -------------------------------------- |
| 任务名称                                   |
| iros_clear_the_countertop_waste        |
| iros_open_drawer_and_store_items       |
| iros_heat_the_food_in_the_microwave    |
| iros_pack_moving_objects_from_conveyor |
| iros_pickup_items_from_the_freezer     |
| iros_restock_supermarket_items         |
| iros_pack_in_the_supermarket           |
| iros_make_a_sandwich                   |
| iros_clear_table_in_the_restaurant     |
| iros_stamp_the_seal                    |

---

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=ODQwNTAzY2FkMzJiMGEzYjNiYzljMjE1MWFhZWE0NjZfc20yaTVlcXA3RTU5cFp4c2Z5M0UzcEtVQzRwUkxhVzlfVG9rZW46QmRjT2IzcGpib05wUlh4OHRURmN6Tm1jbmJIXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

成功咯，24G显卡够用

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MWY4NDZjNzUxNTUwZWM2YWZjOTRhNDY5ZTQ5ODI0MDdfNnJLVmlnOWZsZmdOdUVvVmI2c1ZHb2NUZTE5RWpXTllfVG9rZW46VWNmeWJ5RW9Lb3Q0VFR4RDQxS2M4M3h0blVmXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=OTJmMmVkODg4ZDdmZTg3ODBiODVmM2JiYzQxZDNkZjhfcVZCSUFpTU55ajBJT2h5VGc1Y2NlZ0RXME1wQ2ZvakhfVG9rZW46WXdMWWJZOVBSb1dEaXh4eTVlTGNxN21XbkplXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

打开抽屉并夹取物体，不过过程还是有很多问题的哈哈哈，最后把魔方搞到地上了

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NzQwZmM3ZGIxOTMxMDE3MmNlZmIwODY1NGMxZDY2YjhfeGlGbVFXMXYwRzQ3RXpSclJON08yb0RsT3dkYzk3M0dfVG9rZW46VG5IU2JSWUNYb0sxZjB4eWhVeWNXSU14blBkXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

#### [2.5.2 集成自己的策略](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_252-integrate-your-own-policy)

1. 根据以下说明构建自己的代码

2. a. 使用以下路径的模板开始模型集成。不要修改 `infer` 函数的结构。

```Plain
main├── model│   ├──demo_infer.py
```

b. 在自定义时，请确保 ROS 节点严格遵守指定的话题

*模型推理与仿真环境之间的通信是标准化的，并基于 ROS2 实现。这些是为任务指定的专用话题。

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|                            |      |      |                 |                   |
| -------------------------- | ---- | ---- | --------------- | ----------------- |
| 话题名称                       | 发布者  | 订阅者  | 消息类型            | 内容                |
| /joint_command             | 模型   | 仿真环境 | JointState      | 模型推理输出的关节命令       |
| /joint_states              | 仿真环境 | 模型   | JointState      | 来自仿真的当前机器人关节状态    |
| /sim/head_img              | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前头部 RGB 图像  |
| /sim/left_wrist_img        | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前左手腕 RGB 图像 |
| /sim/right_wrist_img       | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前右手腕 RGB 图像 |
| /sim/head_depth_img        | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前头部深度图像     |
| /sim/left_wrist_depth_img  | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前左手腕深度图像    |
| /sim/right_wrist_depth_img | 仿真环境 | 模型   | CompressedImage | 来自仿真的当前右手腕深度图像    |

c. 自定义后，请确认文件组织结构与指定布局匹配，并确保包含 `infer.py` 和 `genie_sim_ros.py`。

```Plain
main├── AgiBot-World│   ├── scripts│   │   └── infer.py│   │   └── ...│   │   └── ...│   ├──genie_sim_ros.py│   ├──...│   └──...
```

2. 运行 docker 容器

Bash

```Plain
# 需要将 ~/assets 更改为 GenieSimAssets 文件夹SIM_ASSETS=~/assets ./scripts/start_gui.sh
```

3. 运行模型推理

4. 在 docker 容器外的 genie_sim 根目录下执行以下命令

```Plain
./scripts/autorun.sh {TASK_NAME} infer
```

4. 模型推理依赖

常用的 Python 库已在 Genie Sim Benchmark 仓库的 `requirements.txt` 文件中列出，并预装在我们的操作测试服务器的 docker 镜像中。如果需要额外的 Python 库来运行策略，可以在测试服务器上随模型文件一起上传一个包含额外库的 `requirements.txt` 文件。

---

#### [2.5.3 Agibot World 挑战赛评估框架](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_253-agibot-world-challenge-evaluation-framework)

请参考 2.4.2 基准评估框架

---

### [2.6 遥操作](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_26-teleoperation)

#### [2.6.1 PICO](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_261-pico)

支持使用手柄控制机器人腰部、头部、左/右末端执行器和基座的移动。

**用户指南**

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|     |                           |
| --- | ------------------------- |
| 编号  | 功能 (左 / 右)                |
| ①   | 摇杆: 移动机器人基座<br>按下: 重置基座姿态 |
| ②   | 重置左臂                      |
| ③   | 启用姿态跟踪                    |
| ④   | 重置右臂                      |
| ⑤   | 重置身体和头部                   |
| ⑥   | 控制左夹爪                     |

**Pico** **设置**

1. 连接到与计算机相同的**局域网**

2. 在资源库中启动 **AIDEA Vision App**

3. 选择**无线连接**并输入计算机的 **IP** 地址

**启动设置**

1. 启动服务器

Bash

```Plain
# 在容器内运行此命令omni_python server/source/genie.sim.lab/raise_standalone_sim.py
```

2. 在容器中启动 PICO 控制

Bash

```Plain
# 在容器内运行此命令omni_python teleop/teleop.py --task_name genie_task_home_microwave_food --mode pico --host_ip x.x.x.x
```

---

#### [2.6.2 键盘](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_262-keyboard)

支持键盘控制机器人腰部、头部、左/右末端执行器和基座的移动。

用户指南

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|        |         |          |        |
| ------ | ------- | -------- | ------ |
| 按键     | 功能      | 按键       | 功能     |
| w      | 末端执行器向前 | i        | 翻滚 +   |
| s      | 末端执行器向后 | k        | 翻滚 -   |
| a      | 末端执行器向左 | j        | 俯仰 +   |
| d      | 末端执行器向右 | l        | 俯仰 -   |
| q      | 末端执行器向上 | u        | 偏航 +   |
| e      | 末端执行器向下 | o        | 偏航 -   |
| ↑      | 基座向前    | shift+↑  | 头部俯仰 + |
| ↓      | 基座向后    | shift+↓  | 头部俯仰 - |
| ←      | 基座左转    | shift+←  | 头部偏航 + |
| →      | 基座右转    | shift+→  | 头部偏航 - |
| ctrl+↑ | 腰部向上    | ctrl+tab | 切换手臂   |
| ctrl+↓ | 腰部向下    | r        | 重置     |
| ctrl+← | 腰部俯仰 -  | c        | 关闭夹爪   |
| ctrl+→ | 腰部俯仰 +  | ctrl+c   | 打开夹爪   |

**启动设置**

1. 启动服务器

Bash

```Plain
SIM_ASSETS=~/17robo/GenieSimAssets/ ./scripts/start_gui.sh./scripts/into.sh# 在容器内运行此命令omni_python server/source/genie.sim.lab/raise_standalone_sim.py
```

2. 在容器中启动键盘控制

Bash

```Plain
# 在容器内运行此命令omni_python teleop/teleop.py --task_name genie_task_home_microwave_food --mode "keyboard"
```

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=YWJhOTlmYmY4NjRmMDgyOGJjNzZhNzc4N2JlMTQ0M2RfYzBLMlZWVWpuUHhNS3BoUGlsODMyQkw1cTNYUk4ySWZfVG9rZW46S3dnZmJqb3BUb3czMXF4MVFDZWNKekJEbjNiXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

腰部的还是慎用，感觉没弄好，整体来说末端执行器控制还是很棒的

---

### [2.7 记录 & 回放](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_27-record-amp-replay)

这里再备注一下任务：

genie_task_cafe_espresso

genie_task_cafe_toast

genie_task_home_clean_desktop

genie_task_home_collect_toy

genie_task_home_microwave_food

genie_task_home_open_drawer

genie_task_home_pass_water

genie_task_home_pour_water

genie_task_home_wipe_dirt

genie_task_supermarket_cashier_packing

genie_task_supermarket_stock_shelf

genie_task_supermarket_pack_fruit

为提高效率，首先记录轨迹，然后执行回放来录制视频。

将所有场景信息（包括机器人关节位置、物体姿态、相机姿态等）记录在 state.json 文件中。

- 启动服务器

Bash

```Plain
# 在容器内运行此命令omni_python server/source/genie.sim.lab/raise_standalone_sim.py
```

- 启动客户端

Bash

```Plain
# 在容器内运行此命令omni_python teleop/teleop.py --task_name genie_task_home_pour_water --mode keyboard  --record
```

场景信息记录在 `./output/recording_data/{TASK_NAME}/state.json`

这里生成的 /root/workspace/main/output/recording_data/genie_task_home_pour_water/state.json

#### [2.7.1 回放](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_271-replay)

回放轨迹并录制视频。

- 启动服务器

Bash

```Plain
# 在容器内运行此命令omni_python server/source/genie.sim.lab/raise_standalone_sim.py --disable_physics --record_img --record_video
```

- 启动客户端

Bash

```Plain
# 例如：TASK_NAME=genie_task_home_pour_water# 在容器内运行此命令omni_python teleop/replay_state.py --task_file teleop/tasks/${TASK_NAME}.json --state_file output/recording_data/${TASK_NAME}/state.json --record
```

图像和视频记录在 `./output/recording_data/{TASK_NAME}/{IDX}/`

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NzczY2ExNGFhNzk1MDQwNTNjZjgzMDljYzdlMjc2ZTZfeGg0aDhLUmdqUlduM3ZkNDdKOUZsMVZzNjdiOUR4WTVfVG9rZW46QldEMWJtalpRb1VuWEh4UzZyMGNHb3RGbmlmXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MDM2YmY4OTI0MTkxNWNkY2MxNDFjY2FlZmM2MDVmNGZfbGJtNXJ0N0EzUHRLZjNQWndPNEpUd01sUG1ua0NqdFFfVG9rZW46S2ExaWJnYTE3bzhrY0t4TDdWcmNlalJpbjliXzE3NTE4NzYzOTQ6MTc1MTg3OTk5NF9WNA)

---

## [3. 用例](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_3-use-cases)

### [3.1 如何用一行代码运行仿真](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_31-how-to-run-simulation-with-just-one-line-of-code)

1. 运行 docker 容器

Bash

```Plain
SIM_ASSETS=~/17robo/GenieSimAssets ./scripts/start_gui.sh
```

2. 在 docker 容器外的 `genie_sim` 根目录下执行 shell 脚本

3. a. 运行任务布局

Bash

```Plain
./scripts/autorun.sh {TASK_NAME}
```

b. 运行 PICO 遥操作

Bash

```Plain
./scripts/autorun.sh {TASK_NAME} pico {HOST_IP}
```

c. 运行键盘遥操作

Bash

```Plain
./scripts/autorun.sh {TASK_NAME} keyboard
```

d. 运行场景回放

Bash

```Plain
./scripts/autorun.sh {TASK_NAME} replay {STATE_FILE_PATH}
```

e. 运行模型推理

Bash

```Plain
./scripts/autorun.sh {TASK_NAME} infer
```

f. 运行清理

Bash

```Plain
./scripts/autorun.sh clean
```

3. 在终端中按 `q` 或 `Q` 键以正常停止任务。`autorun` 脚本默认启用 ros topic 记录。如果不需要，请在 `autorun` 脚本中删除相关代码，并确保定期清理输出文件夹。（存储哪些信息呢？保存到哪里呢）

---

### [3.2 如何设置基准任务文件](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_32-how-to-set-up-a-benchmark-task-file)

每个基准任务文件都包含以下 6 个关键元素：

1. **task** 包含一个唯一的任务名称

2. **objects** 包含多种任务对象：
   
   1. `extra_objects`: 非交互式对象
   
   2. `fix_objects`: 具有固定初始姿态的交互式对象
   
   3. `task_related_objects`: 具有随机初始姿态的交互式对象

3. **recording_setting** 指定要录制的相机视角

4. **robot** 包括机器人 ID、机器人配置文件和机器人基座初始姿态

5. **scene** 指定一组场景信息：
   
   1. `scene_id`: 场景的唯一名称
   
   2. `function_space_objects`: 随机生成 `task_related_objects` 的立方体区域
   
   3. `scene_info_dir`: 场景资产的路径
   
   4. `scene_usd`: 场景 usd 文件的路径

6. **stages** 包含为规划任务设计的几个子阶段
   
   1. `action`: 定义动作名称
   
   2. `active`: 定义主动对象，如夹爪
   
   3. `passive`: 定义被动对象，如瓶子

---

### [3.3 如何创建一个带有具身 AI 模型的完整基准任务](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_33-how-to-create-a-complete-benchmark-task-with-embodied-ai-model)

1. 首先，组装任务模板，如 "genie_task_supermarket.json"。此配置文件包含机器人、场景、对象和阶段等。

```Plain
benchmark/bddl/eval_tasks/your_task.json
```

请正确填写资产文件路径。程序将在用户配置的环境变量 `SIM_ASSETS` 中查找资产。

2. 场景泛化：将任务与场景进行映射

```Plain
文件路径: benchmark/bddl/task_to_preselected_scenes.json
```

JSON

```Plain
{  "genie_task_supermarket": [    "scenes/genie/supermarket_02/Collected_emptyScene_01/emptyScene_01.usd"  ]}
```

3. 编写评估标准代码，例如

```Plain
文件路径: benchmark/bddl/task_definitions/genie_task_supermarket/problem0.bddl
```

Lisp

```Plain
(define (problem restock_shelves)    (:domain isaac)    (:objects        benchmark_beverage_bottle_013 - bottle.n.01    )    (:init        (onfloor benchmark_beverage_bottle_013 floor.n.01_2)    )    (:goal        (onshelf ?benchmark_beverage_bottle_013)    ))
```

现在，基准配置步骤已完成。

4. 在 "yourpolicy.py" 中访问具身智能模型。（请参考 demopolicy.py）

Python

```Plain
class YourPolicy(BasePolicy):def __init__(self) -> None:super().__init__()        """初始化配置并加载模型。"""passdef reset(self):"""重置。"""passdef act(self, observations, **kwargs) -> np.ndarray:"""根据观察结果采取行动。        参数: observations 包含机器人图像 (Head_Camera_01/Right_Camera_01/Left_Camera_01) 和当前关节信息        返回: 机器人目标关节        """pass
```

5. 最后，运行客户端并评估自己的 AI 模型

Bash

```Plain
python3 benchmark/task_benchmark.py --task_name {task name} --policy_class {policy name} --env_class OmniEnv
```

---

### [3.4 操作任务资产参数的最佳实践](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_34-best-practice-of-asset-parameters-for-manipulation-task)

#### [3.4.1 如何在 IsaacSim 中调试碰撞体](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_341-how-to-debug-collider-in-isaacsim)

> 按照说明启用碰撞体调试模式

---

#### [3.4.2 不良示例](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_342-bad-examples)

- 复杂的网格会导致碰撞计算错误，越简单越好

- 在小区域内有太多的三角网格通常会导致网格碰撞

convexHull 和 convexDecompisition

---

#### [3.4.3 良好示例](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_343-good-examples)

良好意味着易于抓取且网格碰撞少

- 良好的碰撞网格通常看起来简单整洁

- 确保抓取的关键区域恰到好处（例如罐头、瓶子、瓶盖）

convexDecompisition 网格

convexDecompisition 碰撞体

convexHull

---

## [4. API 参考](https://agibot-world.com/sim-evaluation/docs/#/v2?id=_4-api-reference)

<style> td {white-space:nowrap;border:0.5pt solid #dee0e3;font-size:10pt;font-style:normal;font-weight:normal;vertical-align:middle;word-break:normal;word-wrap:normal;}</style>

|                                 |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| ------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 函数                              | 描述                    | 输入                                                                                                                                                                                                                                                                                                                                            | 返回                                                                                                                                    |
| 初始化                             |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.InitRobot()              | 初始化机器人和场景             | robot_cfg: 配置文件路径 (位于 'robot_cfg' 文件夹)<br>scene_usd: usd 路径<br>init_position([x,y,z])<br>init_rotation([x,y,z])                                                                                                                                                                                                                               |                                                                                                                                       |
| 控制器                             |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.moveto()                 | 机器人的末端执行器移动到目标姿态      | target_position([x,y,z])<br>target_quaternion([w,x,y,z])<br>is_backend:<br>1. True: ee 直线移动<br>2. False: ee 带避障移动<br>ee_interpolation:<br>1. True: ruckig 插值<br>2. False: 目标点插值<br>distance_frame: 插值密度                                                                                                                                       |                                                                                                                                       |
| client.set_joint_positions()    | 机器人的关节移动到目标关节状态       | target_joint_position: [N], rad/s<br>joint_indices: [N], 索引<br>is_trajectory:<br>1. True: 关节应用动作<br>2. False: 设置关节状态                                                                                                                                                                                                                          |                                                                                                                                       |
| client.set_gripper_state()      | 设置夹爪状态（打开或关闭）         | gripper_command: "open" 或 "close"<br>is_right(bool)<br>opened_width(float)                                                                                                                                                                                                                                                                    |                                                                                                                                       |
| client.SetTrajectoryList()      | 设置 ee 姿态列表轨迹          | trajectory_list(list): [[position(xyz), rotation(wxyz)]]                                                                                                                                                                                                                                                                                      |                                                                                                                                       |
| 对象                              |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.add_object()             | 向场景中添加一个 USD 对象       | usd_path(str): 基于 SIM_ASSETS 的资产相对路径<br>prim_path(str): 场景中对象的 prim 路径，例如: "/World/Object/obj_01"<br>lable_name(str): 应用于语义分割的对象标签名称<br>target_position([x,y,z])<br>target_quaternion([w,x,y,z])<br>target_scale([x,y,z])<br>mass:[kg]<br>**add_particle(bool):**添加额外的流体粒子，例如：水壶中的水<br>particle_size:([x,y,z])<br>particle_position:([x,y,z]) |                                                                                                                                       |
| client.SetMaterial()            | 设置 XFormPrim 的材质      | material_info(list):<br>例如:<br>material_info = [<br>{"object_prim" : "/obj1"<br>"material_name": "wood"<br>"material_path: "materials/wood"}]                                                                                                                                                                                                 |                                                                                                                                       |
| client.SetLight()               | 设置舞台的灯光信息             | light_info(list):<br>例如:<br>light_info = [{<br>"light_type": "Distant",<br>"light_prim": "/World/DistantLight",<br>"light_temperature": 2000,<br>"light_intensity": 1000,<br>"rotation": [1,0.5,0.5,0.5],<br>"texture": ""}]                                                                                                                  |                                                                                                                                       |
| client.SetObjectPose()          | 在单个物理步骤中设置刚体和关节体对象的姿态 | object_info(list):<br>例如:<br>object_info = [{<br>"prim_path": "/World/obj1",<br>"position": [x,y,z],<br>"rotation": [w,x,y,z]}]<br>object_joint_info(list): 关节体对象关节信息                                                                                                                                                                         |                                                                                                                                       |
| 传感器                             |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.AddCamera()              | 向舞台添加一个摄像头            | camera_prim(str): 相机的 prim 路径<br>camera_position(xyz): 相机的位置<br>camera_rotation(wxyz): 相机的旋转<br>Width, Height, focus_length, horizontal_aperture<br>vertical_aperture 相机的内参:<br>fx = Width * focus_length / horizontal_aperture<br>fy = Height * focus_length / vertical_aperture<br>is_local(bool): 本地姿态或世界姿态                                |                                                                                                                                       |
| client.capture_frame()          | 捕获 rgb/深度 帧           | camera_prim(str): 相机的 prim 路径                                                                                                                                                                                                                                                                                                                 | response.color_image.data<br>response.depth_image.data                                                                                |
| client.capture_semantic_frame() | 捕获语义帧                 | camera_prim_path(str): 相机的 prim 路径                                                                                                                                                                                                                                                                                                            | response.semantic_mask.data                                                                                                           |
| 观察                              |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.get_observation()        | 在单帧中获取相机/关节/tf 数据     | data_keys(dict):<br>例如:<br>data_keys = { 'camera': {<br>'camera_prim_list': ["/camera"],<br>'render_depth': True,<br>'render_semantic': True<br>},<br>'pose': ["/object1" ],<br>'joint_position': True,<br>'gripper': True}                                                                                                                   | observation = {<br>"camera": camera_datas,<br>"joint": joint_datas,<br>"pose": object_datas,<br>"gripper": gripper_datas }            |
| client.GetIKStatus()            | 逆运动学计算                | target_poses(list): [{"position":xyz, "rotation":wxyz}]<br>is_right(bool): 双臂的手臂类型<br>ObsAvoid(bool): 计算带避障的 IK                                                                                                                                                                                                                               | "status"([bool]): 逆运动学成功<br>"Jacobian"([double]): ik 关节状态的雅可比分数<br>"joint_positions"([list]):ik 关节位置<br>"joint_names"([list]):ik 关节名称 |
| client.GetEEPose()              | 获取末端执行器的世界姿态          | is_right(bool): 选择手臂类型                                                                                                                                                                                                                                                                                                                        | state.ee_pose.position<br>state.ee_pose.rpy                                                                                           |
| client.get_object_pose()        | 获取对象的世界姿态             | prim_path(str): 对象 prim 路径                                                                                                                                                                                                                                                                                                                    | object_pose.position<br>object_pose.rpy                                                                                               |
| client.get_joint_positions()    | 获取机器人当前的关节位置          |                                                                                                                                                                                                                                                                                                                                               | result.states.name<br>result.states.position                                                                                          |
| Curobo 特色功能                     |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.AttachObj()              | 附着被动物体                | prim_paths[list[str]]: 附着对象的 prim 路径                                                                                                                                                                                                                                                                                                          |                                                                                                                                       |
| client.DetachObj()              | 分离所有物体                |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| 录制设置                            |                       |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.start_recording()        | 录制片段                  | data_keys(dict): 录制设置<br>例如:<br>data_keys = {<br>'camera': {<br>'camera_prim_list': [<br>'/World/base_link/Head_Camera'<br>],<br>'render_depth': True,<br>'render_semantic': True<br>},<br>'pose': [<br>'/World/obj1'<br>],<br>'joint_position': True,<br>'gripper': True<br>}<br>fps(int): 录制帧率<br>task_name(str)                            |                                                                                                                                       |
| client.stop_recording()         | 停止录制                  |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.reset()                  | 重置场景、机器人和对象           |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
| client.Exit()                   | 退出应用程序                |                                                                                                                                                                                                                                                                                                                                               |                                                                                                                                       |
