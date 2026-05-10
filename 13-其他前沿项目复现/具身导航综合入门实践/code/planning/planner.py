"""
规划模块 —— 路径规划 & 导航执行
==================================
提供：
  - 基于 habitat_sim GreedyGeodesicFollower 的路径规划
  - 导航到目标点（逐步执行动作）
  - 路径像素化（供可视化使用）
"""

import numpy as np
import habitat_sim

from mapping.map_utils import map_coors_to_pixel


class PathPlanner:
    """
    封装 habitat_sim 路径规划与导航执行。
    由 EmbodiedNavigator 持有。
    """

    def __init__(self, sim, agent, config):
        self.sim = sim
        self.agent = agent
        self.pf = sim.pathfinder
        self.cfg = config

    def plan_path_pixels(self, target_world: np.ndarray,
                         top_down_map: np.ndarray) -> list:
        """
        从当前位置到目标点规划路径，返回像素坐标列表（供可视化）。

        Parameters
        ----------
        target_world  : 目标世界坐标
        top_down_map  : 俯视地图（用于坐标转换）

        Returns
        -------
        list of np.ndarray [row, col]，空列表表示规划失败
        """
        state = self.agent.get_state()
        island = self.pf.get_island(state.position)
        snapped = self.pf.snap_point(point=target_world, island_index=island)

        if not self.pf.is_navigable(snapped):
            return []

        path = habitat_sim.ShortestPath()
        path.requested_start = state.position
        path.requested_end = snapped

        if self.pf.find_path(path):
            return [
                map_coors_to_pixel(p, top_down_map, self.sim).astype(int)
                for p in path.points
            ]
        return []

    def navigate_to(self, target_position: np.ndarray,
                    top_down_map: np.ndarray,
                    on_step_callback=None) -> None:
        """
        导航到目标点，沿途执行回调（用于录制视频帧、更新迷雾等）。

        Parameters
        ----------
        target_position   : 目标世界坐标
        top_down_map      : 俯视地图（坐标转换用）
        on_step_callback  : callable(obs, agent_state) or None
                            每执行一步动作后调用；回调返回 True 表示请求提前中止
        """
        state = self.agent.get_state()
        island = self.pf.get_island(state.position)
        snapped = self.pf.snap_point(point=target_position, island_index=island)

        if not self.pf.is_navigable(snapped):
            print(f"[NAV] 目标不可达: {target_position}")
            return

        follower = habitat_sim.GreedyGeodesicFollower(
            self.pf, self.agent,
            forward_key="move_forward",
            left_key="turn_left",
            right_key="turn_right",
        )

        try:
            action_list = follower.find_path(snapped)
        except Exception as e:
            print(f"[NAV] 路径规划失败: {e}")
            return

        for action in action_list:
            if action is None:
                continue
            obs = self.sim.step(action)
            s = self.agent.get_state()

            if on_step_callback is not None:
                stop = on_step_callback(obs, s)
                if stop:
                    break
