"""
VLM 包
=======
提供统一工厂函数 create_vlm_engine()，主函数通过它按模式创建引擎。
"""

from .base_engine import BaseVLMDecisionEngine
from .local_engine import LocalVLMDecisionEngine
from .api_engine import APIVLMDecisionEngine


def create_vlm_engine(config, mode: str = "local") -> BaseVLMDecisionEngine:
    """
    工厂函数：根据 mode 返回对应的 VLM 决策引擎。

    Parameters
    ----------
    config : Config
    mode   : "local" 或 "api"

    Returns
    -------
    BaseVLMDecisionEngine 子类实例
    """
    mode = mode.lower()
    if mode == "local":
        return LocalVLMDecisionEngine(config)
    elif mode == "api":
        return APIVLMDecisionEngine(config)
    else:
        raise ValueError(f"未知 VLM 模式: {mode!r}，请选择 'local' 或 'api'")


__all__ = [
    "BaseVLMDecisionEngine",
    "LocalVLMDecisionEngine",
    "APIVLMDecisionEngine",
    "create_vlm_engine",
]
