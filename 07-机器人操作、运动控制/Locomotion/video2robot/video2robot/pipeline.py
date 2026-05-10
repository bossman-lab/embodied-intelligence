"""video2robot pipeline (programmatic API).

Note:
- This `Pipeline` calls Veo/PromptHMR/GMR directly in the **current Python environment**.
- If you run PromptHMR (phmr) and GMR (gmr) in separate conda envs,
  we recommend using `scripts/run_pipeline.py` which handles env switching automatically.

Example:
    from video2robot import Pipeline

    pipeline = Pipeline()
    result = pipeline.run(prompt="Full body video of a person walking", robot_type="unitree_g1")
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .config import PipelineConfig, get_default_config, ensure_paths
from .pose.extractor import PoseExtractor
from .robot.retargeter import RobotRetargeter
from .video.veo_client import VeoClient
from .video.sora_client import SoraClient


class Pipeline:
    """Video → Human (SMPL-X) → Robot motion pipeline."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or get_default_config()
        ensure_paths()

        self._veo_client: Optional[VeoClient] = None
        self._sora_client: Optional[SoraClient] = None
        self._pose_extractor: Optional[PoseExtractor] = None
        self._robot_retargeter: Optional[RobotRetargeter] = None

    @property
    def veo_client(self) -> VeoClient:
        if self._veo_client is None:
            self._veo_client = VeoClient(
                api_key=self.config.veo.api_key,
                model_id=self.config.veo.model_id,
            )
        return self._veo_client

    @property
    def sora_client(self) -> SoraClient:
        if self._sora_client is None:
            self._sora_client = SoraClient(
                api_key=self.config.sora.api_key,
                model_id=self.config.sora.model_id,
            )
        return self._sora_client

    @property
    def pose_extractor(self) -> PoseExtractor:
        if self._pose_extractor is None:
            self._pose_extractor = PoseExtractor(
                static_camera=self.config.pose.static_camera,
            )
        return self._pose_extractor

    @property
    def robot_retargeter(self) -> RobotRetargeter:
        if self._robot_retargeter is None:
            self._robot_retargeter = RobotRetargeter(
                robot_type=self.config.robot.robot_type,
            )
        return self._robot_retargeter

    def _get_project_dir(self, name: Optional[str] = None) -> Path:
        """Get or create project directory."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if name:
            project_dir = output_dir / name
            project_dir.mkdir(parents=True, exist_ok=True)
            return project_dir

        existing = list(output_dir.glob("video_*"))
        if not existing:
            num = 1
        else:
            nums: list[int] = []
            for d in existing:
                try:
                    nums.append(int(d.name.split("_")[-1]))
                except ValueError:
                    continue
            num = max(nums) + 1 if nums else 1

        project_dir = output_dir / f"video_{num:03d}"
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _save_metadata(self, project_dir: Path, prompt: str):
        """Save generation metadata to config.json."""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "prompt": prompt,
            "veo": {
                "model_id": self.config.veo.model_id,
                "aspect_ratio": self.config.veo.aspect_ratio,
                "duration_seconds": self.config.veo.duration_seconds,
                "seed": self.config.veo.seed,
                "negative_prompt": self.config.veo.negative_prompt,
                "resolution": self.config.veo.resolution,
                "person_generation": self.config.veo.person_generation,
            },
            "pose": {
                "static_camera": self.config.pose.static_camera,
                "tracker": self.config.pose.tracker,
                "run_post_opt": self.config.pose.run_post_opt,
            },
            "robot": {
                "robot_type": self.config.robot.robot_type,
                "target_fps": self.config.robot.target_fps,
            },
        }
        with open(project_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def run(
        self,
        *,
        prompt: Optional[str] = None,
        video: Optional[Union[str, Path]] = None,
        smplx: Optional[Union[str, Path]] = None,
        name: Optional[str] = None,
        robot_type: Optional[str] = None,
        skip_veo: bool = False,
        skip_pose: bool = False,
        skip_robot: bool = False,
    ) -> dict:
        """Run the pipeline.

        Args:
            prompt: Veo text prompt
            video: Existing video path
            smplx: Existing SMPL-X (npz) path
            name: Project folder name
            robot_type: Target robot type
            skip_veo/skip_pose/skip_robot: Skip individual steps
        """
        if not prompt and not video and not smplx:
            raise ValueError("Provide prompt, video, or smplx path")

        project_dir = self._get_project_dir(name)
        robot_type = robot_type or self.config.robot.robot_type

        out = {
            "project_dir": project_dir,
            "video_path": None,
            "smplx_path": None,
            "robot_motion_path": None,
        }

        video_path = project_dir / "original.mp4"
        smplx_path = project_dir / "smplx.npz"
        robot_path = project_dir / "robot_motion.pkl"

        # Step 1: video
        if prompt and not skip_veo:
            self.veo_client.generate(
                prompt=prompt,
                output_path=str(video_path),
                aspect_ratio=self.config.veo.aspect_ratio,
                duration_seconds=self.config.veo.duration_seconds,
                seed=self.config.veo.seed,
                negative_prompt=self.config.veo.negative_prompt,
                resolution=self.config.veo.resolution,
                person_generation=self.config.veo.person_generation,
                poll_interval=self.config.veo.poll_interval,
                max_wait_time=self.config.veo.max_wait_time,
            )
            out["video_path"] = video_path
            self._save_metadata(project_dir, prompt)

        elif video:
            src = Path(video)
            if not src.exists():
                raise FileNotFoundError(f"Video not found: {src}")
            if src.resolve() != video_path.resolve():
                shutil.copy(src, video_path)
            out["video_path"] = video_path

        # Step 2: pose
        if not skip_pose and not smplx:
            if out["video_path"] is None:
                raise ValueError("No video for pose extraction")
            self.pose_extractor.extract(
                video_path=out["video_path"],
                output_path=smplx_path,
                output_dir=project_dir,
            )
            out["smplx_path"] = smplx_path
        elif smplx:
            src = Path(smplx)
            if not src.exists():
                raise FileNotFoundError(f"SMPL-X not found: {src}")
            if src.resolve() != smplx_path.resolve():
                shutil.copy(src, smplx_path)
            out["smplx_path"] = smplx_path

        # Step 3: robot
        if not skip_robot:
            if out["smplx_path"] is None:
                raise ValueError("No SMPL-X data for robot retargeting")
            self.robot_retargeter.retarget(
                smplx_path=out["smplx_path"],
                output_path=robot_path,
                robot_type=robot_type,
                target_fps=self.config.robot.target_fps,
                visualize=self.config.robot.visualize,
            )
            out["robot_motion_path"] = robot_path

        return out
