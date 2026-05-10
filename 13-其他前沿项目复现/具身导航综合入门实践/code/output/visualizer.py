"""
输出模块 —— 视频渲染 & HUD & 地图面板
======================================
提供导航过程的可视化合成功能。
"""

import numpy as np
import cv2

from mapping.map_utils import map_coors_to_pixel, get_polar_angle


class VisualOutput:
    """
    管理俯视地图渲染、HUD 叠加及视频帧合成。
    由 EmbodiedNavigator 持有。
    """

    def __init__(self, config, tdm: np.ndarray, fog: np.ndarray):
        self.cfg = config
        self.tdm = tdm
        self.fog = fog  # 外部持有同一引用，需要每步更新后重新赋值

        self.last_frontier_mask = None
        self.traj_pixels = []
        self.path_pixels = []

    def update_fog(self, fog: np.ndarray):
        """更新探索掩码引用（由 Navigator 在每步调用）。"""
        self.fog = fog

    def hud(self, img: np.ndarray, state, total_steps: int,
            decision_count: int, visited_targets: set,
            target_objects: list, phase: str = "") -> None:
        """在图像左上角叠加导航状态信息（原地修改）。"""
        p = state.position
        lines = [
            f"{phase}  Step:{total_steps}  Dec:{decision_count}",
            f"Pos:({p[0]:.1f},{p[1]:.1f},{p[2]:.1f})",
            f"Found:{list(visited_targets)}",
            f"Left:{[t for t in target_objects if t not in visited_targets]}",
        ]
        for i, l in enumerate(lines):
            cv2.putText(img, l, (10, 20 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

    def render_map_panel(self, state, sim, frontiers=None) -> np.ndarray:
        """渲染 320×320 俯视地图面板。"""
        nav = (self.tdm > 0).astype(np.uint8)
        exp = (self.fog > 0).astype(np.uint8)

        panel = np.zeros((self.tdm.shape[0], self.tdm.shape[1], 3), dtype=np.uint8)
        panel[nav > 0] = (40, 40, 40)
        panel[exp > 0] = (110, 110, 110)

        if self.last_frontier_mask is not None:
            panel[self.last_frontier_mask > 0] = (255, 255, 0)

        if len(self.traj_pixels) > 1:
            for i in range(len(self.traj_pixels) - 1):
                p1 = tuple(self.traj_pixels[i][::-1].astype(int))
                p2 = tuple(self.traj_pixels[i + 1][::-1].astype(int))
                cv2.line(panel, p1, p2, (0, 255, 255), 1)

        if len(self.path_pixels) > 1:
            for i in range(len(self.path_pixels) - 1):
                p1 = tuple(self.path_pixels[i][::-1].astype(int))
                p2 = tuple(self.path_pixels[i + 1][::-1].astype(int))
                cv2.line(panel, p1, p2, (255, 0, 255), 2)

        if frontiers:
            for i, f in enumerate(frontiers):
                fp = f.get("pixel", None)
                if fp is None:
                    fp = map_coors_to_pixel(f["position"], self.tdm, sim)
                c = tuple(fp[::-1].astype(int))
                cv2.circle(panel, c, 3, (0, 255, 0), -1)
                cv2.putText(panel, str(i), (c[0] + 3, c[1] - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        ap = map_coors_to_pixel(state.position, self.tdm, sim).astype(int)
        self.traj_pixels.append(ap.copy())
        if len(self.traj_pixels) > 3000:
            self.traj_pixels = self.traj_pixels[-3000:]

        yaw = get_polar_angle(state)
        tip = ap + np.array([int(10 * np.cos(yaw)), int(10 * np.sin(yaw))])
        cv2.circle(panel, tuple(ap[::-1]), 4, (0, 0, 255), -1)
        cv2.arrowedLine(panel, tuple(ap[::-1]), tuple(tip[::-1]),
                        (0, 0, 255), 2, tipLength=0.35)

        return cv2.resize(panel, (320, 320), interpolation=cv2.INTER_NEAREST)

    def compose_frame(self, rgb_frame: np.ndarray, state, sim,
                      frontiers=None) -> np.ndarray:
        """将 RGB 帧与地图面板左右拼接。"""
        map_panel = self.render_map_panel(state, sim, frontiers=frontiers)
        h, w = rgb_frame.shape[:2]
        if map_panel.shape[0] != h:
            map_panel = cv2.resize(
                map_panel,
                (int(map_panel.shape[1] * h / map_panel.shape[0]), h)
            )
        canvas = np.zeros((h, w + map_panel.shape[1], 3), dtype=np.uint8)
        canvas[:, :w] = rgb_frame
        canvas[:, w:] = map_panel
        cv2.putText(canvas, "RGB View", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(canvas, "2D Frontier Map", (w + 10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return canvas

    def save_video(self, frames: list, path: str, fps: int):
        """将帧列表写入 AVI 视频。"""
        if not frames:
            return
        h, w = frames[0].shape[:2]
        wr = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"DIVX"), fps, (w, h))
        for f in frames:
            wr.write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
        wr.release()
        print(f"[OUTPUT] 视频 -> {path} ({len(frames)} 帧)")
