#!/usr/bin/env python3
"""
Register the GEN72-EG2 robot into ManiSkill environments.

This script registers the custom GEN72-EG2 robot, configures its physical
properties and control parameters, and makes it available in ManiSkill—
in particular for the stable PPO implementation.
"""
import os
import sys
import numpy as np
# torch is imported only when training starts; optional during registration
try:
    import torch
except ImportError:
    print("Warning: torch not installed (only needed for training)")

import sapien
from copy import deepcopy

# Ensure ManiSkill modules are importable
ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.append(ROOT_DIR)

from mani_skill.agents.base_agent import BaseAgent, Keyframe
from mani_skill.agents.controllers import *
from mani_skill.agents.registration import register_agent
from mani_skill.utils import common, sapien_utils
from mani_skill.utils.structs.actor import Actor

# Update this path to your actual URDF file
URDF_PATH = "/home/kewei/17robo/ManiSkill/urdf_01/GEN72-EG2.urdf"

# On first registration you may see warnings about missing links
# (e.g., “4C2_baselink”). Edit the URDF or check joint/link definitions if needed.

@register_agent()
class GEN72EG2Robot(BaseAgent):
    """
    GEN72-EG2 robot: 7-DoF arm + EG2 gripper
    """
    uid = "gen72_eg2_robot"
    urdf_path = URDF_PATH

    # Gripper friction for stable grasping
    urdf_config = dict(
        _materials=dict(
            gripper=dict(static_friction=2.0, dynamic_friction=2.0, restitution=0.0)
        ),
        link={
            "Link7":      dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link2":  dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link3":  dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
        },
    )

    # Joint names extracted from the URDF
    arm_joint_names     = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "joint7"]
    gripper_joint_names = ["4C2_Joint1", "4C2_Joint2", "4C2_Joint3", "4C2_Joint5"]

    ee_link_name = "Link7"
    tcp_link_name = "Link7"  # Tool-Center-Point

    # Controller gains tuned for stability
    arm_stiffness  = 1e3
    arm_damping    = 1e2
    arm_force_limit = 100

    gripper_stiffness  = 1e3
    gripper_damping    = 1e2
    gripper_force_limit = 100

    # Keyframes optimized for block-pushing
    keyframes = dict(
        rest=Keyframe(
            qpos=np.array([
                0, -0.1, 0, -1.5, 0, 1.8, 0.8,      # arm (natural, slightly drooping)
                0.04, 0.04, 0.04, 0.04                # gripper open
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),  # 180° yaw + 0.2 m forward
        ),
        push_ready=Keyframe(
            qpos=np.array([
                0, 0.2, 0, -1.2, 0, 1.6, 0.0,
                0.04, 0.04, 0.04, 0.04
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        ),
        grasp_ready=Keyframe(
            qpos=np.array([
                0, 0.1, 0, -1.0, 0, 1.2, 0.0,
                0.04, 0.04, 0.04, 0.04
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        ),
        grasp_close=Keyframe(
            qpos=np.array([
                0, 0.1, 0, -1.0, 0, 1.2, 0.0,
                0.0, 0.0, 0.0, 0.0                      # gripper closed
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        )
    )

    def initialize(self, engine, scene):
        super().initialize(engine, scene)
        # Cache TCP link
        self._tcp_link = None
        for link in self.robot.get_links():
            if link.name == self.tcp_link_name:
                self._tcp_link = link
                break
        if self._tcp_link is None:
            raise ValueError(f"TCP link {self.tcp_link_name} not found")

    @property
    def tcp(self):
        """Return the TCP Actor."""
        if not hasattr(self, '_tcp_link') or self._tcp_link is None:
            for link in self.robot.get_links():
                if link.name == self.tcp_link_name:
                    self._tcp_link = link
                    break
        return self._tcp_link

    @property
    def _controller_configs(self):
        """Return controller configurations."""
        # ---------------- Arm controllers ---------------- #
        arm_pd_joint_pos = PDJointPosControllerConfig(
            self.arm_joint_names,
            lower=None, upper=None,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            normalize_action=False,
        )

        arm_pd_joint_delta_pos = PDJointPosControllerConfig(
            self.arm_joint_names,
            lower=-0.1, upper=0.1,  # smaller deltas for stability
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            use_delta=True,
        )

        arm_pd_ee_delta_pos = PDEEPosControllerConfig(
            joint_names=self.arm_joint_names,
            pos_lower=-0.05, pos_upper=0.05,
            stiffness=self.arm_stiffness * 2,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit * 3,
            ee_link=self.ee_link_name,
            urdf_path=self.urdf_path,
        )

        arm_pd_ee_delta_pose = PDEEPoseControllerConfig(
            joint_names=self.arm_joint_names,
            pos_lower=-0.05, pos_upper=0.05,
            rot_lower=-0.1,  rot_upper=0.1,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            ee_link=self.ee_link_name,
            urdf_path=self.urdf_path,
        )

        # ---------------- Gripper controller ---------------- #
        gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
            self.gripper_joint_names,
            lower=0.0,   # closed
            upper=0.04,  # open
            stiffness=self.gripper_stiffness,
            damping=self.gripper_damping,
            force_limit=self.gripper_force_limit,
        )

        configs = dict(
            pd_joint_delta_pos=dict(arm=arm_pd_joint_delta_pos, gripper=gripper_pd_joint_pos),
            pd_joint_pos      =dict(arm=arm_pd_joint_pos,       gripper=gripper_pd_joint_pos),
            pd_ee_delta_pos   =dict(arm=arm_pd_ee_delta_pos,    gripper=gripper_pd_joint_pos),
            pd_ee_delta_pose  =dict(arm=arm_pd_ee_delta_pose,   gripper=gripper_pd_joint_pos),
        )
        return deepcopy(configs)

    def is_grasping(self, obj: Actor, min_force=0.5, max_angle=85):
        """
        Simple heuristic grasp check.
        Returns True if the gripper is closed beyond half of its maximum opening.
        """
        q = self.robot.get_qpos()
        gripper_idx = [self.robot.get_active_joints().index(j)
                       for j in self.robot.get_active_joints()
                       if j.name in self.gripper_joint_names[:1]]
        if not gripper_idx:
            return torch.zeros(self.count, dtype=torch.bool, device=self.device)
        gripper_pos = q[:, gripper_idx[0]]
        return gripper_pos < 0.02

    def is_static(self, threshold: float = 0.1):
        """Check if the arm is nearly static."""
        qvel = self.robot.get_qvel()
        arm_vel = torch.zeros(self.count, device=self.device)
        for joint_name in self.arm_joint_names:
            idx = self.robot.get_qlimits().joint_map[joint_name]
            arm_vel += qvel[:, idx] ** 2
        return arm_vel < threshold ** 2

    def get_state_names(self):
        return ["qpos", "qvel"]


def register_to_envs():
    """Add robot to ManiSkill environments."""
    from mani_skill.envs.tasks.tabletop.push_cube import PushCubeEnv
    from mani_skill.envs.tasks.tabletop.pick_cube import PickCubeEnv

    environments = [PushCubeEnv, PickCubeEnv]
    robot_uid = GEN72EG2Robot.uid
    for env_class in environments:
        if robot_uid not in env_class.SUPPORTED_ROBOTS:
            env_class.SUPPORTED_ROBOTS.append(robot_uid)
            print(f"Registered {robot_uid} into {env_class.__name__}")

    print(f"\nYou can now use '{robot_uid}' as the robot_uids argument")
    print(f"Example: python ppo_my.py --env_id='PushCube-v1' --robot_uids='{robot_uid}' ...")


if __name__ == "__main__":
    robot = GEN72EG2Robot
    print(f"GEN72-EG2 robot registered, UID: {robot.uid}")
    print(f"URDF path: {URDF_PATH}")
    register_to_envs()