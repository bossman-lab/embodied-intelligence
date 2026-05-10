"""
配置模块
========
统一管理 local 和 api 两种模式的所有参数。
"""

import os


class Config:
    # ── 场景 ──────────────────────────────────────────────────
    SCENE_PATH = "./data/scene_datasets/habitat-test-scenes/apartment_1.glb"
    TARGET_OBJECTS = ["chair", "couch", "tv"]

    # ── YOLO ──────────────────────────────────────────────────
    YOLO_MODEL = "yolov8n.pt"
    YOLO_CONF_THRESHOLD = 0.35

    # ── 本地 VLM (local 模式) ─────────────────────────────────
    LOCAL_MODEL_NAME = "/home/robot/navigation/Qwen3-VL-4B-Instruct"
    MODEL_DTYPE = "auto"
    MODEL_DEVICE_MAP = "auto"
    MODEL_MAX_NEW_TOKENS = 1024
    MODEL_TEMPERATURE = 0.3
    MODEL_TOP_P = 0.9
    MODEL_TOP_K = 50

    # ── API VLM (api 模式) ────────────────────────────────────
    API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    API_KEY = os.environ.get("DASHSCOPE_API_KEY", "your-api-key")
    API_MODEL_NAME = "qwen3-vl-8b-instruct"

    # ── 导航 ──────────────────────────────────────────────────
    MAX_STEPS = 500
    SPIN_STEPS = 12
    VISIBLE_RADIUS = 3.0
    MAP_RESOLUTION = 512
    AREA_THRESHOLD_M2 = 9
    TARGET_REACH_DIST = 1.5

    # ── 相机 ──────────────────────────────────────────────────
    IMAGE_WIDTH = 640
    IMAGE_HEIGHT = 480
    HFOV = 90
    SENSOR_HEIGHT = 1.5

    # ── 输出 ──────────────────────────────────────────────────
    OUTPUT_VIDEO = "navigation_output.avi"
    OUTPUT_LOG = "vlm_reasoning_log.json"
    VIDEO_FPS = 4
