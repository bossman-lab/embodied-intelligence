# ETPNav 复现指南

## 🌟 项目简介 (About)

> **官方开源仓库**: [MarSaKi/ETPNav](https://github.com/MarSaKi/ETPNav)
> **论文地址**: [ETPNav: Evolving Topological Planning for Vision-Language Navigation in Continuous Environments](https://arxiv.org/abs/2304.03047v2) (该论文已于 2024 年被顶级期刊 **IEEE TPAMI** 收录)

**声明：ETPNav 是由 Dong An 等人提出的一项优秀工作，目前也是连续环境视觉语言导航 (VLN-CE) 领域的一个强力 Baseline。本项目及本文档主要是我在学习和复现 ETPNav 官方开源项目时，整理的详细踩坑笔记与操作指南。希望能为后续想要复现该工作的研究者提供一份清晰、闭环的参考教程。**

<p align="center">
  <img width="1044" height="287" alt="ETPNav展示1" src="https://github.com/user-attachments/assets/fad76d29-53fb-4f8f-aa66-8eb704f748de" />
  <br>
  <img width="1023" height="294" alt="ETPNav展示2" src="https://github.com/user-attachments/assets/c06c0b09-d99e-4cd9-90e5-05833dca93b4" />
  <br>
  <img width="523" height="287" alt="ETPNav展示3" src="https://github.com/user-attachments/assets/1c4b2b30-a174-4830-aeb2-478c4718ee65" />
</p>

关于 **ETPNav** (Evolving Topological Planning) 算法本身，它主要解决了现有方法在长距离规划和避障上的局限，重点突破了两个核心能力：

1. **在线拓扑建图与长距离规划**：模型无需预先探索环境，即可通过自组织沿途预测的路点 (waypoints) 在线动态构建拓扑地图。这使得智能体能够将导航任务解耦为高层规划与底层控制。基于该拓扑地图，跨模态规划器 (基于 Transformer) 能够更好地理解指令并生成长距离的导航路径规划。
2. **连续环境下的避障控制**：针对连续环境的复杂性，ETPNav 提出了一种基于试错启发式 (trial-and-error heuristic) 的鲁棒避障控制器 (Tryout)，有效防止了智能体在连续环境中因碰撞障碍物而陷入死锁的情况。

## 1. 环境配置

本次复现教程使用 Python 3.8 环境。请按照以下步骤配置虚拟环境及相关依赖：

### 1.1 创建虚拟环境与安装 PyTorch

```bash
# 创建并激活 conda 虚拟环境
conda create -n vlnce38 python=3.8
conda activate vlnce38

# 安装 PyTorch (1.9.1+cu111)
（方式一）
pip install torch==1.9.1+cu111 torchvision==0.10.1+cu111 \
-f https://download.pytorch.org/whl/torch_stable.html \
-i https://mirrors.cloud.tencent.com/pypi/simple

（方式二）
## 下载torch 1.9.1+cu111（Python3.8/Linux x86_64）
wget https://mirrors.aliyun.com/pytorch-wheels/cu111/torch-1.9.1%2Bcu111-cp38-cp38-linux_x86_64.whl

## 下载torchvision 0.10.1+cu111（匹配上面的torch版本）
wget https://mirrors.aliyun.com/pytorch-wheels/cu111/torchvision-0.10.1%2Bcu111-cp38-cp38-linux_x86_64.whl

pip install torch-1.9.1+cu111-cp38-cp38-linux_x86_64.whl torchvision-0.10.1+cu111-cp38-cp38-linux_x86_64.whl
```

### 1.2 安装项目依赖

下载 `requirements.txt`：[百度网盘](https://pan.baidu.com/s/1PU1pm596QtL8ZNG08602Dg) (提取码: `8je8`) 

```bash
pip install "pip<24.1" setuptools==65.5.0 wheel==0.38.4
python -m pip install -r requirements.txt
```

### 1.3 安装 Habitat 仿真器

(1)下载无头版本 Habitat-sim v0.1.7 预编译包：[点击下载](https://anaconda.org/aihabitat/habitat-sim/0.1.7/download/linux-64/habitat-sim-0.1.7-py3.8_headless_linux_856d4b08c1a2632626bf0d205bf46471a99502b7.tar.bz2)
(2)下载habitat-lab v0.1.7[点击下载](https://github.com/facebookresearch/habitat-lab/releases/tag/v0.1.7)
```bash
# 安装 habitat-sim
conda install habitat-sim-0.1.7-py3.8_headless_linux_856d4b08c1a2632626bf0d205bf46471a99502b7.tar.bz2

# 安装 habitat-lab
cd habitat-lab-0.1.7
pip install -e .
```
### 1.4 云服务器环境依赖修复 (选做)

在云端容器或精简版 Linux 系统中运行 Habitat 仿真器时，通常会遇到缺少图形渲染库（`OpenGL/EGL` 报错）以及 C++ 底层库版本冲突（`CXXABI` 报错）等问题。请依次执行以下步骤一次性解决：

**1. 安装系统级图形渲染依赖(解决 缺失libEGL库 报错)**

Habitat 的底层三维引擎 Magnum 需要以下库才能正常初始化：

```bash
apt-get update
apt-get install -y libopengl0 libgl1-mesa-glx libglib2.0-0 libegl1
```

**2. 升级系统级 C++ 标准库 (解决 CXXABI 报错)**

```bash
# 安装管理 PPA 源的工具
apt-get install -y software-properties-common

# 添加 ubuntu-toolchain-r 测试源
add-apt-repository ppa:ubuntu-toolchain-r/test -y
apt-get update

# 仅升级系统的 C++ 标准库
apt-get install --only-upgrade libstdc++6 -y
```

### 1.5 下载ETPnav-main原始代码
[离线下载](https://github.com/MarSaKi/ETPNav)
```bash
# 克隆仓库
git clone https://gh-proxy.org/https://github.com/MarSaKi/ETPNav.git
```


## 2. 数据集下载

### 2.1 场景数据 (Scenes): Matterport3D (MP3D)

需要下载 Matterport3D 场景重建数据，共有 90 个场景，数据集大小约 22GB。最终的存放路径应为：`data/scene_datasets/mp3d/{scene}/{scene}.glb`

* **方式一：官方脚本申请下载** (需要 Python 2.7)
  请访问 Matterport3D 的[官方项目主页](https://niessner.github.io/Matterport/)，按照网页上的说明获取官方的下载脚本 (`download_mp.py`)。
  ```bash
  python download_mp.py --task habitat -o data/scene_datasets/mp3d/
  ```

* **方式二：网盘快捷下载**
  * 链接: [百度网盘](https://pan.baidu.com/s/1XRXDsRhg4j09nHxXBe9boA)
  * 提取码: `4kz6`

### 2.2 任务数据 (Episodes): R2R & RxR

请将以下下载的 Episode 数据放置在 `data/datasets` 目录下。

| 数据集 | 下载链接 | 存放路径 |
| --- | --- | --- |
| **R2R_VLNCE_v1-2_preprocessed** | [Google Drive](https://drive.google.com/file/d/1j9sQ0w4wFYSafh42U8VCuKTwMrnrsV6z/view) | `data/datasets` |
| **R2R_VLNCE_v1-2_preprocessed_BERTidx** | [百度网盘](https://pan.baidu.com/s/1Sz7Q7iXcLV7ToQ0FeZmHIg) (提取码: `88yy`) | `data/datasets` |
| **RxR** | [百度网盘](https://pan.baidu.com/s/1WZwKwdBt0ofdmuTKmWjHSQ) (提取码: `g317`) | `data/datasets` |

### 2.3 连通图 (Connectivity Graphs)

用于可视化的连通图文件：
* **下载链接**: [connectivity_graphs.pkl](https://github.com/jacobkrantz/VLN-CE/blob/master/data/connectivity_graphs.pkl)
* **存放路径**: `data/connectivity_graphs.pkl`

---

## 3. 模型权重与预训练数据

请按要求下载相应的编码器权重、预测器权重及预训练特征文件，并放置在指定目录下。

### 3.1 编码器与组件权重

| 模型组件 | 下载链接 | 目标存放路径 |
| --- | --- | --- |
| **Waypoint Predictor (R2R-CE)** | [[原项目链接](https://drive.google.com/file/d/1goXbgLP2om9LsEQZ5XvB0UpGK4A5SGJC/view)] | `data/wp_pred/check_cwp_bestdist_hfov90` |
| **Waypoint Predictor (RxR-CE)** | [[原项目链接](https://drive.google.com/file/d/1LxhXkise-H96yMMrTPIT6b2AGjSjqqg0/view)] | `data/wp_pred/check_cwp_bestdist_hfov63` |
| **BERT 权重** | [Huggingface](https://huggingface.co/google-bert/bert-base-uncased/tree/main) | `bert_config/bert-base-uncased` |
| **RGB 编码器 (ViT-B32)** | [Huggingface](https://huggingface.co/jinaai/clip-models/blob/main/ViT-B-32.pt) | `.cache/clip/ViT-B-32.pt` |
| **Depth 编码器 (ResNet50)** | [Gibson Pretrained](https://dl.fbaipublicfiles.com/habitat/data/baselines/v1/ddppo/ddppo-models/gibson-2plus-resnet50.pth) | `data/pretrained_models/ddppo-models/gibson-2plus-resnet50.pth` |

### 3.2 预训练数据 (Pretraining Data)

* **R2R 预训练数据**: [下载链接](https://www.dropbox.com/scl/fo/4iaw2ii2z2iupu0yn4tqh/AP2waOdlwdbJE5sUti2557U/R2R?dl=0&rlkey=88khaszmvhybxleyv0a9bulyn&subfolder_nav_tracking=1) $\rightarrow$ 存至 `pretrain_src/datasets/R2R`
* **预计算视觉特征**: [下载链接](https://drive.google.com/file/d/1D3Gd9jqRfF-NjlxDAQG_qwxTIakZlrWd/view) $\rightarrow$ 存至 `pretrain_src/datasets/img_features`
* **LXMERT 预训练权重**:[下载链接](https://nlp.cs.unc.edu/data/model_LXRT.pth) $\rightarrow$ 存至 `pretrain_src/datasets/pretrained/LXMERT`

### 3.3 最终预训练权重 (Pretrained Weights)

如果你希望跳过预训练阶段，可直接下载已提供的预训练权重：
* **下载链接**: [百度网盘](https://pan.baidu.com/s/1oTmRkuj6syTmI6kE78k0JQ) (提取码: `vfsh`)
* **存放路径**: `pretrained/ETP/model_step_82500.pt`

**最终文件夹结构如下：**

```text
ETPNav/
├── assets/
├── bert_config/
│   ├── bert-base-uncased/
│   │   ├── config.json
│   │   ├── pytorch_model.bin
│   │   ├── tokenizer_config.json
│   │   └── vocab.txt
│   └── xlm-roberta-base/
├── data/
│   ├── datasets/
│   │   ├── R2R_VLNCE_v1-2_preprocessed/
│   │   ├── R2R_VLNCE_v1-2_preprocessed_BERTidx/
│   │   └── RxR_VLNCE_v0_enc_xlmr/
│   ├── ddppo-models/
│   │   └── gibson-2plus-resnet50.pth
│   ├── scene_datasets/
│   │   └── mp3d/
│   ├── wp_pred/
│   │   ├── check_cwp_bestdist_hfov79
│   │   └── check_cwp_bestdist_hfov90
│   └── connectivity_graphs.pkl
├── habitat_extensions/
├── precompute_img_features/
├── pretrain_src/
│   ├── datasets/
│   │   ├── pretrained/
│   │   │   └── LXMERT/
│   │   │       └── model_LXRT.pth
│   │   └── R2R/
│   ├── img_features/
│   │   ├── CLIP-ViT-B-32-views-habitat.hdf5
│   │   └── ddppo_resnet50_depth_features.hdf5
│   ├── pretrain_src/
│   └── run_pt/
├── pretrained/
│   ├── ETP/
│   │   └── model_step_82500.pt
├── run_r2r/
├── run_rxr/
├── vlnce_baselines/
├── .gitignore
├── environment.yaml
├── LICENSE
├── README.md
└── run.py
```

---

## 4. 代码运行

### 4.1 预训练 (Pretraining)

（如果想跳过这个步骤，可以使用前面下载好的预训练权重，直接进行微调或评估）

1. **修改引用路径**：如果连不上外网，可将 BERT 权重地址更换为本地。
   <p align="center">
     <img width="1566" height="444" alt="修改引用路径" src="https://github.com/user-attachments/assets/47b99ba4-f96a-441b-82d4-0b117a2ba452" />
   </p>

2. **修改 GPU 数量**：根据实际硬件条件按需调整分布式训练的 GPU 数量。
   <p align="center">
     <img width="1148" height="349" alt="修改 GPU 数量" src="https://github.com/user-attachments/assets/0336bc2b-9ae6-4294-9f73-105646ff49b9" />
   </p>

3. **启动预训练**：该步骤主要执行 MLM (Masked Language Modeling) 和 SAP 两个预训练任务。
   ```bash
   CUDA_VISIBLE_DEVICES=0 bash pretrain_src/run_pt/run_r2r.bash 233
   ```
   训练日志会保存到 `/ETPNav-main/pretrained/r2r_ce/mlm.sap_habitat_depth/logs/log.txt`，可根据实际测评指标选择一个最好的预训练权重：
   <p align="center">
     <img width="395" height="260" alt="预训练日志" src="https://github.com/user-attachments/assets/321a4a31-4fb1-420a-b40c-a1540ab5d82a" />
   </p>

### 4.2 微调 (Finetuning)

1. **配置预训练权重路径**：将脚本中的加载路径指向 `pretrained/ETP/model_step_82500.pt`。
   <p align="center">
     <img width="1019" height="499" alt="配置预训练权重路径1" src="https://github.com/user-attachments/assets/5b51f709-6b75-439e-993f-f4d714e8a879" />
     <br>
     <img width="1123" height="497" alt="配置预训练权重路径2" src="https://github.com/user-attachments/assets/0c85ccfa-e76c-4518-8919-bd1246734127" />
   </p>

2. **修改 GPU 数量**：根据实际硬件条件按需调整分布式训练的 GPU 数量。
   <p align="center">
     <img width="1060" height="434" alt="修改GPU数量1" src="https://github.com/user-attachments/assets/1bf9004e-4991-411c-8b7c-92150f8ec5c4" />
     <br>
     <img width="1337" height="333" alt="修改GPU数量2" src="https://github.com/user-attachments/assets/e45b0d7e-7b7b-431b-a760-37830c0dee95" />
   </p>

3. **启动微调**：
   **注**：单张 RTX 4090 显卡完成微调大约需要 1.5 天。
   ```bash
   CUDA_VISIBLE_DEVICES=0 bash run_r2r/main.bash train 2333  # training
   ```
4. **取消TensorFlow警告**（可选）：
  export TF_ENABLE_ONEDNN_OPTS=0
  export TF_CPP_MIN_LOG_LEVEL=2


### 4.3 测试与评估 (Eval & Testing)

#### 评估

运行以下命令进行评估：

```bash
CUDA_VISIBLE_DEVICES=0 bash run_r2r/main.bash eval  2333  # evaluation
```

**以下是 eval 模式得到的评价指标：**

<p align="center">
  <img width="1175" height="266" alt="评价指标" src="https://github.com/user-attachments/assets/fd25cf3f-efed-4265-b46c-0eeaf5f2c810" />
</p>

**增加可视化（可选）**

在此处可以选择将测试视频保存本地，或者使用 TensorBoard 可视化。

<p align="center">
  <img width="1309" height="438" alt="可视化配置" src="https://github.com/user-attachments/assets/d083cf80-8e06-4c31-882f-6b5fe259eff7" />
</p>

如果选择 `disk` 模式，并重新运行评估代码，导航视频会保存至：
`ETPNav-main/data/logs/video/release_r2r/*`

**以下是部分场景可视化视频演示：**

https://github.com/user-attachments/assets/e5797cce-265b-4e95-9ba4-f732c1a2813c

<p align="center">
  <img width="686" height="1440" alt="oLBMNvg9in8-478-spl1 00" src="https://github.com/user-attachments/assets/bf874fef-0de3-4405-b644-23cbf065a976" />
</p>

#### 推理

运行以下命令进行推理：

```bash
CUDA_VISIBLE_DEVICES=0 bash run_r2r/main.bash inference  2333  # inference
```

---

## 5. 参考与致谢 (Acknowledgements)

本复现教程与代码主要参考并依赖于以下优秀的开源项目。在此向原作者们的开源精神致以诚挚的感谢：

* **ETPNav 官方仓库**: [MarSaKi/ETPNav](https://github.com/MarSaKi/ETPNav) —— 本项目核心复现的目标。
* **VLN-CE 官方框架**: [jacobkrantz/VLN-CE](https://github.com/jacobkrantz/VLN-CE) —— 提供了连续环境导航的基础设施与评测标准。
* **Discrete-Continuous-VLN**: [YicongHong/Discrete-Continuous-VLN](https://github.com/YicongHong/Discrete-Continuous-VLN) —— 为预训练、路点预测等模块提供了重要参考。
