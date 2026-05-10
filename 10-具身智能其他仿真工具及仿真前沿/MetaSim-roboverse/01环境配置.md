```bash
pip install uv

export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
```

| Simulator     | Installation Command              | Supported Python Versions | Recommended Python Version |
| ------------- | --------------------------------- | ------------------------- | -------------------------- |
| MuJoCo        | `uv pip install -e ".[mujoco]"`   | 3.9-3.13                  | 3.10                       |
| SAPIEN v2     | `uv pip install -e ".[sapien2]"`  | 3.7-3.11                  | 3.10                       |
| SAPIEN v3     | `uv pip install -e ".[sapien3]"`  | 3.8-3.12                  | 3.10                       |
| Genesis       | `uv pip install -e ".[genesis]"`  | 3.10-3.12                 | 3.10                       |
| PyBullet      | `uv pip install -e ".[pybullet]"` | 3.6-3.11                  | 3.10                       |
| IsaacLab v1.4 | See below                         | 3.10                      | 3.10                       |
| IsaacLab v2   | See below                         | 3.10                      | 3.10                       |
| IsaacGym      | See below                         | 3.6-3.8                   | 3.8                        |

```
uv pip install -e ".[isaaclab2]"
cd third_party
git clone --depth 1 --branch v2.0.2 git@github.com:isaac-sim/IsaacLab.git IsaacLab2 && cd IsaacLab2
./isaaclab.sh -i
```
