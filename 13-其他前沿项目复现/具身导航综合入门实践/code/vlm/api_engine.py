"""
API VLM 引擎 —— OpenAI 兼容接口（DashScope / Qwen3-VL）
=========================================================
通过 HTTP API 调用远端大模型进行推理。
"""

import cv2
import base64
import numpy as np
from openai import OpenAI

from .base_engine import BaseVLMDecisionEngine


def _image_to_base64(image_rgb: np.ndarray) -> str:
    """RGB ndarray → JPEG base64 字符串（长边缩放到 512px）。"""
    bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    if max(h, w) > 512:
        s = 512 / max(h, w)
        bgr = cv2.resize(bgr, (int(w * s), int(h * s)))
    _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return base64.b64encode(buf).decode("utf-8")


class APIVLMDecisionEngine(BaseVLMDecisionEngine):
    """
    API VLM 决策引擎。
    继承 BaseVLMDecisionEngine，实现 _call_model() 以调用远端 API。
    """

    def __init__(self, config):
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.API_KEY,
            base_url=config.API_BASE_URL,
        )
        self._model = config.API_MODEL_NAME

    def _call_model(self, system_prompt: str, user_text: str, key_images) -> str:
        # 构建多模态 parts
        parts = [{"type": "text", "text": user_text}]
        for i, img in enumerate(key_images[-4:]):
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{_image_to_base64(img)}"},
            })
            parts.append({"type": "text", "text": f"[旋转关键帧 {i + 1}]"})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": parts},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return resp.choices[0].message.content
