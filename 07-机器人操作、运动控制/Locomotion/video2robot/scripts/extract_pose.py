#!/usr/bin/env python3
"""
Extract human poses from video using PromptHMR

Usage:
    python scripts/extract_pose.py --project data/video_001
    python scripts/extract_pose.py --project data/video_001 --static-camera
"""

import argparse
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from video2robot.config import PROMPTHMR_DIR
from video2robot.pose.extractor import convert_all_prompthmr_tracks_to_smplx
from video2robot.utils import emit_progress


def run_prompthmr(video_path: Path, output_dir: Path, static_camera: bool = False) -> Path:
    """Run PromptHMR pipeline via subprocess
    
    Args:
        video_path: Input video path
        output_dir: Output directory (project folder)
        static_camera: Assume static camera (skip SLAM)
    
    Returns:
        Path to results directory
    """
    script_path = PROMPTHMR_DIR / "scripts" / "run_pipeline.py"
    output_folder = str(output_dir.absolute())
    
    cmd = [
        "python", str(script_path),
        "--input_video", str(video_path.absolute()),
        "--output_folder", output_folder,
    ]
    
    if static_camera:
        cmd.append("--static_camera")
    
    print(f"[PromptHMR] Running pipeline...")
    print(f"[PromptHMR] Output folder: {output_folder}")
    print(f"[PromptHMR] Command: {' '.join(cmd)}")
    emit_progress("init", 0.05, "Starting pipeline")
    print()
    
    result = subprocess.run(cmd, cwd=str(PROMPTHMR_DIR))
    
    if result.returncode != 0:
        raise RuntimeError(f"PromptHMR failed with return code {result.returncode}")
    
    if not output_dir.exists():
        raise FileNotFoundError(f"Results not found: {output_dir}")
    
    return output_dir


def convert_prompthmr_results(project_dir: Path, output_path: Path, video_path: Path):
    """Convert PromptHMR results to SMPL-X and export every tracked person."""
    emit_progress("smplx", 0.90, "SMPL-X conversion")
    convert_all_prompthmr_tracks_to_smplx(
        results_dir=project_dir,
        output_path=output_path,
        video_path=video_path,
    )


def main():
    parser = argparse.ArgumentParser(description="Extract poses from video using PromptHMR")
    parser.add_argument("--project", "-p", required=True, 
                        help="Project folder path (e.g., data/video_001)")
    parser.add_argument("--static-camera", action="store_true", 
                        help="Assume static camera (skip SLAM)")

    args = parser.parse_args()

    project_dir = Path(args.project)
    if not project_dir.exists():
        parser.error(f"Project not found: {project_dir}")
    
    video_path = project_dir / "original.mp4"
    if not video_path.exists():
        parser.error(f"Video not found: {video_path}")
    
    output_path = project_dir / "smplx.npz"
    
    print(f"[Project] {project_dir}")
    print(f"[Input]   {video_path}")
    print(f"[Output]  {output_path}")
    
    run_prompthmr(video_path, project_dir, args.static_camera)
    convert_prompthmr_results(project_dir, output_path, video_path)

    emit_progress("done", 1.0, "Done")
    print(f"\nDone!")
    print(f"  Project: {project_dir}")
    print(f"  SMPL-X:  {output_path}")


if __name__ == "__main__":
    main()
