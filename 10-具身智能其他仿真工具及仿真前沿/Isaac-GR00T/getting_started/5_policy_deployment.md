## 策略部署

> 本教程要求用户拥有训练好的模型检查点和一个物理的So100 Lerobot机器人来运行策略。

在本教程中，我们将展示部署训练好的策略的示例脚本和代码片段。我们将使用So100 Lerobot机械臂作为示例。

![alt text](../media/so100_eval_demo.gif)

### 1. 加载策略

运行以下命令启动策略服务器。

```bash
python scripts/inference_service.py --server \
    --model_path <PATH_TO_YOUR_CHECKPOINT> \
    --embodiment_tag new_embodiment \
    --data_config so100 \
    --denoising_steps 4
```

 - 模型路径是用于策略的检查点路径，用户应提供微调后的检查点路径
 - 去噪步骤是用于策略的去噪步骤数量，我们注意到使用4个去噪步骤的效果与16个相当
 - 实施标签是用于策略的实施标签，用户在新机器人上微调时应使用new_embodiment
 - 数据配置是用于策略的数据配置。用户应使用`so100`。如果想使用不同的机器人，请实现自己的`ModalityConfig`和`TransformConfig`

### 2. 客户端节点

要部署微调后的模型，可以使用`scripts/inference_policy.py`脚本。该脚本将启动一个策略服务器。

客户端节点可以使用`from gr00t.eval.service import ExternalRobotInferenceClient`类实现。该类是一个独立的客户端-服务器类，可用于与策略服务器通信，`get_action()`端点是唯一的接口。

```python
from gr00t.eval.service import ExternalRobotInferenceClient
from typing import Dict, Any

raw_obs_dict: Dict[str, Any] = {} # 填写空白处

policy = ExternalRobotInferenceClient(host="localhost", port=5555)
raw_action_chunk: Dict[str, Any] = policy.get_action(raw_obs_dict)
```

用户可以直接复制该类并在单独的隔离环境中实现自己的客户端节点。

### So100 Lerobot机械臂示例

我们为So100 Lerobot机械臂提供了一个示例客户端节点实现。有关更多详细信息，请参阅示例脚本`scripts/eval_gr00t_so100.py`。


用户可以运行以下命令启动客户端节点。
```bash
python examples/eval_gr00t_so100.py \
 --use_policy --host <YOUR_POLICY_SERVER_HOST> \
 --port <YOUR_POLICY_SERVER_PORT> \
 --camera_index <YOUR_CAMERA_INDEX>
```

这将激活机器人，并调用策略服务器的`action = get_action(obs)`端点获取动作，然后在机器人上执行该动作。
