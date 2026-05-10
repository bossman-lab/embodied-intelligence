#!/usr/bin/env python3
"""
Run the full video2robot pipeline

Automatically handles conda environment switching:
- Step 1-2: Runs in phmr environment (Veo/Sora + PromptHMR)
- Step 3: Runs in gmr environment (GMR retargeting)

Usage:
    # From action with Seedance (default) - uses BASE_PROMPT template
    python scripts/run_pipeline.py --action "Action sequence:
    The subject walks forward with four steps."

    # From action with Sora
    python scripts/run_pipeline.py --model sora --action "..."

    # From action with Sora Pro
    python scripts/run_pipeline.py --model sora-pro --action "..."

    # From raw prompt (no template)
    python scripts/run_pipeline.py --raw-prompt "A person dancing"

    # From existing project (continue from where you left off)
    python scripts/run_pipeline.py --project data/video_001
"""

import argparse
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from video2robot.config import DATA_DIR, PROJECT_ROOT
from video2robot.pose.tracks import get_smplx_tracks
from video2robot.utils import ensure_project_dir, run_in_conda


def run_video_generation(
    project_dir: Path,
    action: str | None,
    raw_prompt: str | None,
    veo_model: str,
    aspect_ratio: str,
    duration: int,
    phmr_env: str,
    force: bool = False,
    model: str = "veo",
    size: str = "1280x720",
):
    """Run video generation (Seedance/Veo/Sora) in phmr env via subprocess."""
    video_path = project_dir / "original.mp4"
    if video_path.exists() and not force:
        print(f"[Step 1/3] Video exists: {video_path} (use --force to regenerate)")
        return

    # Prefer using the CLI script to keep metadata behavior consistent (config.json).
    script_path = PROJECT_ROOT / "scripts" / "generate_video.py"

    # generate_video.py currently uses --name (folder under DATA_DIR). If project_dir is outside DATA_DIR,
    # it would generate into the wrong place, so we guard here.
    if project_dir.parent.resolve() != DATA_DIR.resolve():
        raise ValueError(
            f"Project dir must be under {DATA_DIR} when using --action/--raw-prompt. Got: {project_dir}"
        )

    argv = [
        "python",
        str(script_path),
        "--model",
        model,
        "--name",
        project_dir.name,
        "--duration",
        str(duration),
    ]

    # Add prompt option
    if action:
        argv.extend(["--action", action])
    else:
        argv.extend(["--raw-prompt", raw_prompt])

    # Add provider-specific options
    if model in ("sora", "sora-pro"):
        argv.extend(["--size", size])
    else:
        argv.extend(["--veo-model", veo_model, "--aspect-ratio", aspect_ratio])

    if model == "sora-pro":
        model_name = "Sora Pro"
    elif model == "sora":
        model_name = "Sora"
    elif model == "veo":
        model_name = "Veo"
    else:
        model_name = "Seedance"
    print(f"\n[Step 1/3] Generating video with {model_name} (env={phmr_env})...")
    print(f"[Step 1/3] Command: {' '.join(argv)}")
    run_in_conda(phmr_env, argv, cwd=PROJECT_ROOT)


def run_pose_extraction(project_dir: Path, static_camera: bool, phmr_env: str, force: bool = False):
    """Run PromptHMR pose extraction in phmr env via subprocess."""
    smplx_path = project_dir / "smplx.npz"
    if smplx_path.exists() and not force:
        print(f"[Step 2/3] SMPL-X exists: {smplx_path} (use --force to regenerate)")
        return

    script_path = PROJECT_ROOT / "scripts" / "extract_pose.py"
    argv = ["python", str(script_path), "--project", str(project_dir)]
    if static_camera:
        argv.append("--static-camera")

    print(f"\n[Step 2/3] Extracting poses with PromptHMR (env={phmr_env})...")
    print(f"[Step 2/3] Command: {' '.join(argv)}")
    run_in_conda(phmr_env, argv, cwd=PROJECT_ROOT)


def run_video_copy(project_dir: Path, video: str, force: bool = False):
    """Copy an existing video into the project as original.mp4."""
    video_path = project_dir / "original.mp4"
    if video_path.exists() and not force:
        print(f"[Step 1/3] Video exists: {video_path} (use --force to overwrite)")
        return

    src = Path(video)
    if not src.exists():
        raise FileNotFoundError(f"Video not found: {src}")

    project_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, video_path)
    print(f"\n[Step 1/3] Using existing video: {video_path}")


