"""
几何工具
========
四元数、深度反投影等几何计算函数。
"""

import numpy as np


def quaternion_to_rotation_matrix(q: np.ndarray) -> np.ndarray:
    """四元数 [w, x, y, z] → 3×3 旋转矩阵。"""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def depth_to_3d_world(depth_map: np.ndarray, bbox, agent_state, K: np.ndarray):
    """
    检测框中心 + 深度图 → 世界坐标 (3D)。

    Parameters
    ----------
    depth_map   : H×W float 深度图（米）
    bbox        : (x1, y1, x2, y2)
    agent_state : habitat_sim.AgentState
    K           : 3×3 相机内参

    Returns
    -------
    np.ndarray (3,) 世界坐标，失败时返回 None
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    mx = max(1, (x2 - x1) // 4)
    my = max(1, (y2 - y1) // 4)
    region = depth_map[y1 + my:y2 - my, x1 + mx:x2 - mx]
    if region.size == 0:
        return None
    valid = region[region > 0]
    if valid.size == 0:
        return None
    d = float(np.median(valid))
    if d <= 0 or d > 10.0:
        return None

    cx_px = (x1 + x2) / 2.0
    cy_px = (y1 + y2) / 2.0
    fx, fy = K[0, 0], K[1, 1]
    cx_c, cy_c = K[0, 2], K[1, 2]

    point_cam = np.array([
        (cx_px - cx_c) * d / fx,
        -(cy_px - cy_c) * d / fy,
        -d,
        1.0,
    ])

    rot = agent_state.rotation
    q = np.array([rot.w, rot.x, rot.y, rot.z])
    R = quaternion_to_rotation_matrix(q)
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.array(agent_state.position)
    return (T @ point_cam)[:3]
