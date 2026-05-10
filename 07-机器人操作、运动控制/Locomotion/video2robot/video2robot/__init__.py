"""
video2robot - Video to Robot Motion Pipeline

End-to-end pipeline: Video (or Prompt) → Human Pose Extraction → Robot Motion Conversion
"""

__version__ = "0.1.0"

__all__ = ["Pipeline", "VeoClient", "PoseExtractor", "RobotRetargeter"]


def __getattr__(name: str):
    if name == "Pipeline":
        from .pipeline import Pipeline

        return Pipeline
    if name == "VeoClient":
        from .video.veo_client import VeoClient

        return VeoClient
    if name == "PoseExtractor":
        from .pose.extractor import PoseExtractor

        return PoseExtractor
    if name == "RobotRetargeter":
        from .robot.retargeter import RobotRetargeter

        return RobotRetargeter
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + __all__)

