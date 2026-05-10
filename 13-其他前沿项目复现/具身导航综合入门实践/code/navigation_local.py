import numpy as np
import cv2
import json
import re
import os
from datetime import datetime

import torch
from PIL import Image
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

import habitat_sim
from habitat.utils.visualizations import maps
from habitat.tasks.utils import cartesian_to_polar
from habitat.utils.geometry_utils import quaternion_rotate_vector

from ultralytics import YOLO


# ============================================================
# 配置
# ============================================================
class Config:
    SCENE_PATH = "./data/scene_datasets/habitat-test-scenes/apartment_1.glb"
    TARGET_OBJECTS = ["chair", "couch", "tv"]

    YOLO_MODEL = "yolov8n.pt"
    YOLO_CONF_THRESHOLD = 0.35

    MODEL_NAME = "/home/robot/navigation/Qwen3-VL-4B-Instruct"
    MODEL_DTYPE = "auto"
    MODEL_DEVICE_MAP = "auto"
    MODEL_MAX_NEW_TOKENS = 1024
    MODEL_TEMPERATURE = 0.3
    MODEL_TOP_P = 0.9
    MODEL_TOP_K = 50

    MAX_STEPS = 500
    SPIN_STEPS = 12
    VISIBLE_RADIUS = 3.0
    MAP_RESOLUTION = 512
    AREA_THRESHOLD_M2 = 9
    TARGET_REACH_DIST = 1.5

    IMAGE_WIDTH = 640
    IMAGE_HEIGHT = 480
    HFOV = 90
    SENSOR_HEIGHT = 1.5

    OUTPUT_VIDEO = "navigation_output.avi"
    OUTPUT_LOG = "vlm_reasoning_log.json"
    VIDEO_FPS = 4


# ============================================================
# 工具函数
# ============================================================
def setup_simulator(config: Config):
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


def get_camera_intrinsics(config: Config):
    hfov_rad = config.HFOV * np.pi / 180.0
    fx = config.IMAGE_WIDTH / (2.0 * np.tan(hfov_rad / 2.0))
    fy = fx
    cx = config.IMAGE_WIDTH / 2.0
    cy = config.IMAGE_HEIGHT / 2.0
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])


