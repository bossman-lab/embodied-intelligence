#!/usr/bin/env python3
"""
Visualize results from video2robot pipeline

Usage:
    # Show project info
    python scripts/visualize.py --project data/video_001

    # Visualize pose with viser (opens browser link)
    python scripts/visualize.py --project data/video_001 --pose

    # Visualize robot motion in viser (video overlay)
    python scripts/visualize.py --project data/video_001 --robot-viser
    python scripts/visualize.py --project data/video_001 --robot-viser --robot-track 2
    python scripts/visualize.py --project data/video_001 --robot-viser --robot-all

    # Visualize robot motion with MuJoCo
    python scripts/visualize.py --project data/video_001 --robot
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from video2robot.config import DATA_DIR, GMR_DIR, PROMPTHMR_DIR
from video2robot.pose.tracks import get_smplx_tracks
from video2robot.utils import run_in_conda


def _available_track_indices(project_dir: Path) -> list[int]:
    """Return sorted list of available track indices."""
    tracks = get_smplx_tracks(project_dir)
    indices = [info.index for info in tracks]
    return indices if indices else [1]


def show_project_info(project_dir: Path):
    """Show available files in project"""
    print(f"\n[Project] {project_dir}")
    print("-" * 50)
    
    files = {
        "original.mp4": "Original video",
        "config.json": "Project config (includes prompt)",
        "smplx.npz": "SMPL-X pose data",
        "results.pkl": "PromptHMR full results",
        "world4d.glb": "Blender/3D viewer file",
        "robot_motion.pkl": "Robot motion data",
        "robot_motion_twist.pkl": "Robot motion data (TWIST 23DOF)",
    }
    
    for filename, desc in files.items():
        filepath = project_dir / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  ✓ {filename:20} ({size_mb:.1f} MB) - {desc}")
        else:
            print(f"  ✗ {filename:20} - {desc}")
    
    print()
    print("[Visualization Commands]")
    print(f"  --pose       : Visualize pose with viser (browser)")
    print(f"  --robot-viser: Visualize robot with viser (video + camera, robot instead of human)")
    print(f"  --robot      : Visualize robot with MuJoCo")


def visualize_pose_viser(project_dir: Path, phmr_env: str):
    """Visualize pose using viser (with floor, camera, GUI controls)"""
    results_pkl = project_dir / "results.pkl"
    video_path = project_dir / "original.mp4"
    
    if not results_pkl.exists():
        print(f"[Error] results.pkl not found in {project_dir}")
        print(f"[Error] Run extract_pose.py first")
        return
    
    # Use PromptHMR's visualization script
    vis_script = PROMPTHMR_DIR / "scripts" / "visualize_results.py"
    
    argv = ["python", str(vis_script), "--results_dir", str(project_dir.absolute())]
    
    if video_path.exists():
        argv.extend(["--video", str(video_path.absolute())])
    
    print("[Pose] Starting viser visualization (with floor, camera, GUI)...")
    print(f"[Pose] Env: {phmr_env}")
    print("[Pose] Press Ctrl+C to stop")
    print()
    
    run_in_conda(phmr_env, argv, cwd=PROMPTHMR_DIR, raise_on_error=False)


def visualize_robot_viser(
    project_dir: Path,
    phmr_env: str,
    *,
    twist: bool = False,
    total: int = 1500,
    subsample: int = 1,
    cube_size: float = 0.03,
    proxy: bool = False,
    img_maxsize: int = 320,
    no_floor: bool = False,
    floor_margin: float = 1.5,
    frustum_scale: float = 0.4,
    frustum_fov: float = 0.96,
    robot_type: str | None = None,
    track_index: int = 1,
    all_tracks: bool = False,
    material_mode: str = "color",
):
    """Visualize robot motion in PromptHMR's viser scene (video + camera frustums)."""
    if twist:
        robot_motion_pkl = project_dir / "robot_motion_twist.pkl"
        if not robot_motion_pkl.exists():
            print(f"[RobotViser] TWIST motion not found, falling back to robot_motion.pkl")
            robot_motion_pkl = project_dir / "robot_motion.pkl"
    else:
        robot_motion_pkl = project_dir / "robot_motion.pkl"

    if not robot_motion_pkl.exists():
        print(f"[Error] robot motion not found in {project_dir}")
        print(f"[Error] Run: python scripts/convert_to_robot.py --project {project_dir}")
        return

    if not (project_dir / "results.pkl").exists():
        print(f"[Error] results.pkl not found in {project_dir}")
        print(f"[Error] Run extract_pose.py first")
        return

    if not (project_dir / "original.mp4").exists():
        print(f"[Error] original.mp4 not found in {project_dir}")
        return

    # Use script path relative to project root (works without package install)
    project_root = Path(__file__).parent.parent
    vis_script = project_root / "video2robot" / "visualization" / "robot_viser.py"
    if not vis_script.exists():
        print(f"[Error] robot viser script not found: {vis_script}")
        return

    argv = [
        "python",
        str(vis_script),
        "--project",
        str(project_dir.absolute()),
        "--total",
        str(int(total)),
        "--subsample",
        str(int(subsample)),
        "--cube-size",
        str(float(cube_size)),
        "--img-maxsize",
        str(int(img_maxsize)),
        "--floor-margin",
        str(float(floor_margin)),
        "--frustum-scale",
        str(float(frustum_scale)),
        "--frustum-fov",
        str(float(frustum_fov)),
    ]
    if all_tracks:
        argv.append("--all-tracks")
    elif track_index is not None:
        argv.extend(["--track-index", str(int(track_index))])
    if twist:
        argv.append("--twist")
    if proxy:
        argv.append("--proxy")
    if no_floor:
        argv.append("--no-floor")
    if robot_type:
        argv.extend(["--robot-type", str(robot_type)])
    if material_mode:
        argv.extend(["--material-mode", str(material_mode)])

    print("[RobotViser] Starting robot visualization in viser...")
    print(f"[RobotViser] Env: {phmr_env}")
    print("[RobotViser] Press Ctrl+C to stop")
    print()

    run_in_conda(phmr_env, argv, cwd=project_dir, raise_on_error=False)


