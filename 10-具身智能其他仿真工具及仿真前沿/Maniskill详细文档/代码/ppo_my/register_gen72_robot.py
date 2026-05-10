#!/usr/bin/env python3
"""
注册GEN72-EG2机器人到ManiSkill环境中

此脚本注册自定义的GEN72-EG2机器人，配置其物理属性和控制参数，
使其可以在ManiSkill环境中使用，特别是与稳定版PPO算法一起使用。
"""
import os
import sys
import numpy as np
# torch将在实际训练时导入，注册阶段可选
try:
    import torch
except ImportError:
    print("警告: torch未安装，仅在使用PPO训练时需要")
import sapien
from copy import deepcopy

# 确保可以导入ManiSkill模块
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(ROOT_DIR)

from mani_skill.agents.base_agent import BaseAgent, Keyframe
from mani_skill.agents.controllers import *
from mani_skill.agents.registration import register_agent
from mani_skill.utils import common, sapien_utils
from mani_skill.utils.structs.actor import Actor

# 修改这个路径为URDF文件实际路径
URDF_PATH = '/home/kewei/17robo/ManiSkill/urdf_01/GEN72-EG2.urdf'

# 环境第一次注册时可能会出现缺少"4C2_baselink"等链接的错误，这是因为URDF文件中的一些链接可能无法被物理引擎正确加载
# 如果遇到此类错误，可能需要修改URDF文件或检查URDF中的链接/关节定义是否有问题

