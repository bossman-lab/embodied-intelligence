# 1X World Model Challenge

Advancements in video generation may soon enable evaluating robot policies in fully learned world models. An end-to-end learned simulator capable of simulating millions of robot environments would greatly accelerate progress in general robotics and provide useful signals for scaling data and computation.

To accelerate progress in robot learning simulators, we announce the 1X World Model Challenge, tasked with predicting future first-person observations of the [EVE Android](https://www.1x.tech/androids/eve). We provide over 100 hours of vector-quantized image tokens and raw action data collected from operating EVE, a baseline world model (GENIE style), and a frame-level MAGVIT2 autoencoder that compresses images into 16x16 tokens and decodes them back to images.

We hope this dataset will assist robotics researchers who want to experiment in human environments. A sufficiently powerful world model would allow anyone to access a "neuro-simulated EVE". The evaluation challenge is the ultimate goal, and we offer cash prizes for intermediate objectives like good data fitting (compression challenge) and generating realistic videos (sampling challenge).

[Dataset on Huggingface](https://huggingface.co/datasets/1x-technologies/worldmodel)

[Join Discord](https://discord.gg/kk2HmvrQsN)

[Phase 1 Blog](https://www.1x.tech/discover/1x-world-model), [Phase 2 Blog](https://www.1x.tech/discover/1x-world-model-sampling-challenge)

Stay tuned for updates on Phase 2 of the 1X World Model Challenge!

|                                                                               |                                                                               |                                                                               |                                                                               |                                                                               |                                                                                |                                                                               |                                                                               |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset700100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset225100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset775100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset875100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset475100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset725100.gif)  | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset525100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset100.gif)    |
| ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset925100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset975100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset625100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset675100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset400100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset175100.gif)  | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset850100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset100100.gif) |
| ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset125100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset375100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset275100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset800100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset600100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset1000100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset450100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset50100.gif)  |
| ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset250100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset150100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset825100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset950100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset25100.gif)  | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset750100.gif)  | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset650100.gif) | ![til](https://7mlcen.aitianhu6.top/c/assets/v1.0/generated_offset300100.gif) |

## The Challenge

Each example is a sequence of 16 first-person images from the robot at 2Hz frame rate (total 8 seconds). Your goal is to predict the next image given previous images.

- **Compression Challenge ($10k prize)**: Predict the discrete distribution of tokens in the next image.
  - Criteria: First to achieve a **[temporal teacher forcing](https://7mlcen.aitianhu6.top/c/67ccfd05-5854-800c-951e-b434719328e4#metric-details) loss below 8.0** on our private test set.
- **Sampling Challenge ($10k prize)**: Future prediction methods aren't limited to predicting next logits. For example, you can use GANs, diffusion models, and MaskGIT to generate future images. Criteria will be released later.
- **Evaluation Challenge (Coming soon)**: Given a set of N policies, $\pi_1, \pi_2, ... \pi_N$, where each policy $\pi_i(a_t|z_t)$ predicts action tokens from image tokens, can you evaluate all policies in the "world model" $p(z_{t+1}|z_t, a_t)$ and tell us which policies rank best?

These challenges are largely inspired by the [commavq compression challenge](https://github.com/commaai/commavq). Please read the [additional challenge details](https://7mlcen.aitianhu6.top/c/67ccfd05-5854-800c-951e-b434719328e4#additional-challenge-details).

## Getting Started

We require `Python 3.10` or higher. This code has been tested on `Python 3.10.12`.

```
# Install dependencies and download data
./build.sh 

# Activate Python environment
source venv/bin/activate
```

```
conda create -n your_environment_name python=3.10.12
conda activate your_environment_name

# Install dependencies
conda install -c conda-forge accelerate=0.30.1 torchvision=0.18.0 lpips=0.1.4 matplotlib tqdm wandb xformers=0.0.26.post1 wheel packaging ninja einops

# For transformers and torch (ensure compatibility with your CUDA version)
pip install transformers==4.41.0 lightning>2.3.1 git+https://github.com/janEbert/mup.git@fsdp-fix

pip install triton
FLASH_ATTENTION_SKIP_CUDA_BUILD=TRUE python -m pip install flash-attn==2.5.8 --no-build-isolation
huggingface-cli download 1x-technologies/worldmodel --repo-type dataset --local-dir data
```

Requires:
export XFORMERS_FORCE_DISABLE_TRITON=1

## GENIE

This repository provides an implementation of the spatio-temporal transformer and MaskGIT sampler described in [Genie: Generative Interactive Environments](https://arxiv.org/abs/2402.15391). Note that this implementation trains only on video sequences, not actions (though adding actions is straightforward by adding embeddings).

```
# Train GENIE model
python train.py --genie_config genie/configs/magvit_n32_h8_d256.json --output_dir data/genie_model --max_eval_steps 10

# Generate frames from trained model
python genie/generate.py --checkpoint_dir data/genie_model/final_checkpt

# Visualize generated frames
python visualize.py --token_dir data/genie_generated

# Evaluate trained model
python genie/evaluate.py --checkpoint_dir data/genie_model/final_checkpt
```

### 1X GENIE Baselines

We provide two pretrained GENIE models with links in the [leaderboard](https://7mlcen.aitianhu6.top/c/67ccfd05-5854-800c-951e-b434719328e4#leaderboard).

```
# Generate and visualize
output_dir='data/genie_baseline_generated'
for i in {0..240..10}; do
    python genie/generate.py --checkpoint_dir 1x-technologies/GENIE_138M \
        --output_dir $output_dir --example_ind $i --maskgit_steps 2 --temperature 0
    python visualize.py --token_dir $output_dir
    mv $output_dir/generated_offset0.gif $output_dir/example_$i.gif
    mv $output_dir/generated_comic_offset0.png $output_dir/example_$i.png
done

# Evaluate
python genie/evaluate.py --checkpoint_dir 1x-technologies/GENIE_138M --maskgit_steps 2
```

## Data Description

[Please see the dataset card on Huggingface](https://huggingface.co/datasets/1x-technologies/worldmodel).

The training dataset is stored in the `data/train_v1.1` directory.

## Participating in the Challenge:

Please first read the [additional challenge details](https://7mlcen.aitianhu6.top/c/67ccfd05-5854-800c-951e-b434719328e4#additional-challenge-details) to understand the rules.

Send source code + build script + some information about your method to [challenge@1x.tech](mailto:challenge@1x.tech). We will evaluate your submission on our held-out dataset and reply with results via email.

Please send us the following:

- Your chosen username (can be your real name or pseudonym, will be linked one-to-one with email)
- Source code as a .zip file
- Approximate FLOP count used when training your model
- Any external data used when training your model
- Your evaluation performance on the provided validation set (so we have a rough idea of your model's expected performance)

After manual review of your code, we run evaluation in a 22.04 + CUDA 12.3 sandbox environment with:

```
./build.sh # Install required dependencies and model weights
./evaluate.py --val_data_dir <PATH-TO-HELD-OUT-DATA>  # Run your model on held-out dataset
```

## Additional Challenge Details

1. We have provided `magvit2.ckpt`, weights for a [MAGVIT2](https://github.com/TencentARC/Open-MAGVIT2) encoder/decoder. This encoder allows you to tokenize external data to help improve metrics.
2. Unlike LLMs, loss metrics are not standard because of the image token vocabulary size, which changed when v1.0 was released (July 8, 2024). Instead of computing cross-entropy loss on logits with 2^18 classes, we compute cross-entropy on predictions for 2x 2^9 classes and sum them. The reason for this is that large vocabulary sizes (2^18) make storing a logit tensor of shape `(B, 2^18, T, 16, 16)` very memory-intensive. Therefore, the compression challenge considers factorized PMFs of model families with the form: p(x1, x2) = p(x1)p(x2). For sampling and evaluation challenges, factorized PMFs are a necessary criterion.
3. For the compression challenge, we intentionally chose to evaluate held-out data with a fixed factorized distribution p(x1, x2) = p(x1)p(x2) during training. While unfactorized models (like p(x1, x2) = f(x1, x2)) should achieve lower cross-entropy on test data by utilizing off-diagonal terms of x1 and x2 covariance, we want to encourage solutions that achieve lower loss while keeping the factorization fixed.
4. For the compression challenge, submissions may only use actions *before* the current prompt frame. Submissions may autoregressively predict subsequent actions to improve performance, but these actions will not be provided with the prompt.
5. Naive nearest neighbor retrieval + finding next frames from the training set will achieve reasonably good loss and sampling results on the development validation set because there are similar sequences in the training set. However, we explicitly prohibit such solutions (the private test set will penalize them).
6. We cannot award individuals from US-sanctioned countries if it violates the spirit of the challenge. We reserve the right not to award prizes in the challenge.

### Metric Details

Evaluation scenarios have different criteria depending on the degree of real context provided to the model.
In decreasing order of context, these scenarios are:

- **Full autoregressive**: Model receives a predetermined number of real frames and autoregressively predicts all remaining frames.
- **Temporal teacher forcing**: Model receives all real frames before the current frame and autoregressively predicts all tokens of the current frame.
- **Full teacher forcing**: Model receives all real tokens before the current frame, including tokens in the current frame. Only applicable to causal LMs.

For example, consider predicting the final token of a video, located at the bottom-right corner of frame 15.
In each scenario, the context received by the model is:

- Full autoregressive: The first $t$ 16x16 tokens are real tokens from the first $t$ frames, remaining tokens are autoregressively generated, with $0 < t < 15$ being the predetermined number of prompt frames.
- Temporal teacher forcing: The first 15 16x16 tokens are real tokens from the first 15 frames, remaining tokens are autoregressively generated.
- Full teacher forcing: All previous (16x16x16 - 1) tokens are real tokens.

The compression challenge uses the "temporal teacher forcing" scenario.

## Leaderboard

These are evaluation results on `data/val_v1.1`.

## Help Us Improve the Challenge!

Beyond the world model challenge, we want to make the challenge and dataset more useful for *your* research questions. Want more data with human interaction? More safety-critical tasks like carefully carrying hot coffee cups? More intricate tool use? Robots collaborating with other robots? Robots dressing themselves in front of mirrors? Think of 1X as an operations team for acquiring high-quality human-like data across extremely diverse scenarios.

Please send your data needs (and why you think they're important) to [challenge@1x.tech](mailto:challenge@1x.tech), and we'll try to incorporate them into future data releases. You can also discuss your data needs with the community on [Discord](https://discord.gg/UMnzbTkw).

We also welcome donors to help us increase the prize pool.

## Citation

If you use this software or dataset in your work, please use the "Cite this repository" button on Github for citation.

## Changelog

- v1.1 - Released compression challenge criteria; removed paused and discontinuous videos from dataset; higher image cropping.
- v1.0 - More efficient MAGVIT2 tokenizer using 16x16 (C=2^18) mapping to 256x256 images, with raw action data provided.
- v0.0.1 - Initial challenge release with 20x20 (C=1000) image tokenizer mapping to 160x160 images.