def run_robot_retargeting(
    project_dir: Path,
    robot_type: str,
    gmr_env: str,
    no_twist: bool = False,
    force: bool = False,
    track_index: int | None = None,
    all_tracks: bool = False,
):
    """Run robot retargeting in gmr conda environment via subprocess."""
    script_path = PROJECT_ROOT / "scripts" / "convert_to_robot.py"

    if not force:
        if all_tracks:
            tracks = get_smplx_tracks(project_dir)
            if tracks:
                missing = []
                for track in tracks:
                    path = project_dir / f"robot_motion_track_{track.index}.pkl"
                    if not path.exists():
                        missing.append(track.index)
                if not missing:
                    print("[Step 3/3] Robot motions for all tracks already exist (use --force to regenerate)")
                    return
        else:
            if track_index is None:
                robot_path = project_dir / "robot_motion.pkl"
            else:
                robot_path = project_dir / f"robot_motion_track_{track_index}.pkl"
            if robot_path.exists():
                print(f"[Step 3/3] Robot motion exists: {robot_path} (use --force to regenerate)")
                return
    
    argv = ["python", str(script_path), "--project", str(project_dir), "--robot", robot_type]
    if all_tracks:
        argv.append("--all-tracks")
    elif track_index is not None:
        argv.extend(["--track-index", str(track_index)])
    if no_twist:
        argv.append("--no-twist")

    print(f"\n[Step 3/3] Retargeting to {robot_type} (env={gmr_env})...")
    print(f"[Step 3/3] Command: {' '.join(argv)}")
    run_in_conda(gmr_env, argv, cwd=PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(
        description="Video to Robot Motion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--action", "-a", help="Action sequence (uses BASE_PROMPT template)")
    input_group.add_argument("--raw-prompt", "-p", help="Raw prompt without BASE_PROMPT template")
    input_group.add_argument("--video", "-v", help="Path to an existing video file")
    input_group.add_argument("--project", help="Existing project folder (continue pipeline)")

    # Output options
    output_group = parser.add_argument_group("Output")
    output_group.add_argument("--name", "-n", help="Project folder name (default: video_XXX)")

    # Robot options
    robot_group = parser.add_argument_group("Robot")
    robot_group.add_argument("--robot", "-r", default="unitree_g1", help="Target robot type")
    robot_group.add_argument("--no-twist", action="store_true", 
                            help="Skip TWIST-compatible motion (23 DOF, default: generate both)")
    robot_group.add_argument("--robot-track", type=int, help="Retarget only this SMPL track (default: all tracks)")

    # Environment options
    env_group = parser.add_argument_group("Environments")
    env_group.add_argument("--phmr-env", default="phmr", help="Conda env name for Veo/PromptHMR")
    env_group.add_argument("--gmr-env", default="gmr", help="Conda env name for GMR retargeting")

    # Video generation options
    video_group = parser.add_argument_group("Video Generation")
    video_group.add_argument("--model", "-m", default="seedance",
                             choices=["seedance", "veo", "sora", "sora-pro"],
                             help="Video generation model (default: seedance)")
    video_group.add_argument("--duration", type=int, default=8,
                             help="Video duration in seconds (Seedance: e.g. 8, Veo: 4-8, Sora: 4/8/12)")
    # Veo-specific
    video_group.add_argument("--veo-model", default="veo-3.1-fast-generate-preview", help="Veo model ID")
    video_group.add_argument("--aspect-ratio", default="16:9", choices=["16:9", "9:16"],
                             help="Aspect ratio for Veo")
    # Sora-specific
    video_group.add_argument("--size", default="1280x720",
                             choices=["720x1280", "1280x720", "1024x1792", "1792x1024"],
                             help="Video size for Sora (default: 1280x720)")

    # Pose options
    pose_group = parser.add_argument_group("Pose")
    pose_group.add_argument("--static-camera", action="store_true", help="Assume static camera")

    # Pipeline control
    control_group = parser.add_argument_group("Pipeline Control")
    control_group.add_argument("--skip-veo", action="store_true", help="Skip video generation")
    control_group.add_argument("--skip-pose", action="store_true", help="Skip pose extraction")
    control_group.add_argument("--skip-robot", action="store_true", help="Skip robot retargeting")
    control_group.add_argument("--force", "-f", action="store_true", 
                              help="Regenerate files even if they exist")

    args = parser.parse_args()

    if args.robot_track is not None and args.robot_track < 1:
        parser.error("--robot-track must be >= 1")

    # Determine project directory
    if args.project:
        project_dir = Path(args.project)
        if not project_dir.exists():
            parser.error(f"Project not found: {project_dir}")
    else:
        project_dir = ensure_project_dir(name=args.name)

    print(f"\n{'='*60}")
    print(f"[Pipeline] Project: {project_dir}")
    print(f"{'='*60}")

    video_path = project_dir / "original.mp4"
    smplx_path = project_dir / "smplx.npz"

    # ================================================================
    # Step 1: Video Generation (phmr environment)
    # ================================================================
    if (args.action or args.raw_prompt) and not args.skip_veo:
        run_video_generation(
            project_dir=project_dir,
            action=args.action,
            raw_prompt=args.raw_prompt,
            veo_model=args.veo_model,
            aspect_ratio=args.aspect_ratio,
            duration=args.duration,
            phmr_env=args.phmr_env,
            force=args.force,
            model=args.model,
            size=args.size,
        )

    elif args.video:
        run_video_copy(project_dir=project_dir, video=args.video, force=args.force)

    elif video_path.exists():
        print(f"[Step 1/3] Video exists: {video_path}")
    
    else:
        print(f"[Step 1/3] Skipped (no video)")

    # ================================================================
    # Step 2: Pose Extraction (phmr environment)
    # ================================================================
    if not args.skip_pose and video_path.exists():
        run_pose_extraction(
            project_dir=project_dir,
            static_camera=args.static_camera,
            phmr_env=args.phmr_env,
            force=args.force,
        )
    
    else:
        print(f"[Step 2/3] Skipped")

    # ================================================================
    # Step 3: Robot Retargeting (gmr environment via subprocess)
    # ================================================================
    if not args.skip_robot and smplx_path.exists():
        run_robot_retargeting(
            project_dir=project_dir,
            robot_type=args.robot,
            gmr_env=args.gmr_env,
            no_twist=args.no_twist,
            force=args.force,
            track_index=args.robot_track,
            all_tracks=args.robot_track is None,
        )
    
    else:
        print(f"[Step 3/3] Skipped")

    # Summary
    print(f"\n{'='*60}")
    print(f"[Pipeline] Complete!")
    print(f"{'='*60}")
    print(f"  Project: {project_dir}")
    
    if project_dir.exists():
        for f in sorted(project_dir.iterdir()):
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"    - {f.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
