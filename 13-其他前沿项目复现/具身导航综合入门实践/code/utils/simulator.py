"""
仿真器工具
==========
habitat-sim 仿真器初始化及相机内参计算。
"""

import numpy as np
import habitat_sim


def setup_simulator(config):
    """根据 Config 创建并返回 habitat_sim.Simulator 实例。"""
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = config.SCENE_PATH
    sim_cfg.enable_physics = False

    rgb_spec = habitat_sim.CameraSensorSpec()
    rgb_spec.uuid = "color_sensor"
    rgb_spec.sensor_type = habitat_sim.SensorType.COLOR
    rgb_spec.resolution = [config.IMAGE_HEIGHT, config.IMAGE_WIDTH]
    rgb_spec.position = [0.0, config.SENSOR_HEIGHT, 0.0]
    rgb_spec.hfov = config.HFOV

    depth_spec = habitat_sim.CameraSensorSpec()
    depth_spec.uuid = "depth_sensor"
    depth_spec.sensor_type = habitat_sim.SensorType.DEPTH
    depth_spec.resolution = [config.IMAGE_HEIGHT, config.IMAGE_WIDTH]
    depth_spec.position = [0.0, config.SENSOR_HEIGHT, 0.0]
    depth_spec.hfov = config.HFOV

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [rgb_spec, depth_spec]
    agent_cfg.action_space = {
        "move_forward": habitat_sim.agent.ActionSpec(
            "move_forward", habitat_sim.agent.ActuationSpec(amount=0.25)),
        "turn_left": habitat_sim.agent.ActionSpec(
            "turn_left", habitat_sim.agent.ActuationSpec(amount=30.0)),
        "turn_right": habitat_sim.agent.ActionSpec(
            "turn_right", habitat_sim.agent.ActuationSpec(amount=30.0)),
    }

    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    return habitat_sim.Simulator(cfg)


def get_camera_intrinsics(config) -> np.ndarray:
    """返回 3×3 相机内参矩阵 K。"""
    hfov_rad = config.HFOV * np.pi / 180.0
    fx = config.IMAGE_WIDTH / (2.0 * np.tan(hfov_rad / 2.0))
    fy = fx
    cx = config.IMAGE_WIDTH / 2.0
    cy = config.IMAGE_HEIGHT / 2.0
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