def quaternion_to_rotation_matrix(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def depth_to_3d_world(depth_map, bbox, agent_state, K):
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


# ============================================================
# 地图 / 前沿
# ============================================================
def convert_meters_to_pixel(meters: float, map_resolution, sim) -> int:
    return int(meters / maps.calculate_meters_per_pixel(map_resolution, sim=sim))


def map_coors_to_pixel(position, top_down_map, sim) -> np.ndarray:
    a_x, a_y = maps.to_grid(
        position[2], position[0],
        (top_down_map.shape[0], top_down_map.shape[1]),
        sim=sim,
    )
    return np.array([a_x, a_y])


def pixel_to_world(pixel: np.ndarray, agent_y, top_down_map, sim) -> np.ndarray:
    x, y = pixel
    realworld_x, realworld_y = maps.from_grid(
        x, y,
        (top_down_map.shape[0], top_down_map.shape[1]),
        sim=sim,
    )
    return sim.pathfinder.snap_point([realworld_y, agent_y, realworld_x])


def get_polar_angle(agent_state):
    ref_rotation = agent_state.rotation
    heading_vector = quaternion_rotate_vector(
        ref_rotation.inverse(), np.array([0, 0, -1])
    )
    phi = cartesian_to_polar(-heading_vector[2], heading_vector[0])[1]
    return np.array(phi) + np.pi


def wrap_heading(heading):
    return (heading + np.pi) % (2 * np.pi) - np.pi


def reveal_fog_of_war(
    top_down_map: np.ndarray,
    current_fog_of_war_mask: np.ndarray,
    current_point: np.ndarray,
    current_angle: float,
    fov: float = 90,
    max_line_len: float = 100,
) -> np.ndarray:
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


def detect_frontiers(full_map: np.ndarray, explored_mask: np.ndarray, min_area=8):
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
            pts.append(np.array([int(c[1]), int(c[0])]))
    return pts, frontier_mask


# ============================================================
# YOLO 检测器
# ============================================================
class YOLODetector:
    def __init__(self, config: Config):
        self.model = YOLO(config.YOLO_MODEL)
        self.conf = config.YOLO_CONF_THRESHOLD
        self.targets = [t.lower() for t in config.TARGET_OBJECTS]

    def detect(self, image_rgb):
        bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        results = self.model(bgr, verbose=False, conf=self.conf)
        dets = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls = self.model.names[int(box.cls[0])].lower()
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                dets.append({
                    "class": cls,
                    "confidence": float(box.conf[0]),
                    "bbox": (x1, y1, x2, y2),
                    "is_target": cls in self.targets,
                })
        return dets

    def draw_detections(self, image_rgb, detections):
        img = image_rgb.copy()
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            if d["is_target"]:
                color, thick = (0, 255, 0), 3
            else:
                color, thick = (200, 200, 200), 1
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
            label = f"{d['class']} {d['confidence']:.2f}"
            lsz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - lsz[1] - 6), (x1 + lsz[0], y1), color, -1)
            cv2.putText(img, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        return img


# ============================================================
# 本地 Qwen3-VL
# ============================================================
class LocalQwen3VLEngine:
    def __init__(
        self,
        model_name: str = "/home/robot/navigation/Qwen3-VL-4B-Instruct",
        device_map: str = "auto",
        dtype: str = "auto",
        max_new_tokens: int = 1024,
    ):
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens

        if dtype == "auto":
            if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8:
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        elif dtype == "bf16":
            torch_dtype = torch.bfloat16
        elif dtype == "fp16":
            torch_dtype = torch.float16
        else:
            torch_dtype = torch.float32

        print(f"正在加载本地模型: {model_name}")
        print(f"数据类型: {torch_dtype}")
        print(f"设备映射: {device_map}")

        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map=device_map,
            attn_implementation="sdpa",
        )
        self.processor = AutoProcessor.from_pretrained(model_name)
        print("本地模型加载完成！")

    def infer_messages(
        self,
        system_prompt: str,
        user_text: str,
        pil_images=None,
        max_new_tokens: int = None,
        temperature: float = 0.3,
        top_p: float = 0.9,
        top_k: int = 50,
    ) -> str:
        if pil_images is None:
            pil_images = []
        if max_new_tokens is None:
            max_new_tokens = self.max_new_tokens

        messages = [{
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}],
        }]

        user_content = []
        for img in pil_images:
            user_content.append({"type": "image", "image": img})
        user_content.append({"type": "text", "text": user_text})

        messages.append({"role": "user", "content": user_content})

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs.pop("token_type_ids", None)
        inputs = inputs.to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=temperature > 0,
            )

        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
        ]

        output_text = self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return output_text[0]