@register_agent()
class GEN72EG2Robot(BaseAgent):
    """
    GEN72-EG2 机器人类，集成了7自由度机械臂和EG2夹爪
    """
    uid = "gen72_eg2_robot"
    urdf_path = URDF_PATH
    
    # 设置摩擦力以便抓取物体
    urdf_config = dict(
        _materials=dict(
            gripper=dict(static_friction=2.0, dynamic_friction=2.0, restitution=0.0)
        ),
        link={
            # 确保这些链接名称与URDF中的实际名称匹配
            "Link7": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link2": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link3": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
        },
    )
    
    # 定义关节名称 - 从URDF文件中获取的实际关节名称
    arm_joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'joint7']
    # 夹爪关节名称，从URDF文件
    gripper_joint_names = ['4C2_Joint1', '4C2_Joint2', '4C2_Joint3', '4C2_Joint5']
    
    # 末端效应器链接名称
    ee_link_name = "Link7"
    tcp_link_name = "Link7"  # 定义TCP链接名称，通常与末端效应器相同
    
    # 控制参数 - 经过调整以确保更稳定的控制
    arm_stiffness = 1e3
    arm_damping = 1e2
    arm_force_limit = 100
    
    gripper_stiffness = 1e3
    gripper_damping = 1e2
    gripper_force_limit = 100
    
    # 定义初始姿态的关键帧 - 针对推方块任务优化的姿势
    keyframes = dict(
        rest=Keyframe(
            qpos=np.array([
                0, -0.1, 0, -1.5, 0, 1.8, 0.8,  # 机械臂 - 更自然的姿势，手臂稍微下垂，适合推方块
                0.04, 0.04, 0.04, 0.04  # 夹爪关节，打开状态
            ]),
            # 旋转180度并前移基座，使机械臂能轻松接触到桌面物体
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),  # 绕z轴旋转180度并前移0.2米
        ),
        push_ready=Keyframe(
            qpos=np.array([
                0, 0.2, 0, -1.2, 0, 1.6, 0.0,  # 机械臂 - 推动准备姿势
                0.04, 0.04, 0.04, 0.04  # 夹爪关节，打开状态
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        ),
        grasp_ready=Keyframe(
            qpos=np.array([
                0, 0.1, 0, -1.0, 0, 1.2, 0.0,  # 机械臂 - 抓取准备姿势
                0.04, 0.04, 0.04, 0.04  # 夹爪关节，打开状态
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        ),
        grasp_close=Keyframe(
            qpos=np.array([
                0, 0.1, 0, -1.0, 0, 1.2, 0.0,  # 机械臂 - 抓取准备姿势
                0.0, 0.0, 0.0, 0.0  # 夹爪关节，关闭状态
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        )
    )
    
    def initialize(self, engine, scene):
        """初始化机器人，保存TCP链接"""
        super().initialize(engine, scene)
        # 找到并保存TCP链接
        self._tcp_link = None
        for link in self.robot.get_links():
            if link.name == self.tcp_link_name:
                self._tcp_link = link
                break
        if self._tcp_link is None:
            raise ValueError(f"TCP link {self.tcp_link_name} not found in robot links")
    
    @property
    def tcp(self):
        """返回TCP (Tool Center Point) 链接的Actor对象"""
        if not hasattr(self, '_tcp_link') or self._tcp_link is None:
            for link in self.robot.get_links():
                if link.name == self.tcp_link_name:
                    self._tcp_link = link
                    break
        return self._tcp_link
    
    @property
    def _controller_configs(self):
        """配置机器人控制器"""
        # -------------------------------------------------------------------------- #
        # 机械臂控制器
        # -------------------------------------------------------------------------- #
        # 关节位置控制
        arm_pd_joint_pos = PDJointPosControllerConfig(
            self.arm_joint_names,
            lower=None,
            upper=None,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            normalize_action=False,
        )
        
        # 关节位置增量控制 - 常用于RL
        arm_pd_joint_delta_pos = PDJointPosControllerConfig(
            self.arm_joint_names,
            lower=-0.1,  # 限制每步动作幅度，增加稳定性
            upper=0.1,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            use_delta=True,
        )
        
        # 末端执行器位置增量控制
        arm_pd_ee_delta_pos = PDEEPosControllerConfig(
            joint_names=self.arm_joint_names,
            pos_lower=-0.05,  # 减小动作空间以提高稳定性
            pos_upper=0.05,
            stiffness=self.arm_stiffness*2,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit*3,
            ee_link=self.ee_link_name,
            urdf_path=self.urdf_path,
        )
        
        # 末端执行器姿态增量控制
        arm_pd_ee_delta_pose = PDEEPoseControllerConfig(
            joint_names=self.arm_joint_names,
            pos_lower=-0.05,  # 更小的动作空间
            pos_upper=0.05,
            rot_lower=-0.1,
            rot_upper=0.1,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            ee_link=self.ee_link_name,
            urdf_path=self.urdf_path,
        )
        
        # -------------------------------------------------------------------------- #
        # 夹爪控制器
        # -------------------------------------------------------------------------- #
        # 夹爪位置控制
        gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
            self.gripper_joint_names,
            lower=0.0,  # 闭合位置
            upper=0.04,  # 打开位置
            stiffness=self.gripper_stiffness,
            damping=self.gripper_damping,
            force_limit=self.gripper_force_limit,
        )
        
        # 返回所有控制器配置
        controller_configs = dict(
            # 组合控制器 - 同时控制机械臂和夹爪
            pd_joint_delta_pos=dict(
                arm=arm_pd_joint_delta_pos,
                gripper=gripper_pd_joint_pos,
            ),
            pd_joint_pos=dict(
                arm=arm_pd_joint_pos,
                gripper=gripper_pd_joint_pos,
            ),
            pd_ee_delta_pos=dict(
                arm=arm_pd_ee_delta_pos,
                gripper=gripper_pd_joint_pos,
            ),
            pd_ee_delta_pose=dict(
                arm=arm_pd_ee_delta_pose,
                gripper=gripper_pd_joint_pos,
            ),
        )
        
        # 深拷贝以防用户修改
        return deepcopy(controller_configs)
    
    def is_grasping(self, obj: Actor, min_force=0.5, max_angle=85):
        """
        检查夹爪是否抓取住了物体
        
        Args:
            obj: 要检查是否被抓取的物体Actor
            min_force: 最小接触力
            max_angle: 最大接触角度（度）
            
        Returns:
            布尔值张量，表示是否抓取成功
        """
        # 简化实现：仅基于夹爪状态判断，不涉及物理接触检测
        # 检查夹爪是否闭合足够
        q = self.robot.get_qpos()
        gripper_idx = [self.robot.get_active_joints().index(j) for j in self.robot.get_active_joints() 
                      if j.name in self.gripper_joint_names[:1]]  # 只检查第一个关节
        
        if len(gripper_idx) == 0:
            return torch.zeros(self.count, dtype=torch.bool, device=self.device)
        
        gripper_pos = q[:, gripper_idx[0]]
        # 如果夹爪关闭程度小于最大开度的一半，则认为抓取成功
        return gripper_pos < 0.02
    
    def is_static(self, threshold: float = 0.1):
        """检查机器人是否静止"""
        qvel = self.robot.get_qvel()
        
        # 计算关节速度的平方和
        arm_vel = torch.zeros(self.count, device=self.device)
        for joint_name in self.arm_joint_names:
            idx = self.robot.get_qlimits().joint_map[joint_name]
            arm_vel += qvel[:, idx] ** 2
            
        is_static = arm_vel < threshold ** 2
        return is_static
    
    def get_state_names(self):
        """返回可用于状态的名称列表"""
        return ["qpos", "qvel"]


def register_to_envs():
    """将机器人注册到相关环境中"""
    # 导入环境模块
    from mani_skill.envs.tasks.tabletop.push_cube import PushCubeEnv
    from mani_skill.envs.tasks.tabletop.pick_cube import PickCubeEnv
    
    environments = [PushCubeEnv, PickCubeEnv]
    robot_uid = GEN72EG2Robot.uid
    
    for env_class in environments:
        if robot_uid not in env_class.SUPPORTED_ROBOTS:
            env_class.SUPPORTED_ROBOTS.append(robot_uid)
            print(f"已将 {robot_uid} 添加到 {env_class.__name__} 的支持机器人列表中")
    
    print(f"\n现在可以在环境中使用 '{robot_uid}' 作为robot_uids参数")
    print(f"示例命令: python ppo_my.py --env_id='PushCube-v1' --robot_uids='{robot_uid}' ...")


if __name__ == "__main__":
    # 注册机器人
    robot = GEN72EG2Robot
    print(f"GEN72-EG2机器人已注册，UID: {robot.uid}")
    print(f"URDF文件路径: {URDF_PATH}")
    
    # 将机器人注册到环境中
    register_to_envs() 