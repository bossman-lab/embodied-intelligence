要使用 Xget 下载 Hugging Face (HF) 的数据集和模型，主要有两种方法：

### 方法一：直接转换 URL 进行下载（适用于命令行工具）

这种方法非常适合需要直接下载某个特定的模型或数据集文件时。你只需要遵循一个简单的规则：在原始的 Hugging Face URL 前面加上 Xget 的域名和 `/hf` 前缀。

**转换规则：**

* **原始 URL**: `https://huggingface.co/...`
* **加速 URL**: `https://xget.xi-xu.me/hf/...`

**示例：**

1. **下载模型文件**
   * **原始 URL**:
     ```
     https://huggingface.co/microsoft/DialoGPT-medium/resolve/main/pytorch_model.bin
     ```
   * **使用 Xget 加速后的 URL**:
     ```
     https://xget.xi-xu.me/hf/microsoft/DialoGPT-medium/resolve/main/pytorch_model.bin
     ```
2. **下载数据集文件**
   * **原始 URL**:
     ```
     https://huggingface.co/datasets/rajpurkar/squad/resolve/main/plain_text/train-00000-of-00001.parquet
     ```
   * **使用 Xget 加速后的 URL**:
     ```
     https://xget.xi-xu.me/hf/datasets/rajpurkar/squad/resolve/main/plain_text/train-00000-of-00001.parquet
     ```

你可以将转换后的 URL 直接粘贴到浏览器，或者使用 `wget`、`curl`、`aria2` 等命令行下载工具进行下载。文档中特别推荐使用 `aria2` 进行多线程下载以获得最佳速度：

**Bash**

```
# 使用 aria2 以 16 个线程下载大模型文件
aria2c -x 16 -s 16 https://xget.xi-xu.me/hf/microsoft/DialoGPT-large/resolve/main/pytorch_model.bin
```

### 方法二：在 Python 代码中集成（推荐）

如果你在 Python 项目中使用 `transformers` 或 `datasets` 这样的库，最方便的方法是配置环境变量，让这些库自动通过 Xget 下载资源。

**核心步骤：**

通过设置 `HF_ENDPOINT` 环境变量，将所有对 Hugging Face Hub 的请求指向 Xget 镜像。

**示例 Python 代码：**

下面的代码演示了如何在加载模型前设置环境变量，`transformers` 库会自动使用 Xget 进行下载。

**Python**

```
import os
from transformers import AutoTokenizer, AutoModelForCausalLM

# 关键步骤：设置环境变量，让 transformers 库自动使用 Xget 镜像
os.environ['HF_ENDPOINT'] = 'https://xget.xi-xu.me/hf'

# 像往常一样定义模型名称
model_name = 'microsoft/DialoGPT-medium'

print(f"正在从 Xget 镜像下载模型: {model_name}")

# 使用 from_pretrained 方法加载模型和分词器
# 由于设置了环境变量，代码无需任何其他修改
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

print("模型和分词器加载成功！")

# 接下来就可以正常使用模型了
# chat_history_ids = model.generate(...)
```

**总结一下：**

* **临时下载单个文件**：手动转换 URL，使用下载工具下载。
* **在 Python 项目中长期使用**：在代码开头设置 `HF_ENDPOINT` 环境变量，即可让 Hugging Face 相关库自动享受加速效果，无需更改后续代码。
