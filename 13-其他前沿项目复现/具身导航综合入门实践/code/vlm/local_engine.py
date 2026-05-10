"""
本地 VLM 引擎 —— Qwen3-VL
===========================
使用本地加载的 Qwen3VL 模型进行推理。
"""

import torch
import numpy as np
from PIL import Image
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

from .base_engine import BaseVLMDecisionEngine


class LocalQwen3VLEngine:
    """
    封装本地 Qwen3-VL 模型推理（底层推理器）。
    由 LocalVLMDecisionEngine 持有，不直接暴露给导航器。
    """

    def __init__(self, model_name: str, device_map: str = "auto",
                 dtype: str = "auto", max_new_tokens: int = 1024):
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens

        # 自动选择精度
        if dtype == "auto":
            if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8:
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        elif dtype == "bf16":
            torch_dtype = torch.bfloat16
        elif dtype == "fp16":
            torch_dtype = torch.float16
        else:
            torch_dtype = torch.float32

        print(f"正在加载本地模型: {model_name}")
        print(f"数据类型: {torch_dtype}  设备: {device_map}")

        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map=device_map,
            attn_implementation="sdpa",
        )
        self.processor = AutoProcessor.from_pretrained(model_name)
        print("本地模型加载完成！")

    def infer_messages(self, system_prompt: str, user_text: str,
                       pil_images=None, max_new_tokens: int = None,
                       temperature: float = 0.3, top_p: float = 0.9,
                       top_k: int = 50) -> str:
        if pil_images is None:
            pil_images = []
        if max_new_tokens is None:
            max_new_tokens = self.max_new_tokens

        messages = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
        user_content = [{"type": "image", "image": img} for img in pil_images]
        user_content.append({"type": "text", "text": user_text})
        messages.append({"role": "user", "content": user_content})

        inputs = self.processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        )
        inputs.pop("token_type_ids", None)
        inputs = inputs.to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=temperature > 0,
            )

        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
        ]
        return self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]


class LocalVLMDecisionEngine(BaseVLMDecisionEngine):
    """
    本地 VLM 决策引擎。
    继承 BaseVLMDecisionEngine，实现 _call_model() 以调用本地 Qwen3-VL。
    """

    def __init__(self, config):
        super().__init__(config)
        self._engine = LocalQwen3VLEngine(
            model_name=config.LOCAL_MODEL_NAME,
            device_map=config.MODEL_DEVICE_MAP,
            dtype=config.MODEL_DTYPE,
            max_new_tokens=config.MODEL_MAX_NEW_TOKENS,
        )

    def _call_model(self, system_prompt: str, user_text: str, key_images) -> str:
        pil_images = []
        for img in key_images[-4:]:
            if isinstance(img, np.ndarray):
                pil_images.append(Image.fromarray(img.astype(np.uint8)))

        return self._engine.infer_messages(
            system_prompt=system_prompt,
            user_text=user_text,
            pil_images=pil_images,
            max_new_tokens=self.cfg.MODEL_MAX_NEW_TOKENS,
            temperature=self.cfg.MODEL_TEMPERATURE,
            top_p=self.cfg.MODEL_TOP_P,
            top_k=self.cfg.MODEL_TOP_K,
        )