def visualize_robot(project_dir: Path, robot_type: str, gmr_env: str, twist: bool = False):
    """Visualize robot motion using MuJoCo"""
    if twist:
        robot_motion_pkl = project_dir / "robot_motion_twist.pkl"
        if not robot_motion_pkl.exists():
            print(f"[Robot] TWIST motion not found, falling back to robot_motion.pkl")
            robot_motion_pkl = project_dir / "robot_motion.pkl"
    else:
        robot_motion_pkl = project_dir / "robot_motion.pkl"
    
    if not robot_motion_pkl.exists():
        print(f"[Error] robot_motion.pkl not found in {project_dir}")
        print(f"[Error] Run: python scripts/convert_to_robot.py --project {project_dir}")
        return
    
    print(f"[Robot] Visualizing: {robot_motion_pkl}")
    
    # Use GMR's visualization
    vis_script = GMR_DIR / "scripts" / "vis_robot_motion.py"
    
    if not vis_script.exists():
        print(f"[Error] GMR visualization script not found: {vis_script}")
        return
    
    argv = [
        "python",
        str(vis_script),
        "--robot",
        robot_type,
        "--robot_motion_path",
        str(robot_motion_pkl.absolute()),
    ]
    
    print(f"[Robot] Env: {gmr_env}")
    print(f"[Robot] Command: {' '.join(argv)}")
    run_in_conda(gmr_env, argv, cwd=GMR_DIR, raise_on_error=False)


def main():
    parser = argparse.ArgumentParser(description="Visualize video2robot results")
    
    parser.add_argument("--project", "-p", required=True, help="Project folder path")
    
    # Visualization options
    vis_group = parser.add_mutually_exclusive_group()
    vis_group.add_argument("--pose", action="store_true", help="Visualize pose with viser")
    vis_group.add_argument("--robot-viser", action="store_true", help="Visualize robot in viser (video + camera)")
    vis_group.add_argument("--robot", action="store_true", help="Visualize robot with MuJoCo")
    
    # Robot options
    # NOTE: keep default=None so that `--robot-viser` can fall back to the motion file's robot_type.
    # For `--robot` (MuJoCo), we will default to unitree_g1 if not provided.
    parser.add_argument("--robot-type", default=None, help="Robot type (default: unitree_g1 for --robot, motion file for --robot-viser)")
    parser.add_argument("--twist", action="store_true", help="Visualize TWIST 23DOF motion if available")

    # Robot-viser options
    parser.add_argument("--total", type=int, default=1500, help="Max video frames to load (robot-viser)")
    parser.add_argument("--subsample", type=int, default=1, help="Subsample frames for visualization (robot-viser)")
    parser.add_argument("--cube-size", type=float, default=0.03, help="Cube size (meters) for each link (robot-viser)")
    parser.add_argument("--proxy", action="store_true", help="Use proxy cubes instead of robot meshes (robot-viser)")
    parser.add_argument("--img-maxsize", type=int, default=0, help="Max image size for frustum textures (robot-viser, 0 means no resize)")
    parser.add_argument("--material-mode", choices=["color", "metal"], default="color", help="Robot appearance in robot-viser")
    parser.add_argument("--no-floor", action="store_true", help="Disable floor rendering (robot-viser)")
    parser.add_argument("--floor-margin", type=float, default=1.5, help="Floor margin around trajectory (robot-viser)")
    parser.add_argument("--frustum-scale", type=float, default=0.4, help="Video camera frustum scale (robot-viser)")
    parser.add_argument("--frustum-fov", type=float, default=0.96, help="Video camera frustum FOV in radians (robot-viser)")
    parser.add_argument("--robot-track", type=int, default=1, help="Track index to visualize for robot-viser (default=1)")
    parser.add_argument("--robot-all", action="store_true", help="Visualize every available track sequentially (robot-viser)")

    # Conda env options
    parser.add_argument("--phmr-env", default="phmr", help="Conda env name for PromptHMR visualization")
    parser.add_argument("--gmr-env", default="gmr", help="Conda env name for GMR visualization")

    args = parser.parse_args()
    
    project_dir = Path(args.project)
    if not project_dir.exists():
        parser.error(f"Project not found: {project_dir}")

    if args.robot_all and not args.robot_viser:
        print("[Warn] --robot-all has no effect without --robot-viser")
    
    if args.pose:
        visualize_pose_viser(project_dir, phmr_env=args.phmr_env)
    elif args.robot_viser:
        visualize_robot_viser(
            project_dir,
            phmr_env=args.phmr_env,
            twist=args.twist,
            total=args.total,
            subsample=args.subsample,
            cube_size=args.cube_size,
            proxy=args.proxy,
            img_maxsize=args.img_maxsize,
            no_floor=args.no_floor,
            floor_margin=args.floor_margin,
            frustum_scale=args.frustum_scale,
            frustum_fov=args.frustum_fov,
            robot_type=args.robot_type,
            track_index=args.robot_track,
            all_tracks=args.robot_all,
            material_mode=args.material_mode,
        )
    elif args.robot:
        visualize_robot(project_dir, args.robot_type or "unitree_g1", gmr_env=args.gmr_env, twist=args.twist)
    else:
        show_project_info(project_dir)


if __name__ == "__main__":
    main()
