# 机器人数据转换指南

## 概述

本指南展示了如何将机器人数据转换为适用于我们的[LeRobot数据集V2.0格式](https://github.com/huggingface/lerobot?tab=readme-ov-file#the-lerobotdataset-format)——`GR00T LeRobot`。虽然我们添加了额外的结构，但我们的模式与上游LeRobot 2.0保持完全兼容。这些额外的元数据和结构允许对机器人数据进行更详细的规范和语言标注。

## 要求

### 核心要求

文件夹应遵循类似下面的结构，并包含这些核心文件夹和文件：

```
.
├─meta 
│ ├─episodes.jsonl
│ ├─modality.json # -> GR00T LeRobot特有
│ ├─info.json
│ └─tasks.jsonl
├─videos
│ └─chunk-000
│   └─observation.images.ego_view
│     └─episode_000001.mp4
│     └─episode_000000.mp4
└─data
  └─chunk-000
    ├─episode_000001.parquet
    └─episode_000000.parquet
```

### 视频观察(video/chunk-*)
视频文件夹将包含与每个episode相关的mp4文件，遵循episode_00000X.mp4命名格式，其中X表示episode编号。
**要求**：
- 必须以MP4文件格式存储。
- 应使用格式：`observation.images.<video_name>`命名。


### 数据(data/chunk-*)
数据文件夹将包含与每个episode相关的所有parquet文件，遵循episode_00000X.parquet命名格式，其中X表示episode编号。
每个parquet文件将包含：
- 状态信息：存储为observation.state，这是所有状态模态的一维连接数组。
- 动作：存储为action，这是所有动作模态的一维连接数组。
- 时间戳：存储为timestamp，这是起始时间的浮点数。
- 注释：存储为annotation.<annotation_source>.<annotation_type>(.<annotation_name>)（参见示例配置中的注释字段以了解命名示例）。其他列不应使用annotation前缀，如果对添加多个注释感兴趣，请参阅(multiple-annotation-support)。

#### 示例Parquet文件
以下是[demo_data](../../demo_data/robot_sim.PickNPlace/)目录中存在的robot_sim.PickNPlace数据集的示例。
```
{
    "observation.state":[-0.01147082911843003,...,0], // 基于modality.json文件的连接状态数组
    "action":[-0.010770668025204974,...0], // 基于modality.json文件的连接动作数组
    "timestamp":0.04999995231628418, // 观察的时间戳
    "annotation.human.action.task_description":0, // meta/tasks.jsonl文件中任务描述的索引
    "task_index":0, // meta/tasks.jsonl文件中任务的索引
    "annotation.human.validity":1, // meta/tasks.jsonl文件中任务的索引
    "episode_index":0, // episode的索引
    "index":0, // 观察的索引。这是整个数据集中所有观察的全局索引。
    "next.reward":0, // 下一个观察的奖励
    "next.done":false // episode是否完成
}
```

### 元数据

- `episodes.jsonl`包含整个数据集中所有episode的列表。每个episode包含一系列任务和episode的长度。
- `tasks.jsonl`包含整个数据集中所有任务的列表。
- `modality.json`包含模态配置。
- `info.json`包含数据集信息。

#### meta/tasks.jsonl
以下是包含任务描述的`meta/tasks.jsonl`文件的示例。
```
{"task_index": 0, "task": "pick the squash from the counter and place it in the plate"}
{"task_index": 1, "task": "valid"}
```

可以在parquet文件中引用任务索引来获取任务描述。因此在这种情况下，第一个观察的`annotation.human.action.task_description`是"pick the squash from the counter and place it in the plate"，`annotation.human.validity`是"valid"。

`tasks.json`包含整个数据集中所有任务的列表。

#### meta/episodes.jsonl

以下是包含episode信息的`meta/episodes.jsonl`文件的示例。

```
{"episode_index": 0, "tasks": [...], "length": 416}
{"episode_index": 1, "tasks": [...], "length": 470}
```

`episodes.json`包含整个数据集中所有episode的列表。每个episode包含一系列任务和episode的长度。


#### `meta/modality.json`配置

此文件提供有关状态和动作模态的详细元数据，使以下功能成为可能：

- **分离数据存储和解释：**
  - **状态和动作：**存储为连接的float32数组。`modality.json`文件提供了将这些数组解释为具有额外训练信息的不同、细粒度字段所需的元数据。
  - **视频：**存储为单独的文件，配置文件允许将它们重命名为标准化格式。
  - **注释：**跟踪所有注释字段。如果没有注释，请不要在配置文件中包含`annotation`字段。
- **细粒度分割：**将状态和动作数组分为更具语义意义的字段。
- **清晰映射：**数据维度的明确映射。
- **复杂数据转换：**在训练期间支持特定字段的归一化和旋转转换。

##### 模式

```json
{
    "state": {
        "<state_key>": {
            "start": <int>,         // 状态数组中的起始索引
            "end": <int>,           // 状态数组中的结束索引
            "rotation_type": <str>,  // 可选：指定旋转格式
            "dtype": <str>,         // 可选：指定数据类型
            "range": <tuple[float, float]>, // 可选：指定模态的范围
        }
    },
    "action": {
        "<action_key>": {
            "start": <int>,         // 动作数组中的起始索引
            "end": <int>,           // 动作数组中的结束索引
            "absolute": <bool>,      // 可选：true表示绝对值，false表示相对/增量值
            "rotation_type": <str>,  // 可选：指定旋转格式
            "dtype": <str>,         // 可选：指定数据类型
            "range": <tuple[float, float]>, // 可选：指定模态的范围
        }
    },
    "video": {
        "<new_key>": {
            "original_key": "<original_video_key>"
        }
    },
    "annotation": {
        "<annotation_key>": {}  // 空字典，保持与其他模态的一致性
    }
}
```

**支持的旋转类型：**

- `axis_angle`
- `quaternion`
- `rotation_6d`
- `matrix`
- `euler_angles_rpy`
- `euler_angles_ryp`
- `euler_angles_pry`
- `euler_angles_pyr`
- `euler_angles_yrp`
- `euler_angles_ypr`

##### 示例配置

```json
{
    "state": {
        "left_arm": { // parquet文件中observation.state数组的前7个元素是左臂
            "start": 0,
            "end": 7
        },
        "left_hand": { // parquet文件中observation.state数组的接下来6个元素是左手
            "start": 7,
            "end": 13
        },
        "left_leg": {
            "start": 13,
            "end": 19
        },
        "neck": {
            "start": 19,
            "end": 22
        },
        "right_arm": {
            "start": 22,
            "end": 29
        },
        "right_hand": {
            "start": 29,
            "end": 35
        },
        "right_leg": {
            "start": 35,
            "end": 41
        },
        "waist": {
            "start": 41,
            "end": 44
        }
    },
    "action": {
        "left_arm": {
            "start": 0,
            "end": 7
        },
        "left_hand": {
            "start": 7,
            "end": 13
        },
        "left_leg": {
            "start": 13,
            "end": 19
        },
        "neck": {
            "start": 19,
            "end": 22
        },
        "right_arm": {
            "start": 22,
            "end": 29
        },
        "right_hand": {
            "start": 29,
            "end": 35
        },
        "right_leg": {
            "start": 35,
            "end": 41
        },
        "waist": {
            "start": 41,
            "end": 44
        }
    },
    "video": {
        "ego_view": { // 视频存储在videos/chunk-*/observation.images.ego_view/episode_00000X.mp4中
            "original_key": "observation.images.ego_view"
        }
    },
    "annotation": {
        "human.action.task_description": {}, // 任务描述存储在meta/tasks.jsonl文件中
        "human.validity": {}
    }
}
```

### 多注释支持

为了支持单个parquet文件中的多个注释，用户可以向parquet文件添加额外的列。用户应该像处理原始LeRobot V2数据集中的`task_index`列一样处理这些列：

在LeRobot V2中，实际的语言描述存储在`meta/tasks.jsonl`文件的一行中，而parquet文件仅存储`task_index`列中的相应索引。我们遵循相同的约定，并在`annotation.<annotation_source>.<annotation_type>`列中存储每个注释的相应索引。尽管`task_index`列仍可用于默认注释，但需要专用列`annotation.<annotation_source>.<annotation_type>`以确保它可由我们的自定义数据加载器加载。

### GR00T LeRobot对标准LeRobot的扩展
GR00T LeRobot是标准LeRobot格式的一种变体，具有更多固定要求：
- 标准LeRobot格式使用meta/stats.json，但我们的数据加载器不需要它。如果计算太耗时，可以安全地忽略此文件。
- "observation.state"键中必须始终包含本体感受器状态。
- 我们支持多通道注释格式（例如，粗粒度、微调），允许用户通过`annotation.<annotation_source>.<annotation_type>`键根据需要添加任意数量的注释通道。
- 我们需要一个标准LeRobot格式中不存在的额外元数据文件`meta/modality.json`。

#### 注意

- 仅在可选字段与默认值不同时指定它们。
- 视频键映射使整个数据集的摄像机名称标准化。
- 所有索引都是从零开始的，并遵循Python的数组切片约定（`[start:end]`）。

## 示例

请参阅[示例数据集](../../demo_data/robot_sim.PickNPlace/)以获取完整参考。

