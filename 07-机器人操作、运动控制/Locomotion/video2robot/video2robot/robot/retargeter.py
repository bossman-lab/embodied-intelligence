"""
Robot motion retargeting using GMR

Converts SMPL-X motion to robot joint angles
"""

from __future__ import annotations

import sys
import pickle
import numpy as np
from pathlib import Path
from typing import Union, Optional

from video2robot.config import GMR_DIR, GMR_BODY_MODELS_DIR
from video2robot.utils import emit_progress


# Supported robots
SUPPORTED_ROBOTS = [
    "unitree_g1",
    "unitree_g1_with_hands",
    "unitree_h1",
    "unitree_h1_2",
    "booster_t1",
    "booster_t1_29dof",
    "booster_k1",
    "stanford_toddy",
    "fourier_n1",
    "engineai_pm01",
    "kuavo_s45",
    "hightorque_hi",
    "galaxea_r1pro",
]


class RobotRetargeter:
    """Robot motion retargeter using GMR"""

    def __init__(
        self,
        robot_type: str = "unitree_g1",
        smplx_model_path: Optional[str] = None,
    ):
        """
        Initialize robot retargeter

        Args:
            robot_type: Target robot type
            smplx_model_path: Path to SMPL-X body models
        """
        if robot_type not in SUPPORTED_ROBOTS:
            raise ValueError(f"Unsupported robot: {robot_type}. Choose from {SUPPORTED_ROBOTS}")

        self.robot_type = robot_type
        self.smplx_model_path = smplx_model_path or str(GMR_BODY_MODELS_DIR)
        
        self._gmr = None
        self._initialized = False

    def _init_gmr(self):
        """Initialize GMR (lazy loading)"""
        if self._initialized:
            return

        # Add GMR to path
        if str(GMR_DIR) not in sys.path:
            sys.path.insert(0, str(GMR_DIR))

        try:
            from general_motion_retargeting import GeneralMotionRetargeting
            from general_motion_retargeting.utils.smpl import load_smplx_file, get_smplx_data_offline_fast
            
            self._GMR = GeneralMotionRetargeting
            self._load_smplx_file = load_smplx_file
            self._get_smplx_data_offline_fast = get_smplx_data_offline_fast
            self._initialized = True
            print(f"[RobotRetargeter] GMR initialized for {self.robot_type}")
        except ImportError as e:
            raise ImportError(
                f"Failed to import GMR. Make sure it's installed at {GMR_DIR}\n"
                f"Error: {e}"
            )

    def retarget(
        self,
        smplx_path: Union[str, Path],
        output_path: Union[str, Path],
        robot_type: Optional[str] = None,
        target_fps: int = 30,
        visualize: bool = False,
    ) -> Path:
        """
        Retarget SMPL-X motion to robot

        Args:
            smplx_path: Input SMPL-X .npz file
            output_path: Output robot motion .pkl file
            robot_type: Target robot (uses default if None)
            target_fps: Target FPS (0 = use original)
            visualize: Show MuJoCo visualization

        Returns:
            Path to output file
        """
        self._init_gmr()

        smplx_path = Path(smplx_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        robot_type = robot_type or self.robot_type

        print(f"[RobotRetargeter] Input: {smplx_path}")
        print(f"[RobotRetargeter] Robot: {robot_type}")
        emit_progress("loading", 0.05, "Loading SMPL-X")

        # Load SMPL-X data
        smplx_data, body_model, smplx_output, human_height = self._load_smplx_file(
            str(smplx_path), self.smplx_model_path
        )
        print(f"[RobotRetargeter] Human height: {human_height:.2f}m")

        # Get original FPS
        original_fps = float(smplx_data.get("mocap_frame_rate", 30))
        use_fps = original_fps if target_fps == 0 else target_fps

        # Align to target FPS
        smplx_frames, aligned_fps = self._get_smplx_data_offline_fast(
            smplx_data, body_model, smplx_output, tgt_fps=use_fps
        )
        print(f"[RobotRetargeter] Frames: {len(smplx_frames)}, FPS: {aligned_fps}")

        # Initialize GMR
        gmr = self._GMR(
            actual_human_height=human_height,
            src_human="smplx",
            tgt_robot=robot_type,
            verbose=False,
        )

        # Visualization (optional)
        robot_viewer = None
        if visualize:
            from general_motion_retargeting import RobotMotionViewer
            robot_viewer = RobotMotionViewer(
                robot_type=robot_type,
                motion_fps=aligned_fps,
            )

        # Retarget each frame
        num_frames = len(smplx_frames)
        print(f"[RobotRetargeter] Retargeting {num_frames} frames...")
        emit_progress("retarget", 0.15, f"Retargeting {num_frames} frames", frames=f"0/{num_frames}")
        qpos_list = []

        for i, frame_data in enumerate(smplx_frames):
            qpos = gmr.retarget(frame_data)
            qpos_list.append(qpos)

            if robot_viewer:
                robot_viewer.step(
                    root_pos=qpos[:3],
                    root_rot=qpos[3:7],
                    dof_pos=qpos[7:],
                    human_motion_data=gmr.scaled_human_data,
                )

            # Emit progress every 10 frames or on last frame
            if (i + 1) % 10 == 0 or i == num_frames - 1:
                # Progress: 0.15 to 0.85 based on frame progress
                ratio = (i + 1) / num_frames
                progress = 0.15 + 0.70 * ratio
                emit_progress("retarget", progress, f"Frame {i + 1}/{num_frames}", frames=f"{i + 1}/{num_frames}")

            if (i + 1) % 100 == 0:
                print(f"[RobotRetargeter] Processed {i + 1}/{num_frames}")

        if robot_viewer:
            robot_viewer.close()

        # Build output
        robot_motion = self._build_robot_motion(
            qpos_list, gmr, robot_type, human_height, aligned_fps
        )

        # Save
        emit_progress("saving", 0.88, "Saving robot motion")
        with open(output_path, "wb") as f:
            pickle.dump(robot_motion, f)

        print(f"[RobotRetargeter] Saved: {output_path}")
        print(f"[RobotRetargeter] root_pos: {robot_motion['root_pos'].shape}")
        print(f"[RobotRetargeter] dof_pos: {robot_motion['dof_pos'].shape}")

        return output_path

    def _build_robot_motion(
        self,
        qpos_list: list,
        gmr,
        robot_type: str,
        human_height: float,
        fps: float,
    ) -> dict:
        """Build robot motion dictionary"""
        import torch
        from general_motion_retargeting.kinematics_model import KinematicsModel

        # Parse qpos
        root_pos = np.array([qpos[:3] for qpos in qpos_list])
        root_rot = np.array([qpos[3:7][[1, 2, 3, 0]] for qpos in qpos_list])  # wxyz -> xyzw
        dof_pos = np.array([qpos[7:] for qpos in qpos_list])

        # Compute local_body_pos (forward kinematics)
        device = torch.device("cpu")
        kin_model = KinematicsModel(gmr.xml_file, device=device)

        num_frames = dof_pos.shape[0]
        fk_root_pos = torch.zeros((num_frames, 3), device=device)
        fk_root_rot = torch.zeros((num_frames, 4), device=device)
        fk_root_rot[:, -1] = 1.0  # identity quaternion

        local_body_pos, _ = kin_model.forward_kinematics(
            fk_root_pos,
            fk_root_rot,
            torch.from_numpy(dof_pos).float()
        )
        local_body_pos = local_body_pos.numpy()

        # Height adjustment
        body_pos, _ = kin_model.forward_kinematics(
            torch.from_numpy(root_pos).float(),
            torch.from_numpy(root_rot).float(),
            torch.from_numpy(dof_pos).float()
        )
        lowest = torch.min(body_pos[..., 2]).item()
        root_pos[:, 2] -= lowest

        return {
            "fps": fps,
            "robot_type": robot_type,
            "num_frames": num_frames,
            "human_height": human_height,
            "root_pos": root_pos.astype(np.float32),
            "root_rot": root_rot.astype(np.float32),
            "dof_pos": dof_pos.astype(np.float32),
            "local_body_pos": local_body_pos.astype(np.float32),
            "link_body_list": kin_model.body_names,
        }

    @staticmethod
    def get_supported_robots() -> list:
        """Get list of supported robots"""
        return SUPPORTED_ROBOTS.copy()

