"""Pose extraction using PromptHMR.

Extracts 3D human poses from video and outputs SMPL-X format.
Adds helpers to export every tracked person to individual SMPL-X files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

import numpy as np

from video2robot.config import PROMPTHMR_DIR


def _check_ffprobe() -> None:
    """Check if ffprobe is installed."""
    if shutil.which("ffprobe") is None:
        raise RuntimeError(
            "ffprobe not found. Install FFmpeg:\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  macOS: brew install ffmpeg"
        )


def get_video_fps(video_path: Path) -> float:
    """Get FPS from video file using ffprobe"""
    _check_ffprobe()
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "json",
        str(video_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        fps_str = data["streams"][0]["r_frame_rate"]
        num, den = map(int, fps_str.split("/"))
        return num / den
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError, ValueError, ZeroDivisionError):
        return 30.0  # fallback


_PROMPTHMR_TO_GMR_COORD_TRANSFORM = np.array(
    [
        [0, 0, -1],  # X_gmr = -Z_phmr
        [-1, 0, 0],  # Y_gmr = -X_phmr
        [0, 1, 0],  # Z_gmr =  Y_phmr
    ],
    dtype=np.float32,
)


def _score_person(person_dict: dict) -> tuple[int, float]:
    """Return (num_frames, median_bbox_area) for ranking."""
    frames = person_dict.get("frames", None)
    num_frames = int(len(frames)) if frames is not None else 0

    bbox_area = 0.0
    bboxes = person_dict.get("bboxes", None)
    if bboxes is not None and len(bboxes) > 0:
        try:
            b = np.asarray(bboxes)
            if b.ndim == 2 and b.shape[1] >= 4:
                area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
                bbox_area = float(np.nanmedian(area))
        except (ValueError, TypeError, IndexError):
            bbox_area = 0.0

    return num_frames, bbox_area


def get_ranked_track_ids(people: dict[str, dict]) -> list[str]:
    """Return track IDs sorted by heuristic score."""
    ranked: list[tuple[str, tuple[int, float]]] = []
    for key, person in people.items():
        ranked.append((key, _score_person(person)))

    if not ranked:
        return []

    ranked.sort(key=lambda item: item[1], reverse=True)
    return [key for key, _ in ranked]


def pick_best_track_id(people: dict) -> str:
    """Pick the top-ranked track (backwards-compatible helper)."""
    ranked = get_ranked_track_ids(people)
    if not ranked:
        raise ValueError("No people found in results.pkl")
    return ranked[0]


def convert_prompthmr_results_to_smplx_npz(
    results_dir: Path,
    output_path: Path,
    video_path: Optional[Path] = None,
    *,
    track_key: Optional[str] = None,
    track_index: Optional[int] = None,
    results_data: Optional[dict] = None,
) -> Path:
    """Convert PromptHMR results.pkl to a GMR-compatible SMPL-X npz.

    Args:
        results_dir: Directory containing results.pkl
        output_path: Output .npz path
        video_path: Original video path (to get correct FPS)
    """
    import joblib
    from scipy.spatial.transform import Rotation as R

    results_dir = Path(results_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_pkl = results_dir / "results.pkl"
    if not results_pkl.exists():
        raise FileNotFoundError(f"results.pkl not found: {results_pkl}")

    results = results_data if results_data is not None else joblib.load(results_pkl)

    people = results.get("people", {})
    if not people:
        raise ValueError("No people detected in video")

    ranked_tracks = get_ranked_track_ids(people)
    if not ranked_tracks:
        raise ValueError("No valid tracks available")

    resolved_track_key: Optional[str] = None
    if track_key is not None:
        if track_key not in people:
            raise ValueError(f"Track not found: {track_key}")
        resolved_track_key = track_key
    elif track_index is not None:
        if track_index < 1 or track_index > len(ranked_tracks):
            raise ValueError(f"Track index out of range: {track_index}")
        resolved_track_key = ranked_tracks[track_index - 1]
    else:
        resolved_track_key = ranked_tracks[0]

    resolved_index = ranked_tracks.index(resolved_track_key) + 1
    person = people[resolved_track_key]
    print(f"[PoseExtractor] Using track #{resolved_index}: {resolved_track_key}")

    smplx_world = person.get("smplx_world", {})
    if not smplx_world:
        raise ValueError("No world-coordinate SMPL-X data found")

    frames = person.get("frames", np.arange(len(smplx_world.get("pose", []))))
    num_frames = int(len(frames))

    poses_flat = smplx_world.get("pose", np.zeros((num_frames, 165)))
    shapes = smplx_world.get("shape", np.zeros((num_frames, 10)))
    trans_yup = smplx_world.get("trans", np.zeros((num_frames, 3)))

    poses = poses_flat.reshape(num_frames, 55, 3)

    # Get FPS from original video if provided, otherwise fallback
    if video_path is None:
        video_path = results_dir / "original.mp4"
    
    if video_path.exists():
        fps = get_video_fps(video_path)
        print(f"[PoseExtractor] FPS from video: {fps}")
    else:
        fps = float(results.get("fps", 30.0))
        print(f"[PoseExtractor] FPS from results.pkl (fallback): {fps}")

    # Translation: (N,3)
    trans_zup = trans_yup @ _PROMPTHMR_TO_GMR_COORD_TRANSFORM.T

    # Root orientation: axis-angle (N,3)
    root_orient_yup = poses[:, 0, :].reshape(num_frames, 3)
    root_orient_zup = np.zeros_like(root_orient_yup)
    for i in range(num_frames):
        rot_mat_yup = R.from_rotvec(root_orient_yup[i]).as_matrix()
        rot_mat_zup = _PROMPTHMR_TO_GMR_COORD_TRANSFORM @ rot_mat_yup
        root_orient_zup[i] = R.from_matrix(rot_mat_zup).as_rotvec()

    # Body pose: 21 joints (N,63)
    pose_body = poses[:, 1:22, :].reshape(num_frames, 63)

    # Betas: use mean over frames (10,)
    betas_mean = shapes.mean(axis=0) if len(shapes) > 0 else np.zeros(10)

    smplx_data = {
        "root_orient": root_orient_zup.astype(np.float32),
        "pose_body": pose_body.astype(np.float32),
        "betas": betas_mean.astype(np.float32),
        "trans": trans_zup.astype(np.float32),
        "gender": np.array("neutral"),
        "mocap_frame_rate": np.array(fps),
    }

    np.savez(output_path, **smplx_data)
    print(f"[PoseExtractor] Saved: {output_path}")
    return output_path


def convert_all_prompthmr_tracks_to_smplx(
    results_dir: Path,
    output_path: Path,
    video_path: Optional[Path] = None,
) -> dict:
    """Convert every tracked person to separate SMPL-X files.

    Returns:
        Metadata dictionary describing generated tracks.
    """
    import joblib

    results_dir = Path(results_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_pkl = results_dir / "results.pkl"
    if not results_pkl.exists():
        raise FileNotFoundError(f"results.pkl not found: {results_pkl}")

    results = joblib.load(results_pkl)
    people = results.get("people", {})
    track_keys = get_ranked_track_ids(people)
    if not track_keys:
        raise ValueError("No people detected in video")

    # Remove stale track files matching the base name.
    base_name = output_path.stem  # typically 'smplx'
    for old_file in output_path.parent.glob(f"{base_name}_track_*.npz"):
        try:
            old_file.unlink()
        except OSError:
            pass

    track_metadata: list[dict] = []
    track_paths: list[Path] = []
    for idx, track_key in enumerate(track_keys, start=1):
        track_out = output_path.parent / f"{base_name}_track_{idx}.npz"
        convert_prompthmr_results_to_smplx_npz(
            results_dir,
            track_out,
            video_path=video_path,
            track_key=track_key,
            results_data=results,
        )
        track_paths.append(track_out)

        num_frames, bbox_area = _score_person(people[track_key])
        track_metadata.append(
            {
                "index": idx,
                "track_id": track_key,
                "num_frames": num_frames,
                "median_bbox_area": bbox_area,
                "output": track_out.name,
            }
        )

    if track_paths:
        shutil.copy(track_paths[0], output_path)
        print(f"[PoseExtractor] Default track alias updated -> {output_path}")

    meta = {
        "base_file": output_path.name,
        "track_files": [p.name for p in track_paths],
        "tracks": track_metadata,
        "best_track_index": 1 if track_metadata else None,
    }

    meta_path = output_path.parent / f"{base_name}_tracks.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"[PoseExtractor] Track metadata saved: {meta_path}")
    return meta


class PoseExtractor:
    """Pose extractor using PromptHMR pipeline"""

    def __init__(
        self,
        static_camera: bool = False,
        conda_env: str = "phmr",
    ):
        """
        Initialize pose extractor

        Args:
            static_camera: Assume static camera (no SLAM)
            conda_env: Conda environment name for PromptHMR
        """
        self.static_camera = static_camera
        self.conda_env = conda_env

        # Verify PromptHMR exists
        if not PROMPTHMR_DIR.exists():
            raise FileNotFoundError(f"PromptHMR not found: {PROMPTHMR_DIR}")

    def extract(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Extract poses from video using PromptHMR

        Args:
            video_path: Input video path
            output_path: Output SMPL-X .npz path
            output_dir: Output directory for intermediate results

        Returns:
            Path to output SMPL-X file
        """
        video_path = Path(video_path).absolute()
        output_path = Path(output_path).absolute()
        
        if output_dir is None:
            output_dir = output_path.parent
        output_dir = Path(output_dir).absolute()
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[PoseExtractor] Processing: {video_path}")
        print(f"[PoseExtractor] Output: {output_path}")

        # Run PromptHMR (saves directly to output_dir)
        results_dir = self._run_prompthmr(video_path, output_dir)
        
        # Convert results to SMPL-X format for GMR
        self._convert_results(results_dir, output_path)
        
        print(f"[PoseExtractor] Done: {output_path}")
        return output_path

    def _run_prompthmr(self, video_path: Path, output_dir: Path) -> Path:
        """
        Run PromptHMR run_pipeline.py script
        
        Args:
            video_path: Input video path
            output_dir: Output directory (results saved directly here)

        Returns:
            Path to results directory (same as output_dir)
        """
        script_path = PROMPTHMR_DIR / "scripts" / "run_pipeline.py"
        
        cmd = [
            "python", str(script_path),
            "--input_video", str(video_path),
            "--output_folder", str(output_dir),
        ]
        
        if self.static_camera:
            cmd.append("--static_camera")

        print(f"[PoseExtractor] Running PromptHMR...")
        print(f"[PoseExtractor] Output folder: {output_dir}")
        print(f"[PoseExtractor] Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=str(PROMPTHMR_DIR))
        
        if result.returncode != 0:
            raise RuntimeError(f"PromptHMR failed with return code {result.returncode}")

        if not output_dir.exists():
            raise FileNotFoundError(f"Results not found: {output_dir}")

        return output_dir

    def _convert_results(
        self,
        results_dir: Path,
        output_path: Path,
    ):
        meta = convert_all_prompthmr_tracks_to_smplx(
            results_dir=results_dir,
            output_path=output_path,
            video_path=output_path.parent / "original.mp4",
        )
        num_tracks = len(meta.get("tracks", []))
        if num_tracks > 1:
            print(f"[PoseExtractor] Exported {num_tracks} SMPL-X tracks (track_1 defaults to {output_path.name})")
