import sys
import os
import argparse

from config import Config
from vlm import create_vlm_engine
from navigator import EmbodiedNavigator


def parse_args():
    parser = argparse.ArgumentParser(
        description="Habitat + YOLO + VLM 具身导航系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default=os.environ.get("NAV_VLM_MODE", "local"),
        help="VLM 模式: local=本地Qwen3-VL, api=DashScope API (默认: local)",
    )
    parser.add_argument(
        "scene",
        nargs="?",
        default=None,
        help="场景文件路径 (.glb)，不传则使用 Config.SCENE_PATH",
    )
    parser.add_argument(
        "targets",
        nargs="?",
        default=None,
        help="目标物体列表，逗号分隔，如 chair,couch,tv",
    )
    return parser.parse_args()


def print_banner(cfg: Config, mode: str):
    print("=" * 60)
    print(f"  Habitat + YOLO + VLM 具身导航")
    print("=" * 60)
    print(f"  场景  : {cfg.SCENE_PATH}")
    print(f"  目标  : {cfg.TARGET_OBJECTS}")
    print(f"  YOLO  : {cfg.YOLO_MODEL}")
    if mode == "local":
        print(f"  VLM   : {cfg.LOCAL_MODEL_NAME}  [本地推理]")
    else:
        print(f"  VLM   : {cfg.API_MODEL_NAME}  [API: {cfg.API_BASE_URL}]")
    print(f"  步数上限: {cfg.MAX_STEPS}")
    print("=" * 60)


def main():
    args = parse_args()

    # 构建配置
    cfg = Config()
    if args.scene:
        cfg.SCENE_PATH = args.scene
    if args.targets:
        cfg.TARGET_OBJECTS = args.targets.split(",")

    mode = args.mode
    print_banner(cfg, mode)

    # 创建 VLM 引擎（local 或 api）
    print(f"\n 初始化 VLM 引擎 [{mode}] ...")
    vlm = create_vlm_engine(cfg, mode=mode)

    # 启动导航
    EmbodiedNavigator(cfg, vlm).run()


if __name__ == "__main__":
    main()
