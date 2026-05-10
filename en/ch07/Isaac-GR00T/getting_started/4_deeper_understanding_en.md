# Deeper Understanding

In this section, we will explore training configuration options in depth. We will also explain implementation tags, modality configurations, data transformations, and more in detail.

## Implementing Action Head Fine-tuning

GR00T is designed with dedicated action heads to work with different types of robots (embodiments). When fine-tuning, you need to specify which embodiment head to train based on your dataset:

1. **Embodiment Tags**
   - Each dataset must be tagged with a specific `EmbodimentTag` (e.g., EmbodimentTag.GR1_UNIFIED) when instantiating the `LeRobotSingleDataset` class
   - A comprehensive list of embodiment tags can be found in `gr00t/data/embodiment_tags.py`
   - This tag determines which action head will be fine-tuned
   - If you have a new embodiment, you can use the `EmbodimentTag.NEW_EMBODIMENT` tag (e.g., `new_embodiment.your_custom_dataset`)

2. **How It Works**
   - When you load a dataset with a specific embodiment tag (e.g., `EmbodimentTag.GR1_UNIFIED`)
   - The model has multiple components that can be configured for fine-tuning (visual encoder, language model, DiT, etc.)
   - Specifically for action heads, only the head corresponding to your specified embodiment tag will be fine-tuned. Other embodiment-specific action heads remain frozen

## Advanced Tuning Parameters

### Model Components

The model has several components that can be fine-tuned independently. You can configure these parameters in the `GR00T_N1.from_pretrained` function.

1. **Visual Encoder** (`tune_visual`)
   - Set to `true` if your data has visually distinct characteristics from pre-trained data
   - Note: This is computationally expensive
   - Default: false

2. **Language Model** (`tune_llm`)
   - Set to `true` only if you have domain-specific language significantly different from standard instructions
   - In most cases, should be `false`
   - Default: false

3. **Projector** (`tune_projector`)
   - By default, the projector is tuned
   - This helps align action and state spaces for specific embodiments

4. **Diffusion Model** (`tune_diffusion_model`)
   - By default, the diffusion model is not tuned
   - This is the action head shared across all embodiment projectors

### Understanding Data Transformations

This document explains the different types of transformations used in our data processing pipeline. There are four main categories of transformations:

#### 1. Video Transformations

Video transformations are applied to video data to prepare it for model training. Based on our experimental evaluation, the following combination of video transformations works best:

- **VideoToTensor**: Converts video data from its raw format to PyTorch tensors for processing.
- **VideoCrop**: Crops video frames using a scale factor of 0.95 in random mode to introduce minor variations.
- **VideoResize**: Resizes video frames to standard size (224x224 pixels) using linear interpolation.
- **VideoColorJitter**: Applies color augmentation by randomly adjusting brightness (±0.3), contrast (±0.4), saturation (±0.5), and hue (±0.08).
- **VideoToNumpy**: Converts processed tensors back to NumPy arrays for further processing.

#### 2. State Transformations

State transformations process robot state information:

- **StateActionToTensor**: Converts state data (e.g., arm positions, hand configurations) to PyTorch tensors.
- **StateActionTransform**: Applies normalization to state data. Different normalization modes are used based on modality keys. You can find the transformation logic in the [state_action.py](../gr00t/data/transform/state_action.py) file.

#### 3. Action Transformations

Action transformations process robot action data:

- **StateActionToTensor**: Similar to state transformations, converts action data to PyTorch tensors.
- **StateActionTransform**: Applies normalization to action data. Like state data, min-max normalization is used to standardize action values for left/right arms, hands, and waist.

#### 4. Concatenation Transformations

**ConcatTransform** combines processed data into unified arrays:

- It concatenates video data according to the specified video modality key order.
- It concatenates state data according to the specified state modality key order.
- It concatenates action data according to the specified action modality key order.

This concatenation step is crucial as it prepares data in the format expected by the model, ensuring all modalities are properly aligned and ready for training or inference.

#### 5. GR00T Transform

**GR00TTransform** is a custom transform used to prepare data for the model. It is applied at the end of the data pipeline.

- It pads data to the maximum sequence length in the batch.
- It creates a dictionary with modality keys as keys and processed data as values.

In practice, you typically won't need to modify this transform much, if at all.

### Lerobot Dataset Compatibility

More details about GR00T-compatible lerobot datasets can be found in the [LeRobot_compatible_data_schema.md](./LeRobot_compatible_data_schema.md) file.