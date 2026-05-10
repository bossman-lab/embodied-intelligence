# Robot Data Conversion Guide

## Overview

This guide demonstrates how to convert your robot data to the format compatible with our [LeRobot Dataset V2.0](https://github.com/huggingface/lerobot?tab=readme-ov-file#the-lerobotdataset-format) - `GR00T LeRobot`. While we've added additional structure, our schema remains fully compatible with upstream LeRobot 2.0. These additional metadata and structures allow for more detailed specification and language annotation of your robot data.

## Requirements

### Core Requirements

Folders should follow a structure similar to the one below and contain these core folders and files:

```
.
├─meta 
│ ├─episodes.jsonl
│ ├─modality.json # -> GR00T LeRobot specific
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

### Video Observations (video/chunk-*)
The video folder will contain mp4 files related to each episode, following the naming format episode_00000X.mp4 where X represents the episode number.
**Requirements**:
- Must be stored in MP4 file format.
- Should use the format: `observation.images.<video_name>` for naming.


### Data (data/chunk-*)
The data folder will contain all parquet files related to each episode, following the naming format episode_00000X.parquet where X represents the episode number.
Each parquet file will contain:
- State information: stored as observation.state, which is a 1D concatenated array of all state modalities.
- Actions: stored as action, which is a 1D concatenated array of all action modalities.
- Timestamps: stored as timestamp, which is a float representing the start time.
- Annotations: stored as annotation.<annotation_source>.<annotation_type>(.<annotation_name>) (see annotation fields in example configuration for naming examples). Other columns should not use the annotation prefix. If interested in adding multiple annotations, please refer to (multiple-annotation-support).

#### Example Parquet File
Below is an example from the robot_sim.PickNPlace dataset present in the [demo_data](../../demo_data/robot_sim.PickNPlace/) directory.
```
{
    "observation.state":[-0.01147082911843003,...,0], // Concatenated state array based on modality.json file
    "action":[-0.010770668025204974,...0], // Concatenated action array based on modality.json file
    "timestamp":0.04999995231628418, // Timestamp of the observation
    "annotation.human.action.task_description":0, // Index of task description in meta/tasks.jsonl file
    "task_index":0, // Index of task in meta/tasks.jsonl file
    "annotation.human.validity":1, // Index of task in meta/tasks.jsonl file
    "episode_index":0, // Index of the episode
    "index":0, // Global index of all observations in the entire dataset.
    "next.reward":0, // Reward of the next observation
    "next.done":false // Whether the episode is completed
}
```

### Metadata

- `episodes.jsonl` contains a list of all episodes in the entire dataset. Each episode contains a series of tasks and the length of the episode.
- `tasks.jsonl` contains a list of all tasks in the entire dataset.
- `modality.json` contains modality configuration.
- `info.json` contains dataset information.

#### meta/tasks.jsonl
The following is an example of a `meta/tasks.jsonl` file containing task descriptions.
```
{"task_index": 0, "task": "pick the squash from the counter and place it in the plate"}
{"task_index": 1, "task": "valid"}
```

You can reference the task index in parquet files to get task descriptions. Therefore, in this case, the `annotation.human.action.task_description` of the first observation is "pick the squash from the counter and place it in the plate", and `annotation.human.validity` is "valid".

`tasks.json` contains a list of all tasks in the entire dataset.

#### meta/episodes.jsonl

The following is an example of an `meta/episodes.jsonl` file containing episode information.

```
{"episode_index": 0, "tasks": [...], "length": 416}
{"episode_index": 1, "tasks": [...], "length": 470}
```

`episodes.json` contains a list of all episodes in the entire dataset. Each episode contains a series of tasks and the length of the episode.


#### `meta/modality.json` Configuration

This file provides detailed metadata about state and action modalities, enabling the following features:

- **Separation of data storage and interpretation:**
  - **State and action:** Stored as concatenated arrays. The `modality.json` file provides the metadata needed to interpret these arrays as distinct, fine-grained fields with additional training information.
  - **Video:** Stored as separate files, with configuration allowing renaming to standardized formats.
  - **Annotations:** Track all annotation fields. If there are no annotations, do not include the `annotation` field in the configuration file.
- **Fine-grained segmentation:** Dividing state and action arrays into more semantically meaningful fields.
- **Clear mapping:** Explicit mapping of data dimensions.
- **Complex data transformations:** Supporting normalization and rotation transformations for specific fields during training.

##### Schema

```json
{
    "state": {
        "<state_key>": {
            "start": <int>,         // Start index in the state array
            "end": <int>,           // End index in the state array
            "rotation_type": <str>,  // Optional: specify rotation format
            "dtype": <str>,         // Optional: specify data type
            "range": <tuple[float, float]>, // Optional: specify modality range
        }
    },
    "action": {
        "<action_key>": {
            "start": <int>,         // Start index in the action array
            "end": <int>,           // End index in the action array
            "absolute": <bool>,      // Optional: true for absolute values, false for relative/incremental values
            "rotation_type": <str>,  // Optional: specify rotation format
            "dtype": <str>,         // Optional: specify data type
            "range": <tuple[float, float]>, // Optional: specify modality range
        }
    },
    "video": {
        "<new_key>": {
            "original_key": "<original_video_key>"
        }
    },
    "annotation": {
        "<annotation_key>": {}  // Empty dictionary for consistency with other modalities
    }
}
```

**Supported rotation types:**

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

##### Example Configuration

```json
{
    "state": {
        "left_arm": { // First 7 elements of observation.state array in parquet file are left arm
            "start": 0,
            "end": 7
        },
        "left_hand": { // Next 6 elements of observation.state array in parquet file are left hand
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
        "ego_view": { // Videos are stored in videos/chunk-*/observation.images.ego_view/episode_00000X.mp4
            "original_key": "observation.images.ego_view"
        }
    },
    "annotation": {
        "human.action.task_description": {}, // Task descriptions are stored in meta/tasks.jsonl file
        "human.validity": {}
    }
}
```

### Multiple Annotation Support

To support multiple annotations in a single parquet file, users can add additional columns to the parquet file. Users should handle these columns the same way as the `task_index` column in the original LeRobot V2 dataset:

In LeRobot V2, the actual language descriptions are stored in a line in the `meta/tasks.jsonl` file, while the parquet file only stores the corresponding index in the `task_index` column. We follow the same convention and store the corresponding index for each annotation in the `annotation.<annotation_source>.<annotation_type>` column. While the `task_index` column can still be used for default annotations, a dedicated column `annotation.<annotation_source>.<annotation_type>` is needed to ensure it can be loaded by our custom data loader.

### GR00T LeRobot Extensions to Standard LeRobot
GR00T LeRobot is a variant of the standard LeRobot format with additional fixed requirements:
- The standard LeRobot format uses meta/stats.json, but our data loader does not require it. You can safely omit this file if computation is too time-consuming.
- Proprioceptive state must always be included in the "observation.state" key.
- We support multi-channel annotation formats (e.g., coarse-grained, fine-tuned), allowing users to add as many annotation channels as needed through the `annotation.<annotation_source>.<annotation_type>` key.
- We require an additional metadata file `meta/modality.json` that does not exist in the standard LeRobot format.

#### Notes

- Only specify optional fields when they differ from default values.
- Video key mapping standardizes camera names across the entire dataset.
- All indices are zero-based and follow Python's array slicing convention (`[start:end]`).

## Examples

Please refer to the [example dataset](../../demo_data/robot_sim.PickNPlace/) for complete reference.
```