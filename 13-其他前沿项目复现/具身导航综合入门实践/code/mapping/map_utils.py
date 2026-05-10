"""
地图模块 —— 战争迷雾 & 前沿点探测
===================================
提供：
  - 俯视图坐标互转
  - 战争迷雾更新（扇形视野展开）
  - 前沿点检测（Frontier Exploration）
"""

import numpy as np
import cv2

from habitat.utils.visualizations import maps
from habitat.tasks.utils import cartesian_to_polar
from habitat.utils.geometry_utils import quaternion_rotate_vector


# ── 坐标转换 ──────────────────────────────────────────────────

def convert_meters_to_pixel(meters: float, map_resolution: int, sim) -> int:
    """米 → 像素（俯视图分辨率下）。"""
    return int(meters / maps.calculate_meters_per_pixel(map_resolution, sim=sim))


def map_coors_to_pixel(position, top_down_map: np.ndarray, sim) -> np.ndarray:
    """世界坐标 → 俯视图像素坐标 [row, col]。"""
    a_x, a_y = maps.to_grid(
        position[2], position[0],
        (top_down_map.shape[0], top_down_map.shape[1]),
        sim=sim,
    )
    return np.array([a_x, a_y])


def pixel_to_world(pixel: np.ndarray, agent_y: float,
                   top_down_map: np.ndarray, sim) -> np.ndarray:
    """俯视图像素坐标 → 可导航世界坐标（snap 到 navmesh）。"""
    x, y = pixel
    realworld_x, realworld_y = maps.from_grid(
        x, y,
        (top_down_map.shape[0], top_down_map.shape[1]),
        sim=sim,
    )
    return sim.pathfinder.snap_point([realworld_y, agent_y, realworld_x])


# ── 朝向角 ────────────────────────────────────────────────────

def get_polar_angle(agent_state) -> float:
    """返回 agent 当前航向角（弧度，俯视图极坐标系）。"""
    ref_rotation = agent_state.rotation
    heading_vector = quaternion_rotate_vector(
        ref_rotation.inverse(), np.array([0, 0, -1])
    )
    phi = cartesian_to_polar(-heading_vector[2], heading_vector[0])[1]
    return float(np.array(phi) + np.pi)


def wrap_heading(heading: float) -> float:
    """将航向角归一化到 [-π, π]。"""
    return (heading + np.pi) % (2 * np.pi) - np.pi


# ── 战争迷雾 ──────────────────────────────────────────────────

def reveal_fog_of_war(
    top_down_map: np.ndarray,
    current_fog_of_war_mask: np.ndarray,
    current_point: np.ndarray,
    current_angle: float,
    fov: float = 90,
    max_line_len: float = 100,
) -> np.ndarray:
    """
    根据当前位置与朝向，更新战争迷雾掩码（扇形视野）。

    Parameters
    ----------
    top_down_map          : 可通行区域二值图（>0 可通行）
    current_fog_of_war_mask: 已探索区域掩码
    current_point         : agent 在俯视图中的像素坐标 [row, col]
    current_angle         : 航向角（弧度）
    fov                   : 水平视场角（度）
    max_line_len          : 可见半径（像素）

    Returns
    -------
    更新后的探索掩码
    """
    curr_pt_cv2 = current_point[::-1].astype(int)
    angle_cv2 = np.rad2deg(wrap_heading(-current_angle + np.pi / 2))

    cone_mask = cv2.ellipse(
        np.zeros_like(top_down_map, dtype=np.uint8),
        tuple(curr_pt_cv2),
        (int(max_line_len), int(max_line_len)),
        0,
        angle_cv2 - fov / 2,
        angle_cv2 + fov / 2,
        1,
        -1,
    )

    visible = cv2.bitwise_and(cone_mask, (top_down_map > 0).astype(np.uint8))
    return cv2.bitwise_or(current_fog_of_war_mask.astype(np.uint8), visible.astype(np.uint8))


# ── 前沿点检测 ────────────────────────────────────────────────

def detect_frontiers(full_map: np.ndarray, explored_mask: np.ndarray,
                     min_area: int = 8):
    """
    在已探索与未探索的边界处检测前沿点。

    Parameters
    ----------
    full_map      : 全图可通行区域二值图
    explored_mask : 已探索区域掩码
    min_area      : 连通域最小面积（像素），过滤噪声

    Returns
    -------
    (pts, frontier_mask)
        pts           : list of np.ndarray [row, col]，各前沿点像素坐标
        frontier_mask : 前沿区域掩码图
    """
    navigable = (full_map > 0).astype(np.uint8)
    explored = (explored_mask > 0).astype(np.uint8)
    unexplored_nav = (navigable & (1 - explored)).astype(np.uint8)

    border = cv2.morphologyEx(explored, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    frontier_mask = (border & unexplored_nav).astype(np.uint8)

    n, labels, stats, centroids = cv2.connectedComponentsWithStats(frontier_mask, 8)
    pts = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            c = centroids[i]
            pts.append(np.array([int(c[1]), int(c[0])]))  # row, col
    return pts, frontier_mask
