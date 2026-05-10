"""
Configuration management for video2robot
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
THIRD_PARTY_DIR = PROJECT_ROOT / "third_party"
DATA_DIR = PROJECT_ROOT / "data"
CONFIGS_DIR = PROJECT_ROOT / "configs"

# Third-party paths
PROMPTHMR_DIR = THIRD_PARTY_DIR / "PromptHMR"
GMR_DIR = THIRD_PARTY_DIR / "GMR"

# Model paths (PromptHMR)
PROMPTHMR_CHECKPOINT_DIR = PROMPTHMR_DIR / "data" / "pretrain"
PROMPTHMR_BODY_MODELS_DIR = PROMPTHMR_DIR / "data" / "body_models"

# Model paths (GMR)
# GMR expects a body-model root containing subfolders like `smplx/`.
# Reuse PromptHMR's downloaded body models by default.
GMR_BODY_MODELS_DIR = PROMPTHMR_BODY_MODELS_DIR


@dataclass
class VeoConfig:
    """Veo video generation config"""
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GOOGLE_API_KEY"))
    model_id: str = "veo-3.1-fast-generate-preview"
    aspect_ratio: str = "16:9"
    duration_seconds: int = 8
    seed: Optional[int] = None
    negative_prompt: Optional[str] = None
    resolution: Optional[str] = None  # "720p" or "1080p"
    person_generation: str = "allow_all"
    poll_interval: int = 10
    max_wait_time: int = 600


@dataclass
class SoraConfig:
    """Sora video generation config"""
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    model_id: str = "sora-2"  # "sora-2" (fast) or "sora-2-pro" (quality)
    size: str = "1280x720"  # "720x1280", "1280x720", "1024x1792", "1792x1024"
    duration_seconds: int = 8  # 4, 8, or 12
    poll_interval: float = 5.0
    max_wait_time: float = 600.0


@dataclass
class SeedanceConfig:
    """Seedance video generation config"""
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("SEEDANCE_API_KEY"))
    base_url: str = "https://seedanceapi.org/v1"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    duration_seconds: int = 8
    poll_interval: int = 10
    max_wait_time: int = 600


@dataclass
class PoseConfig:
    """Pose extraction config"""
    # PromptHMR settings
    static_camera: bool = False
    max_height: int = 896
    max_fps: int = 60
    tracker: str = "sam2"  # "bytetrack" or "sam2"
    run_post_opt: bool = True


@dataclass
class RobotConfig:
    """Robot retargeting config"""
    robot_type: str = "unitree_g1"
    target_fps: int = 30
    visualize: bool = False
    record_video: bool = False


@dataclass
class PipelineConfig:
    """Full pipeline config"""
    veo: VeoConfig = field(default_factory=VeoConfig)
    sora: SoraConfig = field(default_factory=SoraConfig)
    seedance: SeedanceConfig = field(default_factory=SeedanceConfig)
    pose: PoseConfig = field(default_factory=PoseConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)

    # Output settings
    output_dir: Path = field(default_factory=lambda: DATA_DIR)
    save_intermediate: bool = True


def get_default_config() -> PipelineConfig:
    """Get default pipeline configuration"""
    return PipelineConfig()


def ensure_paths():
    """Ensure required directories exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check third-party dependencies
    if not PROMPTHMR_DIR.exists():
        print(f"[Warning] PromptHMR not found: {PROMPTHMR_DIR}")
    if not GMR_DIR.exists():
        print(f"[Warning] GMR not found: {GMR_DIR}")

