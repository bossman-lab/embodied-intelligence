from collections import defaultdict
import os
import random
import time
from dataclasses import dataclass
from typing import Optional

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import tyro
from torch.distributions.normal import Normal
from torch.utils.tensorboard import SummaryWriter

# ManiSkill specific imports
import mani_skill.envs
from mani_skill.utils import gym_utils
from mani_skill.utils.wrappers.flatten import FlattenActionSpaceWrapper
from mani_skill.utils.wrappers.record import RecordEpisode
from mani_skill.vector.wrappers.gymnasium import ManiSkillVectorEnv

# 导入和注册GEN72-EG2机器人
import sys
import sapien
from mani_skill.agents.base_agent import BaseAgent, Keyframe
from mani_skill.agents.controllers import *
from mani_skill.agents.registration import register_agent
from mani_skill.utils import common, sapien_utils
from mani_skill.utils.structs.actor import Actor
from copy import deepcopy

# 机器人URDF路径
URDF_PATH = '/home/kewei/17robo/ManiSkill/urdf_01/GEN72-EG2.urdf'

# 注册GEN72-EG2机器人
@register_agent()
class GEN72EG2Robot(BaseAgent):
    """GEN72-EG2 机器人类，集成了7自由度机械臂和夹爪"""
    uid = "gen72_eg2_robot"
    urdf_path = URDF_PATH
    
    # 设置摩擦力以便抓取物体
    urdf_config = dict(
        _materials=dict(
            gripper=dict(static_friction=2.0, dynamic_friction=2.0, restitution=0.0)
        ),
        link={
            # 夹爪和末端链接的摩擦设置
            "Link7": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link2": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
            "4C2_Link3": dict(material="gripper", patch_radius=0.1, min_patch_radius=0.1),
        },
    )
    
    # 定义关节名称
    arm_joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'joint7']
    gripper_joint_names = ['4C2_Joint1', '4C2_Joint2', '4C2_Joint3', '4C2_Joint5']
    
    # 末端效应器链接名称
    ee_link_name = "Link7"
    tcp_link_name = "Link7"
    
    # 控制参数
    arm_stiffness = 1e3
    arm_damping = 1e2
    arm_force_limit = 100
    
    gripper_stiffness = 1e3
    gripper_damping = 1e2
    gripper_force_limit = 100
    
    # 定义初始姿态的关键帧
    keyframes = dict(
        rest=Keyframe(
            qpos=np.array([
                0, -0.1, 0, -1.5, 0, 1.8, 0.8,  # 机械臂
                0.04, 0.04, 0.04, 0.04  # 夹爪
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
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
                0.0, 0.0, 0.0, 0.0
            ]),
            pose=sapien.Pose(p=[0, 0.2, 0], q=[0, 0, 1, 0]),
        )
    )
    
    def initialize(self, engine, scene):
        """初始化机器人，保存TCP链接"""
        super().initialize(engine, scene)
        self._tcp_link = None
        for link in self.robot.get_links():
            if link.name == self.tcp_link_name:
                self._tcp_link = link
                break
        if self._tcp_link is None:
            raise ValueError(f"TCP link {self.tcp_link_name} not found in robot links")
    
    @property
    def tcp(self):
        """返回TCP链接的Actor对象"""
        if not hasattr(self, '_tcp_link') or self._tcp_link is None:
            for link in self.robot.get_links():
                if link.name == self.tcp_link_name:
                    self._tcp_link = link
                    break
        return self._tcp_link
    
    @property
    def _controller_configs(self):
        """配置机器人控制器"""
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
        
        # 关节位置增量控制
        arm_pd_joint_delta_pos = PDJointPosControllerConfig(
            self.arm_joint_names,
            lower=-0.1,
            upper=0.1,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            use_delta=True,
        )
        
        # 末端执行器位置增量控制
        arm_pd_ee_delta_pos = PDEEPosControllerConfig(
            joint_names=self.arm_joint_names,
            pos_lower=-0.05,
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
            pos_lower=-0.05,
            pos_upper=0.05,
            rot_lower=-0.1,
            rot_upper=0.1,
            stiffness=self.arm_stiffness,
            damping=self.arm_damping,
            force_limit=self.arm_force_limit,
            ee_link=self.ee_link_name,
            urdf_path=self.urdf_path,
        )
        
        # 夹爪位置控制
        gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
            self.gripper_joint_names,
            lower=0.0,
            upper=0.04,
            stiffness=self.gripper_stiffness,
            damping=self.gripper_damping,
            force_limit=self.gripper_force_limit,
        )
        
        # 返回所有控制器配置
        controller_configs = dict(
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
        
        return deepcopy(controller_configs)
    
    def is_grasping(self, obj: Actor, min_force=0.5, max_angle=85):
        """检查夹爪是否抓取住了物体"""
        q = self.robot.get_qpos()
        gripper_idx = [self.robot.get_active_joints().index(j) for j in self.robot.get_active_joints() 
                      if j.name in self.gripper_joint_names[:1]]
        
        if len(gripper_idx) == 0:
            return torch.zeros(self.count, dtype=torch.bool, device=self.device)
        
        gripper_pos = q[:, gripper_idx[0]]
        return gripper_pos < 0.02
    
    def is_static(self, threshold: float = 0.1):
        """检查机器人是否静止"""
        qvel = self.robot.get_qvel()
        
        arm_vel = torch.zeros(self.count, device=self.device)
        for joint_name in self.arm_joint_names:
            idx = self.robot.get_qlimits().joint_map[joint_name]
            arm_vel += qvel[:, idx] ** 2
            
        is_static = arm_vel < threshold ** 2
        return is_static
    
    def get_state_names(self):
        """返回可用于状态的名称列表"""
        return ["qpos", "qvel"]

# 将机器人注册到环境中
def register_robot_to_envs():
    """将GEN72-EG2机器人注册到任务环境中"""
    # 导入环境模块
    from mani_skill.envs.tasks.tabletop.push_cube import PushCubeEnv
    from mani_skill.envs.tasks.tabletop.pick_cube import PickCubeEnv
    
    environments = [PushCubeEnv, PickCubeEnv]
    robot_uid = GEN72EG2Robot.uid
    
    print(f"正在将机器人 {robot_uid} 注册到环境中...")
    
    for env_class in environments:
        if robot_uid not in env_class.SUPPORTED_ROBOTS:
            env_class.SUPPORTED_ROBOTS.append(robot_uid)
            print(f"已将 {robot_uid} 添加到 {env_class.__name__} 的支持机器人列表中")

# 在模块导入时立即注册机器人
print("注册GEN72-EG2机器人...")
register_robot_to_envs()
print(f"GEN72-EG2机器人注册完成，UID: {GEN72EG2Robot.uid}")

@dataclass
class Args:
    exp_name: Optional[str] = None
    """the name of this experiment"""
    seed: int = 1
    """seed of the experiment"""
    torch_deterministic: bool = True
    """if toggled, `torch.backends.cudnn.deterministic=True`"""
    cuda: bool = True
    """if toggled, cuda will be enabled by default"""
    track: bool = False
    """if toggled, this experiment will be tracked with Weights and Biases"""
    wandb_project_name: str = "ManiSkill"
    """the wandb's project name"""
    wandb_entity: Optional[str] = None
    """the entity (team) of wandb's project"""
    capture_video: bool = True
    """whether to capture videos of the agent performances (check out `videos` folder)"""
    save_model: bool = True
    """whether to save model into the `runs/{run_name}` folder"""
    evaluate: bool = False
    """if toggled, only runs evaluation with the given model checkpoint and saves the evaluation trajectories"""
    checkpoint: Optional[str] = None
    """path to a pretrained checkpoint file to start evaluation/training from"""
    robot_uids: str = "panda"
    """robot_uid to use in the environment, e.g., panda, gen72_eg2_robot"""

    # Algorithm specific arguments
    env_id: str = "PushCube-v1"
    """the id of the environment"""
    total_timesteps: int = 10000000
    """total timesteps of the experiments"""
    learning_rate: float = 3e-4  # 降低学习率以增加稳定性
    """the learning rate of the optimizer"""
    num_envs: int = 512
    """the number of parallel environments"""
    num_eval_envs: int = 8
    """the number of parallel evaluation environments"""
    partial_reset: bool = True
    """whether to let parallel environments reset upon termination instead of truncation"""
    eval_partial_reset: bool = False
    """whether to let parallel evaluation environments reset upon termination instead of truncation"""
    num_steps: int = 50
    """the number of steps to run in each environment per policy rollout"""
    num_eval_steps: int = 50
    """the number of steps to run in each evaluation environment during evaluation"""
    reconfiguration_freq: Optional[int] = None
    """how often to reconfigure the environment during training"""
    eval_reconfiguration_freq: Optional[int] = 1
    """for benchmarking purposes we want to reconfigure the eval environment each reset to ensure objects are randomized in some tasks"""
    control_mode: Optional[str] = "pd_joint_delta_pos"
    """the control mode to use for the environment"""
    anneal_lr: bool = False
    """Toggle learning rate annealing for policy and value networks"""
    gamma: float = 0.8
    """the discount factor gamma"""
    gae_lambda: float = 0.9
    """the lambda for the general advantage estimation"""
    num_minibatches: int = 32
    """the number of mini-batches"""
    update_epochs: int = 4
    """the K epochs to update the policy"""
    norm_adv: bool = True
    """Toggles advantages normalization"""
    clip_coef: float = 0.2
    """the surrogate clipping coefficient"""
    clip_vloss: bool = False
    """Toggles whether or not to use a clipped loss for the value function, as per the paper."""
    ent_coef: float = 0.0
    """coefficient of the entropy"""
    vf_coef: float = 0.5
    """coefficient of the value function"""
    max_grad_norm: float = 0.25  # 降低梯度裁剪阈值以防止梯度爆炸
    """the maximum norm for the gradient clipping"""
    target_kl: float = 0.1
    """the target KL divergence threshold"""
    reward_scale: float = 1.0
    """Scale the reward by this factor"""
    eval_freq: int = 25
    """evaluation frequency in terms of iterations"""
    save_train_video_freq: Optional[int] = None
    """frequency to save training videos in terms of iterations"""
    finite_horizon_gae: bool = False
    
    # 数值稳定性选项
    eps: float = 1e-8  # 数值稳定性小常数
    """小常数用于数值稳定性"""
    detect_anomaly: bool = False  # 是否检测梯度异常
    """是否开启PyTorch的异常检测"""
    log_grad_norm: bool = True  # 是否记录梯度范数
    """是否记录梯度范数"""

    # to be filled in runtime
    batch_size: int = 0
    """the batch size (computed in runtime)"""
    minibatch_size: int = 0
    """the mini-batch size (computed in runtime)"""
    num_iterations: int = 0
    """the number of iterations (computed in runtime)"""

def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


class Agent(nn.Module):
    def __init__(self, envs):
        super().__init__()
        self.critic = nn.Sequential(
            layer_init(nn.Linear(np.array(envs.single_observation_space.shape).prod(), 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, 1), std=0.01),  # 更小的初始化值
        )
        self.actor_mean = nn.Sequential(
            layer_init(nn.Linear(np.array(envs.single_observation_space.shape).prod(), 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, 256)),
            nn.Tanh(),
            layer_init(nn.Linear(256, np.prod(envs.single_action_space.shape)), std=0.001),  # 更小的初始化值
        )
        # 使用稍微更小的初始化标准差
        self.actor_logstd = nn.Parameter(torch.zeros(1, np.prod(envs.single_action_space.shape)) - 1.0) 
        
        # 添加数值边界
        self.max_action_range = 5.0
        self.max_log_std = 2
        self.min_log_std = -5
        
        print(f"Agent initialized with action space shape: {envs.single_action_space.shape}")

    def get_value(self, x):
        """获取状态值，添加了数值稳定性处理"""
        # 数值稳定性检查
        x = torch.as_tensor(x, dtype=torch.float32)
        if torch.isnan(x).any() or torch.isinf(x).any():
            x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        
        value = self.critic(x)
        # 值限制，防止过大或过小
        value = torch.clamp(value, -10.0, 10.0)
        return value
        
    def get_action(self, x, deterministic=False):
        """获取动作，添加了数值稳定性处理"""
        # 数值稳定性检查
        x = torch.as_tensor(x, dtype=torch.float32)
        if torch.isnan(x).any() or torch.isinf(x).any():
            x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        
        action_mean = self.actor_mean(x)
        # 限制行为均值范围
        action_mean = torch.clamp(action_mean, -self.max_action_range, self.max_action_range)
        
        if deterministic:
            return action_mean
            
        action_logstd = self.actor_logstd.expand_as(action_mean)
        # 限制标准差范围
        action_logstd = torch.clamp(action_logstd, self.min_log_std, self.max_log_std)
        action_std = torch.exp(action_logstd)
        
        # 确保标准差有效
        action_std = torch.clamp(action_std, 1e-6, 1.0)
        
        probs = Normal(action_mean, action_std)
        action = probs.sample()
        
        # 限制行为范围
        action = torch.clamp(action, -self.max_action_range, self.max_action_range)
        return action
        
    def get_action_and_value(self, x, action=None):
        """获取动作和价值，添加了数值稳定性处理"""
        # 数值稳定性检查
        x = torch.as_tensor(x, dtype=torch.float32)
        if torch.isnan(x).any() or torch.isinf(x).any():
            x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        
        action_mean = self.actor_mean(x)
        # 限制行为均值范围
        action_mean = torch.clamp(action_mean, -self.max_action_range, self.max_action_range)
        
        action_logstd = self.actor_logstd.expand_as(action_mean)
        # 限制标准差范围
        action_logstd = torch.clamp(action_logstd, self.min_log_std, self.max_log_std)
        action_std = torch.exp(action_logstd)
        
        # 确保标准差有效
        action_std = torch.clamp(action_std, 1e-6, 1.0)
        
        probs = Normal(action_mean, action_std)
        if action is None:
            action = probs.sample()
            # 限制行为范围
            action = torch.clamp(action, -self.max_action_range, self.max_action_range)
            
        # 数值稳定性：计算log_prob和entropy时避免NaN
        log_prob = probs.log_prob(action)
        if torch.isnan(log_prob).any():
            print(f"Warning: NaN in log_prob. action_mean: {action_mean}, action_std: {action_std}, action: {action}")
            log_prob = torch.nan_to_num(log_prob, nan=0.0)
            
        entropy = probs.entropy()
        if torch.isnan(entropy).any():
            print(f"Warning: NaN in entropy. action_mean: {action_mean}, action_std: {action_std}")
            entropy = torch.nan_to_num(entropy, nan=0.0)
            
        value = self.get_value(x)
            
        return action, log_prob.sum(1), entropy.sum(1), value

class Logger:
    def __init__(self, log_wandb=False, tensorboard: SummaryWriter = None) -> None:
        self.writer = tensorboard
        self.log_wandb = log_wandb
    def add_scalar(self, tag, scalar_value, step):
        # 数值稳定性检查
        if isinstance(scalar_value, torch.Tensor):
            if torch.isnan(scalar_value).any() or torch.isinf(scalar_value).any():
                print(f"Warning: NaN or Inf in {tag}")
                scalar_value = torch.nan_to_num(scalar_value, nan=0.0, posinf=0.0, neginf=0.0)
            scalar_value = scalar_value.item()
        
        if np.isnan(scalar_value) or np.isinf(scalar_value):
            print(f"Warning: NaN or Inf in {tag}")
            scalar_value = 0.0
            
        if self.log_wandb:
            wandb.log({tag: scalar_value}, step=step)
        self.writer.add_scalar(tag, scalar_value, step)
    def close(self):
        self.writer.close()

if __name__ == "__main__":
    args = tyro.cli(Args)
    args.batch_size = int(args.num_envs * args.num_steps)
    args.minibatch_size = int(args.batch_size // args.num_minibatches)
    args.num_iterations = args.total_timesteps // args.batch_size
    if args.exp_name is None:
        args.exp_name = os.path.basename(__file__)[: -len(".py")]
        run_name = f"{args.env_id}__{args.exp_name}__{args.seed}__{int(time.time())}"
    else:
        run_name = args.exp_name
        
    # 设置模型保存路径，优先使用环境变量
    model_save_dir = os.environ.get("MODEL_SAVE_DIR", "runs")
    print(f"模型将保存在: {os.path.abspath(model_save_dir)}/{run_name}")

    # 设置PyTorch异常检测
    if args.detect_anomaly:
        print("开启PyTorch异常检测")
        torch.autograd.set_detect_anomaly(True)

    # TRY NOT TO MODIFY: seeding
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cudnn.deterministic = args.torch_deterministic

    device = torch.device("cuda" if torch.cuda.is_available() and args.cuda else "cpu")

    # 打印接收到的参数
    print(f"获取到的参数: robot_uids={args.robot_uids}")

    # env setup
    env_kwargs = dict(obs_mode="state", render_mode="rgb_array", sim_backend="physx_cuda")
    if args.control_mode is not None:
        env_kwargs["control_mode"] = args.control_mode
    envs = gym.make(args.env_id, num_envs=args.num_envs if not args.evaluate else 1, 
                    reconfiguration_freq=args.reconfiguration_freq, 
                    robot_uids=args.robot_uids, **env_kwargs)
    eval_envs = gym.make(args.env_id, num_envs=args.num_eval_envs, 
                         reconfiguration_freq=args.eval_reconfiguration_freq, 
                         robot_uids=args.robot_uids, **env_kwargs)
    if isinstance(envs.action_space, gym.spaces.Dict):
        envs = FlattenActionSpaceWrapper(envs)
        eval_envs = FlattenActionSpaceWrapper(eval_envs)
    if args.capture_video:
        # 使用自定义保存路径
        eval_output_dir = f"{model_save_dir}/{run_name}/videos"
        if args.evaluate:
            eval_output_dir = f"{os.path.dirname(args.checkpoint)}/test_videos"
        print(f"Saving eval videos to {eval_output_dir}")
        if args.save_train_video_freq is not None:
            save_video_trigger = lambda x : (x // args.num_steps) % args.save_train_video_freq == 0
            envs = RecordEpisode(envs, output_dir=f"{model_save_dir}/{run_name}/train_videos", save_trajectory=False, save_video_trigger=save_video_trigger, max_steps_per_video=args.num_steps, video_fps=30)
        eval_envs = RecordEpisode(eval_envs, output_dir=eval_output_dir, save_trajectory=args.evaluate, trajectory_name="trajectory", max_steps_per_video=args.num_eval_steps, video_fps=30)
    envs = ManiSkillVectorEnv(envs, args.num_envs, ignore_terminations=not args.partial_reset, record_metrics=True)
    eval_envs = ManiSkillVectorEnv(eval_envs, args.num_eval_envs, ignore_terminations=not args.eval_partial_reset, record_metrics=True)
    assert isinstance(envs.single_action_space, gym.spaces.Box), "only continuous action space is supported"

    max_episode_steps = gym_utils.find_max_episode_steps_value(envs._env)
    logger = None
    if not args.evaluate:
        print("Running training")
        if args.track:
            import wandb
            config = vars(args)
            config["env_cfg"] = dict(**env_kwargs, num_envs=args.num_envs, env_id=args.env_id, reward_mode="normalized_dense", env_horizon=max_episode_steps, partial_reset=args.partial_reset)
            config["eval_env_cfg"] = dict(**env_kwargs, num_envs=args.num_eval_envs, env_id=args.env_id, reward_mode="normalized_dense", env_horizon=max_episode_steps, partial_reset=False)
            wandb.init(
                project=args.wandb_project_name,
                entity=args.wandb_entity,
                sync_tensorboard=False,
                config=config,
                name=run_name,
                save_code=True,
                group="PPO",
                tags=["ppo", "stable_ppo", "walltime_efficient"]
            )
        # 使用自定义保存路径
        log_dir = f"{model_save_dir}/{run_name}"
        os.makedirs(log_dir, exist_ok=True)
        writer = SummaryWriter(log_dir)
        writer.add_text(
            "hyperparameters",
            "|param|value|\n|-|-|\n%s" % ("\n".join([f"|{key}|{value}|" for key, value in vars(args).items()])),
        )
        logger = Logger(log_wandb=args.track, tensorboard=writer)
    else:
        print("Running evaluation")

    agent = Agent(envs).to(device)
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

    # ALGO Logic: Storage setup
    obs = torch.zeros((args.num_steps, args.num_envs) + envs.single_observation_space.shape).to(device)
    actions = torch.zeros((args.num_steps, args.num_envs) + envs.single_action_space.shape).to(device)
    logprobs = torch.zeros((args.num_steps, args.num_envs)).to(device)
    rewards = torch.zeros((args.num_steps, args.num_envs)).to(device)
    dones = torch.zeros((args.num_steps, args.num_envs)).to(device)
    values = torch.zeros((args.num_steps, args.num_envs)).to(device)

    # TRY NOT TO MODIFY: start the game
    global_step = 0
    start_time = time.time()
    next_obs, _ = envs.reset(seed=args.seed)
    eval_obs, _ = eval_envs.reset(seed=args.seed)
    next_done = torch.zeros(args.num_envs, device=device)
    print(f"####")
    print(f"args.num_iterations={args.num_iterations} args.num_envs={args.num_envs} args.num_eval_envs={args.num_eval_envs}")
    print(f"args.minibatch_size={args.minibatch_size} args.batch_size={args.batch_size} args.update_epochs={args.update_epochs}")
    print(f"####")
    action_space_low, action_space_high = torch.from_numpy(envs.single_action_space.low).to(device), torch.from_numpy(envs.single_action_space.high).to(device)
    def clip_action(action: torch.Tensor):
        return torch.clamp(action.detach(), action_space_low, action_space_high)

    if args.checkpoint:
        agent.load_state_dict(torch.load(args.checkpoint))

    # 添加NaN跟踪
    nan_detected_count = 0
    max_nan_tolerance = 5
    total_grad_norm_list = []

    for iteration in range(1, args.num_iterations + 1):
        print(f"Epoch: {iteration}, global_step={global_step}")
        final_values = torch.zeros((args.num_steps, args.num_envs), device=device)
        agent.eval()
        if iteration % args.eval_freq == 1:
            print("Evaluating")
            eval_obs, _ = eval_envs.reset()
            eval_metrics = defaultdict(list)
            num_episodes = 0
            for _ in range(args.num_eval_steps):
                with torch.no_grad():
                    eval_obs, eval_rew, eval_terminations, eval_truncations, eval_infos = eval_envs.step(agent.get_action(eval_obs, deterministic=True))
                    if "final_info" in eval_infos:
                        mask = eval_infos["_final_info"]
                        num_episodes += mask.sum()
                        for k, v in eval_infos["final_info"]["episode"].items():
                            eval_metrics[k].append(v)
            print(f"Evaluated {args.num_eval_steps * args.num_eval_envs} steps resulting in {num_episodes} episodes")
            for k, v in eval_metrics.items():
                mean = torch.stack(v).float().mean()
                if logger is not None:
                    logger.add_scalar(f"eval/{k}", mean, global_step)
                print(f"eval_{k}_mean={mean}")
            if args.evaluate:
                break
        if args.save_model and iteration % args.eval_freq == 1:
            # 使用自定义保存路径
            model_path = f"{model_save_dir}/{run_name}/ckpt_{iteration}.pt"
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            torch.save(agent.state_dict(), model_path)
            print(f"model saved to {model_path}")
        # Annealing the rate if instructed to do so.
        if args.anneal_lr:
            frac = 1.0 - (iteration - 1.0) / args.num_iterations
            lrnow = frac * args.learning_rate
            optimizer.param_groups[0]["lr"] = lrnow

        rollout_time = time.time()
        for step in range(0, args.num_steps):
            global_step += args.num_envs
            obs[step] = next_obs
            dones[step] = next_done

            # ALGO LOGIC: action logic
            with torch.no_grad():
                action, logprob, _, value = agent.get_action_and_value(next_obs)
                values[step] = value.flatten()
            actions[step] = action
            logprobs[step] = logprob

            # 检查是否有NaN值
            if torch.isnan(action).any() or torch.isnan(logprob).any() or torch.isnan(value).any():
                print(f"Warning: NaN detected in action/logprob/value at step {step}, iteration {iteration}")
                # 替换NaN值
                action = torch.nan_to_num(action, nan=0.0)
                logprob = torch.nan_to_num(logprob, nan=0.0)
                value = torch.nan_to_num(value, nan=0.0)
                
                nan_detected_count += 1
                if nan_detected_count > max_nan_tolerance:
                    print(f"Error: Too many NaN values detected ({nan_detected_count}). Aborting training.")
                    # 保存当前模型以便调试
                    # 使用自定义保存路径
                    model_path = f"{model_save_dir}/{run_name}/emergency_ckpt_{iteration}.pt"
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    torch.save(agent.state_dict(), model_path)
                    print(f"Emergency model saved to {model_path}")
                    if not args.evaluate:
                        logger.close()
                    envs.close()
                    eval_envs.close()
                    exit(1)

            # TRY NOT TO MODIFY: execute the game and log data.
            next_obs, reward, terminations, truncations, infos = envs.step(clip_action(action))
            next_done = torch.logical_or(terminations, truncations).to(torch.float32)
            
            # 奖励裁剪，防止过大的奖励导致不稳定
            reward = torch.clamp(reward, -10.0, 10.0)
            rewards[step] = reward.view(-1) * args.reward_scale

            if "final_info" in infos:
                final_info = infos["final_info"]
                done_mask = infos["_final_info"]
                for k, v in final_info["episode"].items():
                    logger.add_scalar(f"train/{k}", v[done_mask].float().mean(), global_step)
                with torch.no_grad():
                    final_values[step, torch.arange(args.num_envs, device=device)[done_mask]] = agent.get_value(infos["final_observation"][done_mask]).view(-1)
        rollout_time = time.time() - rollout_time
        # bootstrap value according to termination and truncation
        with torch.no_grad():
            next_value = agent.get_value(next_obs).reshape(1, -1)
            advantages = torch.zeros_like(rewards).to(device)
            lastgaelam = 0
            for t in reversed(range(args.num_steps)):
                if t == args.num_steps - 1:
                    next_not_done = 1.0 - next_done
                    nextvalues = next_value
                else:
                    next_not_done = 1.0 - dones[t + 1]
                    nextvalues = values[t + 1]
                real_next_values = next_not_done * nextvalues + final_values[t] # t instead of t+1
                # next_not_done means nextvalues is computed from the correct next_obs
                # if next_not_done is 1, final_values is always 0
                # if next_not_done is 0, then use final_values, which is computed according to bootstrap_at_done
                if args.finite_horizon_gae:
                    """
                    See GAE paper equation(16) line 1, we will compute the GAE based on this line only
                    1             *(  -V(s_t)  + r_t                                                               + gamma * V(s_{t+1})   )
                    lambda        *(  -V(s_t)  + r_t + gamma * r_{t+1}                                             + gamma^2 * V(s_{t+2}) )
                    lambda^2      *(  -V(s_t)  + r_t + gamma * r_{t+1} + gamma^2 * r_{t+2}                         + ...                  )
                    lambda^3      *(  -V(s_t)  + r_t + gamma * r_{t+1} + gamma^2 * r_{t+2} + gamma^3 * r_{t+3}
                    We then normalize it by the sum of the lambda^i (instead of 1-lambda)
                    """
                    if t == args.num_steps - 1: # initialize
                        lam_coef_sum = 0.
                        reward_term_sum = 0. # the sum of the second term
                        value_term_sum = 0. # the sum of the third term
                    lam_coef_sum = lam_coef_sum * next_not_done
                    reward_term_sum = reward_term_sum * next_not_done
                    value_term_sum = value_term_sum * next_not_done

                    lam_coef_sum = 1 + args.gae_lambda * lam_coef_sum
                    reward_term_sum = args.gae_lambda * args.gamma * reward_term_sum + lam_coef_sum * rewards[t]
                    value_term_sum = args.gae_lambda * args.gamma * value_term_sum + args.gamma * real_next_values

                    advantages[t] = (reward_term_sum + value_term_sum) / lam_coef_sum - values[t]
                else:
                    delta = rewards[t] + args.gamma * real_next_values - values[t]
                    advantages[t] = lastgaelam = delta + args.gamma * args.gae_lambda * next_not_done * lastgaelam # Here actually we should use next_not_terminated, but we don't have lastgamlam if terminated
            returns = advantages + values
            
            # 检查是否有NaN值
            if torch.isnan(advantages).any() or torch.isnan(returns).any():
                print(f"Warning: NaN detected in advantages/returns calculation, iteration {iteration}")
                # 替换NaN值
                advantages = torch.nan_to_num(advantages, nan=0.0)
                returns = torch.nan_to_num(returns, nan=0.0)

        # flatten the batch
        b_obs = obs.reshape((-1,) + envs.single_observation_space.shape)
        b_logprobs = logprobs.reshape(-1)
        b_actions = actions.reshape((-1,) + envs.single_action_space.shape)
        b_advantages = advantages.reshape(-1)
        b_returns = returns.reshape(-1)
        b_values = values.reshape(-1)

        # Optimizing the policy and value network
        agent.train()
        b_inds = np.arange(args.batch_size)
        clipfracs = []
        update_time = time.time()
        for epoch in range(args.update_epochs):
            np.random.shuffle(b_inds)
            for start in range(0, args.batch_size, args.minibatch_size):
                end = start + args.minibatch_size
                mb_inds = b_inds[start:end]

                _, newlogprob, entropy, newvalue = agent.get_action_and_value(b_obs[mb_inds], b_actions[mb_inds])
                logratio = newlogprob - b_logprobs[mb_inds]
                ratio = logratio.exp()

                with torch.no_grad():
                    # calculate approx_kl http://joschu.net/blog/kl-approx.html
                    old_approx_kl = (-logratio).mean()
                    approx_kl = ((ratio - 1) - logratio).mean()
                    clipfracs += [((ratio - 1.0).abs() > args.clip_coef).float().mean().item()]

                if args.target_kl is not None and approx_kl > args.target_kl:
                    break

                mb_advantages = b_advantages[mb_inds]
                if args.norm_adv:
                    mb_advantages = (mb_advantages - mb_advantages.mean()) / (mb_advantages.std() + args.eps)

                # Policy loss
                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(ratio, 1 - args.clip_coef, 1 + args.clip_coef)
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                # Value loss
                newvalue = newvalue.view(-1)
                if args.clip_vloss:
                    v_loss_unclipped = (newvalue - b_returns[mb_inds]) ** 2
                    v_clipped = b_values[mb_inds] + torch.clamp(
                        newvalue - b_values[mb_inds],
                        -args.clip_coef,
                        args.clip_coef,
                    )
                    v_loss_clipped = (v_clipped - b_returns[mb_inds]) ** 2
                    v_loss_max = torch.max(v_loss_unclipped, v_loss_clipped)
                    v_loss = 0.5 * v_loss_max.mean()
                else:
                    v_loss = 0.5 * ((newvalue - b_returns[mb_inds]) ** 2).mean()

                entropy_loss = entropy.mean()
                loss = pg_loss - args.ent_coef * entropy_loss + v_loss * args.vf_coef

                # 检查是否有NaN值
                if torch.isnan(loss).any():
                    print(f"Warning: NaN detected in loss calculation, epoch {epoch}, iteration {iteration}")
                    print(f"pg_loss: {pg_loss}, v_loss: {v_loss}, entropy_loss: {entropy_loss}")
                    # 尝试通过跳过此批次来恢复
                    continue

                optimizer.zero_grad()
                loss.backward()
                
                # 梯度检查和记录
                if args.log_grad_norm:
                    total_grad_norm = 0
                    for p in agent.parameters():
                        if p.grad is not None:
                            param_norm = p.grad.data.norm(2)
                            total_grad_norm += param_norm.item() ** 2
                            
                            # 检查梯度中是否有NaN
                            if torch.isnan(p.grad).any():
                                print(f"Warning: NaN in gradients for parameter {p.shape}")
                                p.grad = torch.nan_to_num(p.grad, nan=0.0)
                    
                    total_grad_norm = total_grad_norm ** 0.5
                    total_grad_norm_list.append(total_grad_norm)
                    if logger is not None:
                        logger.add_scalar("debug/grad_norm", total_grad_norm, global_step)
                    
                    # 如果梯度范数过大，打印警告
                    if total_grad_norm > args.max_grad_norm * 2:
                        print(f"Warning: Gradient norm too large: {total_grad_norm}")
                
                # 梯度裁剪以防止梯度爆炸
                nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
                optimizer.step()

            if args.target_kl is not None and approx_kl > args.target_kl:
                break

        update_time = time.time() - update_time

        y_pred, y_true = b_values.cpu().numpy(), b_returns.cpu().numpy()
        var_y = np.var(y_true)
        explained_var = np.nan if var_y == 0 else 1 - np.var(y_true - y_pred) / var_y

        # 记录调试信息
        if len(total_grad_norm_list) > 0:
            avg_grad_norm = sum(total_grad_norm_list) / len(total_grad_norm_list)
            logger.add_scalar("debug/avg_grad_norm", avg_grad_norm, global_step)
            total_grad_norm_list = []

        logger.add_scalar("charts/learning_rate", optimizer.param_groups[0]["lr"], global_step)
        logger.add_scalar("losses/value_loss", v_loss.item(), global_step)
        logger.add_scalar("losses/policy_loss", pg_loss.item(), global_step)
        logger.add_scalar("losses/entropy", entropy_loss.item(), global_step)
        logger.add_scalar("losses/old_approx_kl", old_approx_kl.item(), global_step)
        logger.add_scalar("losses/approx_kl", approx_kl.item(), global_step)
        logger.add_scalar("losses/clipfrac", np.mean(clipfracs), global_step)
        logger.add_scalar("losses/explained_variance", explained_var, global_step)
        
        # 打印和记录性能指标
        sps = int(global_step / (time.time() - start_time))
        print(f"SPS: {sps}, NaN检测计数: {nan_detected_count}")
        logger.add_scalar("charts/SPS", sps, global_step)
        logger.add_scalar("debug/nan_count", nan_detected_count, global_step)
        logger.add_scalar("time/step", global_step, global_step)
        logger.add_scalar("time/update_time", update_time, global_step)
        logger.add_scalar("time/rollout_time", rollout_time, global_step)
        logger.add_scalar("time/rollout_fps", args.num_envs * args.num_steps / rollout_time, global_step)
    if not args.evaluate:
        if args.save_model:
            # 使用自定义保存路径
            model_path = f"{model_save_dir}/{run_name}/final_ckpt.pt"
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            torch.save(agent.state_dict(), model_path)
            print(f"model saved to {model_path}")
        logger.close()
    envs.close()
    eval_envs.close()