# ============================================================
# 决策引擎
# ============================================================
class VLMDecisionEngine:
    def __init__(self, config: Config):
        self.cfg = config
        self.model = config.MODEL_NAME
        self.targets = config.TARGET_OBJECTS
        self.reasoning_log = []
        self.count = 0

        self.local_engine = LocalQwen3VLEngine(
            model_name=config.MODEL_NAME,
            device_map=config.MODEL_DEVICE_MAP,
            dtype=config.MODEL_DTYPE,
            max_new_tokens=config.MODEL_MAX_NEW_TOKENS,
        )

    def make_decision(self, key_images, detection_summary, frontier_info,
                      visited_targets, nav_history, agent_pos):
        self.count += 1

        system_prompt = f"""你是一个具身智能导航机器人的决策大脑。你的任务是在室内环境中找到以下全部目标物体: {self.targets}

你需要根据当前观察到的图像、YOLO检测结果（含物体3D坐标和距离）、可探索的前沿点，做出导航决策。

决策规则:
1. 如果检测到了目标物体且距离合理(< 8米), 优先导航到目标物体
2. 如果检测到多个目标物体, 选择最近的未访问目标
3. 如果没有检测到目标物体, 选择最优的前沿点进行探索
4. 选择前沿点时, 优先选择距离适中、朝向较大未探索区域的方向
5. 如果所有目标都已访问, 返回 "task_complete"

严格以以下JSON格式回复, 不要输出其他内容:
{{
    "thinking": "你的详细思考过程: 1)看到了什么 2)分析各选项 3)做出决策的理由",
    "action": "go_to_object" 或 "explore_frontier" 或 "task_complete",
    "target_index": 选择的目标在对应列表中的索引(从0开始),
    "confidence": 0到1之间的置信度
}}"""

        text = f"""## 第 {self.count} 次决策

### 当前状态
- Agent位置: [{agent_pos[0]:.2f}, {agent_pos[1]:.2f}, {agent_pos[2]:.2f}]
- 已访问目标: {visited_targets if visited_targets else '无'}
- 待寻找目标: {[t for t in self.targets if t not in visited_targets]}

### YOLO 检测结果 (原地旋转360°汇总)
"""
        if detection_summary:
            for i, d in enumerate(detection_summary):
                p = f"[{d['world_pos'][0]:.2f}, {d['world_pos'][1]:.2f}, {d['world_pos'][2]:.2f}]" if d.get("world_pos") else "未知"
                dist = f"{d['distance']:.2f}m" if d.get("distance") is not None else "未知"
                tag = "目标" if d["is_target"] else "非目标"
                text += f"  [{i}] {d['class']} (置信度:{d['confidence']:.2f}) 3D位置:{p} 距离:{dist} {tag}\n"
        else:
            text += "  当前旋转一圈未检测到任何物体\n"

        text += "\n### 可用前沿点\n"
        if frontier_info:
            for i, f in enumerate(frontier_info):
                text += f"  [{i}] 位置:[{f['position'][0]:.2f}, {f['position'][1]:.2f}, {f['position'][2]:.2f}] 距离:{f['distance']:.2f}m\n"
        else:
            text += "  无可用前沿点\n"

        text += f"\n### 导航历史\n{nav_history}\n"

        try:
            pil_images = []
            for img in key_images[-4:]:
                if isinstance(img, np.ndarray):
                    pil_images.append(Image.fromarray(img.astype(np.uint8)))

            raw = self.local_engine.infer_messages(
                system_prompt=system_prompt,
                user_text=text,
                pil_images=pil_images,
                max_new_tokens=self.cfg.MODEL_MAX_NEW_TOKENS,
                temperature=self.cfg.MODEL_TEMPERATURE,
                top_p=self.cfg.MODEL_TOP_P,
                top_k=self.cfg.MODEL_TOP_K,
            ).strip()

            print(f"\n{'=' * 60}")
            print(f"[VLM 决策 #{self.count}] 本地模型原始回复:")
            print(raw)
            print(f"{'=' * 60}\n")
            decision = self._parse(raw)
        except Exception as e:
            print(f"[VLM Local Error] {e}")
            decision = self._fallback(detection_summary, frontier_info, visited_targets)

        self.reasoning_log.append({
            "decision_id": self.count,
            "agent_position": agent_pos.tolist() if isinstance(agent_pos, np.ndarray) else list(agent_pos),
            "detections_count": len(detection_summary) if detection_summary else 0,
            "frontiers_count": len(frontier_info) if frontier_info else 0,
            "decision": decision,
            "timestamp": datetime.now().isoformat(),
        })
        return decision

    def _parse(self, text):
        l = text.find("{")
        r = text.rfind("}")
        if l != -1 and r != -1 and r > l:
            chunk = text[l:r+1]
            try:
                d = json.loads(chunk)
                return {
                    "action": d.get("action", "explore_frontier"),
                    "target_index": d.get("target_index", 0),
                    "reasoning": d.get("thinking", ""),
                    "confidence": d.get("confidence", 0.5),
                }
            except Exception:
                pass

        if "go_to_object" in text:
            return {"action": "go_to_object", "target_index": 0, "reasoning": text, "confidence": 0.5}
        if "task_complete" in text:
            return {"action": "task_complete", "target_index": -1, "reasoning": text, "confidence": 0.5}
        return {"action": "explore_frontier", "target_index": 0, "reasoning": text, "confidence": 0.3}

    def _fallback(self, dets, fronts, visited):
        if dets:
            tgts = [d for d in dets if d["is_target"] and d["class"] not in visited
                    and d.get("distance") is not None and d["distance"] < 8]
            if tgts:
                tgts.sort(key=lambda x: x["distance"])
                idx = dets.index(tgts[0])
                return {"action": "go_to_object", "target_index": idx,
                        "reasoning": f"[降级] 检测到 {tgts[0]['class']}", "confidence": 0.6}
        if fronts:
            return {"action": "explore_frontier", "target_index": 0,
                    "reasoning": "[降级] 无目标, 探索前沿", "confidence": 0.3}
        return {"action": "explore_frontier", "target_index": 0,
                "reasoning": "[降级] 随机探索", "confidence": 0.1}

    def save_log(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.reasoning_log, f, ensure_ascii=False, indent=2)
        print(f"[LOG] 推理日志 -> {path}")


