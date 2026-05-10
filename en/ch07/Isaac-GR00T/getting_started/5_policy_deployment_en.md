## Policy Deployment

> This tutorial requires users to have a trained model checkpoint and a physical So100 Lerobot robot to run the policy.

In this tutorial, we will demonstrate example scripts and code snippets for deploying a trained policy. We will use the So100 Lerobot robotic arm as an example.

![alt text](../media/so100_eval_demo.gif)

### 1. Loading the Policy

Run the following command to start the policy server:

```bash
python scripts/inference_service.py --server \
    --model_path <PATH_TO_YOUR_CHECKPOINT> \
    --embodiment_tag new_embodiment \
    --data_config so100 \
    --denoising_steps 4
```

 - The model path is the checkpoint path for the policy; users should provide the path to their fine-tuned checkpoint
 - Denoising steps is the number of denoising steps for the policy; we've observed that using 4 denoising steps achieves comparable results to 16
 - Embodiment tag is the embodiment tag for the policy; users should use `new_embodiment` when fine-tuning on new robots
 - Data config is the data configuration for the policy. Users should use `so100`. If you want to use a different robot, please implement your own `ModalityConfig` and `TransformConfig`

### 2. Client Node

To deploy your fine-tuned model, you can use the `scripts/inference_policy.py` script. This script will start a policy server.

The client node can be implemented using the `from gr00t.eval.service import ExternalRobotInferenceClient` class. This class is a standalone client-server class that can be used to communicate with the policy server, with the `get_action()` endpoint being the only interface.

```python
from gr00t.eval.service import ExternalRobotInferenceClient
from typing import Dict, Any

raw_obs_dict: Dict[str, Any] = {} # Fill in the blank

policy = ExternalRobotInferenceClient(host="localhost", port=5555)
raw_action_chunk: Dict[str, Any] = policy.get_action(raw_obs_dict)
```

Users can directly copy this class and implement their own client node in a separate isolated environment.

### So100 Lerobot Arm Example

We provide an example client node implementation for the So100 Lerobot arm. For more details, refer to the example script `scripts/eval_gr00t_so100.py`.

Users can run the following command to start the client node:
```bash
python examples/eval_gr00t_so100.py \
 --use_policy --host <YOUR_POLICY_SERVER_HOST> \
 --port <YOUR_POLICY_SERVER_PORT> \
 --camera_index <YOUR_CAMERA_INDEX>
```

This will activate the robot and call the policy server's `action = get_action(obs)` endpoint to obtain actions, which will then be executed on the robot.