# ============================================================
# 主导航器
# ============================================================
class EmbodiedNavigator:
    def __init__(self, config: Config):
        self.cfg = config
        self.sim = setup_simulator(config)
        self.agent = self.sim.get_agent(0)
        self.pf = self.sim.pathfinder
        self.K = get_camera_intrinsics(config)

        self.detector = YOLODetector(config)
        self.vlm = VLMDecisionEngine(config)

        self.total_steps = 0
        self.decision_count = 0
        self.visited_targets = set()
        self.visited_frontier_set = set()
        self.nav_history = []
        self.video_frames = []

        self.tdm = None
        self.fog = None
        self.vis_px = 0

        self.last_frontier_mask = None
        self.current_frontiers = []
        self.path_pixels = []
        self.traj_pixels = []

    def initialize(self):
        pos = self.pf.get_random_navigable_point()
        st = habitat_sim.AgentState()
        st.position = pos
        self.agent.set_state(st)

        self.tdm = maps.get_topdown_map_from_sim(
            self.sim, map_resolution=self.cfg.MAP_RESOLUTION, draw_border=False
        )
        self.tdm = (self.tdm > 0).astype(np.uint8)
        self.fog = np.zeros_like(self.tdm, dtype=np.uint8)
        self.vis_px = convert_meters_to_pixel(self.cfg.VISIBLE_RADIUS, self.cfg.MAP_RESOLUTION, self.sim)

        print(f"[INIT] 起始 {pos}, 目标 {self.cfg.TARGET_OBJECTS}")

    def _update_fog(self, state):
        px = map_coors_to_pixel(state.position, self.tdm, self.sim)
        ang = get_polar_angle(state)
        self.fog = reveal_fog_of_war(
            self.tdm, self.fog, px, ang,
            fov=self.cfg.HFOV // 2, max_line_len=self.vis_px
        )

    def _hud(self, img, state, phase=""):
        p = state.position
        lines = [
            f"{phase}  Step:{self.total_steps}  Dec:{self.decision_count}",
            f"Pos:({p[0]:.1f},{p[1]:.1f},{p[2]:.1f})",
            f"Found:{list(self.visited_targets)}",
            f"Left:{[t for t in self.cfg.TARGET_OBJECTS if t not in self.visited_targets]}",
        ]
        for i, l in enumerate(lines):
            cv2.putText(img, l, (10, 20 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

    def _plan_path_pixels(self, target_world):
        state = self.agent.get_state()
        island = self.pf.get_island(state.position)
        snapped = self.pf.snap_point(point=target_world, island_index=island)
        self.path_pixels = []
        if not self.pf.is_navigable(snapped):
            return
        path = habitat_sim.ShortestPath()
        path.requested_start = state.position
        path.requested_end = snapped
        if self.pf.find_path(path):
            self.path_pixels = [map_coors_to_pixel(p, self.tdm, self.sim).astype(int) for p in path.points]

    def _render_map_panel(self, state, frontiers=None):
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
                    fp = map_coors_to_pixel(f["position"], self.tdm, self.sim)
                c = tuple(fp[::-1].astype(int))
                cv2.circle(panel, c, 3, (0, 255, 0), -1)
                cv2.putText(panel, str(i), (c[0] + 3, c[1] - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

        ap = map_coors_to_pixel(state.position, self.tdm, self.sim).astype(int)
        self.traj_pixels.append(ap.copy())
        if len(self.traj_pixels) > 3000:
            self.traj_pixels = self.traj_pixels[-3000:]

        yaw = get_polar_angle(state)
        tip = ap + np.array([int(10 * np.cos(yaw)), int(10 * np.sin(yaw))])
        cv2.circle(panel, tuple(ap[::-1]), 4, (0, 0, 255), -1)
        cv2.arrowedLine(panel, tuple(ap[::-1]), tuple(tip[::-1]), (0, 0, 255), 2, tipLength=0.35)

        panel = cv2.resize(panel, (320, 320), interpolation=cv2.INTER_NEAREST)
        return panel

    def _compose_frame_with_map(self, rgb_frame, state, frontiers=None):
        map_panel = self._render_map_panel(state, frontiers=frontiers)
        h, w = rgb_frame.shape[:2]
        if map_panel.shape[0] != h:
            map_panel = cv2.resize(map_panel, (int(map_panel.shape[1] * h / map_panel.shape[0]), h))
        canvas = np.zeros((h, w + map_panel.shape[1], 3), dtype=np.uint8)
        canvas[:, :w] = rgb_frame
        canvas[:, w:] = map_panel
        cv2.putText(canvas, "RGB View", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(canvas, "2D Frontier Map", (w + 10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return canvas

    def spin_and_observe(self):
        colors, depths, states, all_dets = [], [], [], []

        for _ in range(self.cfg.SPIN_STEPS):
            obs = self.sim.step("turn_left")
            c = obs["color_sensor"][:, :, :3]
            d = obs["depth_sensor"]
            s = self.agent.get_state()

            colors.append(c)
            depths.append(d)
            states.append(s)

            dets = self.detector.detect(c)
            for det in dets:
                wp = depth_to_3d_world(d, det["bbox"], s, self.K)
                det["world_pos"] = wp
                det["distance"] = float(np.linalg.norm(np.array(s.position) - wp)) if wp is not None else None
                all_dets.append(det)

            ann = self.detector.draw_detections(c, dets)
            self._hud(ann, s, phase="[SCAN]")
            out = self._compose_frame_with_map(ann, s, frontiers=self.current_frontiers)
            self.video_frames.append(out)

            self._update_fog(s)
            self.total_steps += 1

        return colors, depths, states, all_dets

    def navigate_to(self, target_position):
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
            right_key="turn_right"
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
            c = obs["color_sensor"][:, :, :3]
            s = self.agent.get_state()

            frame = c.copy()
            self._hud(frame, s, phase="[MOVE]")
            out = self._compose_frame_with_map(frame, s, frontiers=self.current_frontiers)
            self.video_frames.append(out)

            self._update_fog(s)
            self.total_steps += 1
            if self.total_steps >= self.cfg.MAX_STEPS:
                break

    def get_frontiers(self):
        state = self.agent.get_state()
        area_thr = max(
            8,
            convert_meters_to_pixel(self.cfg.AREA_THRESHOLD_M2, self.cfg.MAP_RESOLUTION, self.sim) // 10
        )
        fpxs, frontier_mask = detect_frontiers(self.tdm, self.fog, min_area=area_thr)
        self.last_frontier_mask = frontier_mask

        infos = []
        for fp in fpxs:
            wp = pixel_to_world(fp, state.position[1], self.tdm, self.sim)
            if wp is None or np.any(np.isnan(wp)):
                continue
            if self.pf.is_navigable(wp):
                d = float(np.linalg.norm(np.array(state.position) - wp))
                key = tuple(np.round(wp, 1))
                if key not in self.visited_frontier_set:
                    infos.append({"position": wp, "distance": d, "pixel": fp})
        infos.sort(key=lambda x: x["distance"])
        return infos[:8]

    @staticmethod
    def merge_detections(dets):
        merged = {}
        for d in dets:
            if d["world_pos"] is None:
                continue
            key = (d["class"], tuple(np.round(d["world_pos"], 1)))
            if key not in merged or d["confidence"] > merged[key]["confidence"]:
                merged[key] = d
        return list(merged.values())

    def run(self):
        self.initialize()
        print(f"\n{'=' * 60}")
        print(f"  导航开始  目标: {self.cfg.TARGET_OBJECTS}")
        print(f"{'=' * 60}\n")

        while self.total_steps < self.cfg.MAX_STEPS:
            print(f"\n[Step {self.total_steps}] 原地旋转观察...")
            colors, depths, states, raw_dets = self.spin_and_observe()
            all_dets = self.merge_detections(raw_dets)
            tgt_dets = [d for d in all_dets if d["is_target"]]

            print(f"  检测 {len(all_dets)} 物体, 其中 {len(tgt_dets)} 个目标:")
            for d in tgt_dets:
                dist_text = f"{d['distance']:.2f}" if d.get("distance") is not None else "None"
                print(f"  {d['class']}  conf={d['confidence']:.2f}  dist={dist_text}m  pos={d['world_pos']}")

            agent_state = self.agent.get_state()
            frontiers = self.get_frontiers()
            self.current_frontiers = frontiers
            print(f"  前沿点 {len(frontiers)} 个")

            idx = np.linspace(0, len(colors) - 1, min(4, len(colors)), dtype=int)
            key_imgs = [colors[i] for i in idx]

            det_summary = [{
                "class": d["class"],
                "confidence": d["confidence"],
                "is_target": d["is_target"],
                "world_pos": d["world_pos"].tolist() if d.get("world_pos") is not None else None,
                "distance": d.get("distance"),
            } for d in all_dets]

            frontier_summary = [{
                "position": f["position"].tolist() if isinstance(f["position"], np.ndarray) else list(f["position"]),
                "distance": f["distance"],
            } for f in frontiers]

            hist_text = f"已决策 {self.decision_count} 次, 共 {self.total_steps} 步\n"
            for h in self.nav_history[-5:]:
                hist_text += f"  - {h}\n"

            print(f"[Step {self.total_steps}] VLM 决策中...")
            decision = self.vlm.make_decision(
                key_images=key_imgs,
                detection_summary=det_summary,
                frontier_info=frontier_summary,
                visited_targets=list(self.visited_targets),
                nav_history=hist_text,
                agent_pos=np.array(agent_state.position),
            )
            self.decision_count += 1

            print(f" 动作: {decision['action']}")
            print(f" 思考: {decision['reasoning'][:300]}")

            if decision["action"] == "task_complete":
                print(f"\n 任务完成! 已找到: {list(self.visited_targets)}")
                self.nav_history.append(f"决策{self.decision_count}: 任务完成")
                break

            elif decision["action"] == "go_to_object":
                i = decision["target_index"]
                if i < len(all_dets) and all_dets[i].get("world_pos") is not None:
                    det = all_dets[i]
                    print(f" 前往 {det['class']} @ {det['world_pos']}")
                    self._plan_path_pixels(det["world_pos"])
                    self.navigate_to(det["world_pos"])
                    self.path_pixels = []

                    final_dist = float(np.linalg.norm(np.array(self.agent.get_state().position) - det["world_pos"]))
                    if final_dist < self.cfg.TARGET_REACH_DIST:
                        self.visited_targets.add(det["class"])
                        print(f" 到达 {det['class']}  距离 {final_dist:.2f}m")
                        self.nav_history.append(f"决策{self.decision_count}: → {det['class']} ({final_dist:.1f}m)")
                    else:
                        print(f" 接近 {det['class']}  距离 {final_dist:.2f}m")
                        self.nav_history.append(f"决策{self.decision_count}: → {det['class']} ({final_dist:.1f}m)")
                else:
                    print(" 索引无效, 随机探索")
                    rp = self.pf.get_random_navigable_point()
                    self._plan_path_pixels(rp)
                    self.navigate_to(rp)
                    self.path_pixels = []
                    self.nav_history.append(f"决策{self.decision_count}: 索引无效, 随机")

            elif decision["action"] == "explore_frontier":
                i = decision["target_index"]
                if frontiers and i < len(frontiers):
                    fp = frontiers[i]
                    self.visited_frontier_set.add(tuple(np.round(fp["position"], 1)))
                    print(f" 探索前沿[{i}] dist={fp['distance']:.1f}m")
                    self._plan_path_pixels(fp["position"])
                    self.navigate_to(fp["position"])
                    self.path_pixels = []
                    self.nav_history.append(f"决策{self.decision_count}: 前沿[{i}] {fp['distance']:.1f}m")
                else:
                    print(" 无前沿, 随机")
                    rp = self.pf.get_random_navigable_point()
                    self._plan_path_pixels(rp)
                    self.navigate_to(rp)
                    self.path_pixels = []
                    self.nav_history.append(f"决策{self.decision_count}: 随机")

            if self.visited_targets >= set(self.cfg.TARGET_OBJECTS):
                print(f"\n 全部目标已找到: {list(self.visited_targets)}")
                break

        if self.total_steps >= self.cfg.MAX_STEPS:
            print(f"\n 步数耗尽 ({self.cfg.MAX_STEPS})")
            print(f"  已找到: {list(self.visited_targets)}")
            print(f"  未找到: {[t for t in self.cfg.TARGET_OBJECTS if t not in self.visited_targets]}")

        self._save()
        self.sim.close()

    def _save(self):
        if self.video_frames:
            h, w = self.video_frames[0].shape[:2]
            wr = cv2.VideoWriter(
                self.cfg.OUTPUT_VIDEO,
                cv2.VideoWriter_fourcc(*"DIVX"),
                self.cfg.VIDEO_FPS,
                (w, h),
            )
            for f in self.video_frames:
                wr.write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
            wr.release()
            print(f"[OUTPUT] 视频 -> {self.cfg.OUTPUT_VIDEO} ({len(self.video_frames)} 帧)")

        self.vlm.save_log(self.cfg.OUTPUT_LOG)

        print(f"\n{'=' * 60}")
        print(" 大模型完整思考过程")
        print(f"{'=' * 60}")
        for e in self.vlm.reasoning_log:
            print(f"\n--- 决策 #{e['decision_id']} ---")
            print(f"  位置: {e['agent_position']}")
            print(f"  检测: {e['detections_count']} 物体,  前沿: {e['frontiers_count']} 个")
            print(f"  动作: {e['decision']['action']}")
            print(f"  置信: {e['decision'].get('confidence', '-')}")
            print(f"  思考: {e['decision']['reasoning']}")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    import sys

    cfg = Config()
    if len(sys.argv) > 1:
        cfg.SCENE_PATH = sys.argv[1]
    if len(sys.argv) > 2:
        cfg.TARGET_OBJECTS = sys.argv[2].split(",")

    print("=" * 60)
    print("  Habitat + YOLO + 本地 Qwen3-VL 具身导航")
    print("=" * 60)
    print(f"  场景: {cfg.SCENE_PATH}")
    print(f"  目标: {cfg.TARGET_OBJECTS}")
    print(f"  YOLO: {cfg.YOLO_MODEL}")
    print(f"  VLM:  {cfg.MODEL_NAME} (local)")
    print("=" * 60)

    EmbodiedNavigator(cfg).run()
