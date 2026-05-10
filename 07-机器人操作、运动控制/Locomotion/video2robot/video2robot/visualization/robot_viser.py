#!/usr/bin/env python3
"""Visualize robot motion in PromptHMR viser scene.

Goal:
  Original video + robot overlay (replacing SMPL mesh).

Implementation strategy:
  - Reuse PromptHMR's `viser_vis_world4d()` GUI + camera-frustum + video handling.
  - Add a simple ground plane (Y-up => floor at y=0).
  - Render the robot using its MuJoCo visual meshes (from GMR assets), not proxies.
    - Load MJCF XML (e.g., `assets/unitree_g1/g1_mocap_29dof.xml`).
    - Load mesh files referenced by `<asset><mesh ... file=.../>` (STL/OBJ supported).
    - For each body, attach its visual geom meshes under a viser frame.
    - Animate by updating body frame poses (position + orientation) each timestep.

Run (inside phmr env):
  python video2robot/visualization/robot_viser.py --project data/video_001
  # or via visualize.py wrapper:
  python scripts/visualize.py --project data/video_001 --robot-viser
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import cv2
import joblib
import numpy as np
import trimesh
import viser
from scipy.spatial.transform import Rotation as R

# Make video2robot importable when running as a script
_REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from video2robot.config import GMR_DIR
from video2robot.pose.tracks import get_smplx_tracks
from video2robot.pose.extractor import (
    _PROMPTHMR_TO_GMR_COORD_TRANSFORM,
    get_ranked_track_ids,
)

# IMPORTANT:
# Do NOT import `general_motion_retargeting` as a package here.
# Its `__init__.py` may pull in heavy optional deps (e.g., `mink`, MuJoCo).
# For this visualization we only need:
# - robot MJCF xml path (from GMR assets)
# - forward kinematics (we implement a small MJCF kinematics parser below)
GMR_ASSET_ROOT = (Path(GMR_DIR) / "assets").resolve()
ROBOT_XML_DICT: dict[str, Path] = {
    # Keep this in sync with GMR's `general_motion_retargeting/params.py`.
    "unitree_g1": GMR_ASSET_ROOT / "unitree_g1" / "g1_mocap_29dof.xml",
    "unitree_g1_with_hands": GMR_ASSET_ROOT / "unitree_g1" / "g1_mocap_29dof_with_hands.xml",
    "unitree_h1": GMR_ASSET_ROOT / "unitree_h1" / "h1.xml",
    "unitree_h1_2": GMR_ASSET_ROOT / "unitree_h1_2" / "h1_2_handless.xml",
    "booster_t1": GMR_ASSET_ROOT / "booster_t1" / "T1_serial.xml",
    "booster_t1_29dof": GMR_ASSET_ROOT / "booster_t1_29dof" / "t1_mocap.xml",
    "stanford_toddy": GMR_ASSET_ROOT / "stanford_toddy" / "toddy_mocap.xml",
    "fourier_n1": GMR_ASSET_ROOT / "fourier_n1" / "n1_mocap.xml",
    "engineai_pm01": GMR_ASSET_ROOT / "engineai_pm01" / "pm_v2.xml",
    "kuavo_s45": GMR_ASSET_ROOT / "kuavo_s45" / "biped_s45_collision.xml",
    "hightorque_hi": GMR_ASSET_ROOT / "hightorque_hi" / "hi_25dof.xml",
    "galaxea_r1pro": GMR_ASSET_ROOT / "galaxea_r1pro" / "r1_pro.xml",
    "berkeley_humanoid_lite": GMR_ASSET_ROOT / "berkeley_humanoid_lite" / "bhl_scene.xml",
    "booster_k1": GMR_ASSET_ROOT / "booster_k1" / "K1_serial.xml",
    "pnd_adam_lite": GMR_ASSET_ROOT / "pnd_adam_lite" / "scene.xml",
    "tienkung": GMR_ASSET_ROOT / "tienkung" / "mjcf" / "tienkung.xml",
    "pal_talos": GMR_ASSET_ROOT / "pal_talos" / "talos.xml",
}


_TRACK_COLORS = [
    (80, 200, 255),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
    (140, 86, 75),
    (227, 119, 194),
    (127, 127, 127),
    (188, 189, 34),
    (23, 190, 207),
]

_TRACK_COLOR_NAMES = [
    "Sky Blue",
    "Orange",
    "Green",
    "Red",
    "Purple",
    "Brown",
    "Pink",
    "Gray",
    "Olive",
    "Teal",
]


@dataclass
class RobotEntry:
    track_index: int
    track_key: str
    motion_path: Path
    robot_type: str
    robot_fps: float
    num_frames: int
    root_pos: np.ndarray  # (N,3) Z-up
    root_rot: np.ndarray  # (N,4) xyzw
    dof_pos: np.ndarray   # (N,D)
    root_pos_yup: np.ndarray  # (N,3)
    vis_to_robot: List[int]
    color: tuple[int, int, int]
    local_body_pos: np.ndarray | None = None  # (N,L,3) from motion (optional)
    body_pos_yup: np.ndarray | None = None  # (N,B,3)
    body_rot_wxyz_yup: np.ndarray | None = None  # (N,B,4)
    proxy_frames: List = field(default_factory=list)
    body_frames: Dict[str, object] = field(default_factory=dict)
    visible_toggle: object | None = None


def _color_for_track(index: int) -> tuple[int, int, int]:
    return _TRACK_COLORS[(index - 1) % len(_TRACK_COLORS)]


def _color_name_for_track(index: int) -> str:
    return _TRACK_COLOR_NAMES[(index - 1) % len(_TRACK_COLOR_NAMES)]

def _get_track_order(project_dir: Path, people: dict[str, dict]) -> list[str]:
    """Load track order from metadata if available, otherwise fallback to heuristic."""
    meta_path = project_dir / "smplx_tracks.json"

    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            ordered: list[str] = []
            for track in meta.get("tracks", []):
                track_id = track.get("track_id")
                if track_id in people:
                    ordered.append(track_id)

            # Append any missing tracks (e.g., metadata stale)
            for key in get_ranked_track_ids(people):
                if key not in ordered:
                    ordered.append(key)

            if ordered:
                return ordered
        except Exception as exc:
            print(f"[RobotViser] Warning: failed to parse {meta_path}: {exc}")

    return get_ranked_track_ids(people)


def _resolve_track_selection(
    project_dir: Path,
    people: dict[str, dict],
    *,
    all_tracks: bool,
    explicit_tracks: list[int] | None,
    default_track: int,
) -> tuple[list[int], dict[int, str]]:
    track_infos = get_smplx_tracks(project_dir)
    if not track_infos:
        raise SystemExit(f"No SMPL-X tracks found in {project_dir}. Run extract_pose.py first.")

    track_order = _get_track_order(project_dir, people)
    index_to_key: dict[int, str] = {}
    for info in track_infos:
        key = info.track_id
        if not key:
            order_idx = info.index - 1
            if 0 <= order_idx < len(track_order):
                key = track_order[order_idx]
        if key:
            index_to_key[info.index] = key

    if all_tracks:
        indices = [info.index for info in track_infos]
    elif explicit_tracks:
        indices = sorted({idx for idx in explicit_tracks if idx >= 1})
    else:
        indices = [max(1, default_track)]

    valid_indices: list[int] = []
    for idx in indices:
        if idx not in index_to_key:
            print(f"[RobotViser] Warning: Track #{idx} not found in metadata/results, skipping")
            continue
        valid_indices.append(idx)

    if not valid_indices:
        raise SystemExit("No valid tracks selected for visualization.")

    return valid_indices, index_to_key


def _motion_path_for_track(project_dir: Path, track_index: int, *, twist: bool) -> Path | None:
    suffix = "_twist" if twist else ""
    candidate = project_dir / f"robot_motion_track_{track_index}{suffix}.pkl"
    if candidate.exists():
        return candidate

    if track_index == 1:
        fallback = project_dir / f"robot_motion{suffix}.pkl"
        if fallback.exists():
            print(f"[RobotViser] Track #{track_index}: falling back to {fallback.name}")
            return fallback
    return None


def _prepare_robot_entry(
    *,
    track_index: int,
    track_key: str,
    motion_path: Path,
    video_fps: float,
    num_vis_frames: int,
    subsample: int,
) -> RobotEntry:
    with open(motion_path, "rb") as f:
        motion = pickle.load(f)

    robot_fps = float(motion.get("fps", 30.0))
    root_pos = np.asarray(motion["root_pos"], dtype=np.float32)
    root_rot = np.asarray(motion["root_rot"], dtype=np.float32)
    dof_pos = np.asarray(motion["dof_pos"], dtype=np.float32)
    local_body_pos_raw = motion.get("local_body_pos", None)
    if local_body_pos_raw is None:
        local_body_pos = None
    else:
        local_body_pos = np.asarray(local_body_pos_raw, dtype=np.float32)
    robot_type_motion = str(motion.get("robot_type", "unitree_g1"))

    if root_pos.ndim != 2 or root_pos.shape[1] != 3:
        raise SystemExit(f"Invalid root_pos in {motion_path}")
    if root_rot.ndim != 2 or root_rot.shape[1] != 4:
        raise SystemExit(f"Invalid root_rot in {motion_path}")
    if dof_pos.ndim != 2:
        raise SystemExit(f"Invalid dof_pos in {motion_path}")

    T = _PROMPTHMR_TO_GMR_COORD_TRANSFORM.astype(np.float32)
    root_pos_yup = root_pos @ T

    vis_to_robot: list[int] = []
    num_robot_frames = int(root_pos.shape[0])
    for vis_idx in range(num_vis_frames):
        orig_idx = vis_idx * max(1, subsample)
        t_sec = float(orig_idx) / float(max(video_fps, 1e-6))
        r_idx = int(round(t_sec * robot_fps))
        r_idx = max(0, min(num_robot_frames - 1, r_idx))
        vis_to_robot.append(r_idx)

    entry = RobotEntry(
        track_index=track_index,
        track_key=track_key,
        motion_path=motion_path,
        robot_type=robot_type_motion,
        robot_fps=robot_fps,
        num_frames=num_robot_frames,
        root_pos=root_pos,
        root_rot=root_rot,
        dof_pos=dof_pos,
        root_pos_yup=root_pos_yup,
        vis_to_robot=vis_to_robot,
        color=_color_for_track(track_index),
        local_body_pos=local_body_pos if local_body_pos.ndim == 3 else None,
    )
    return entry


def _compute_body_poses(
    entry: RobotEntry,
    kin_model: KinematicsModelLite,
    *,
    device,
    T: np.ndarray,
):
    import torch

    body_pos_t, body_rot_t = kin_model.forward_kinematics(
        torch.from_numpy(entry.root_pos).float().to(device),
        torch.from_numpy(entry.root_rot).float().to(device),
        torch.from_numpy(entry.dof_pos).float().to(device),
    )
    body_pos_zup = body_pos_t.numpy().astype(np.float32, copy=False)
    body_rot_zup = body_rot_t.numpy().astype(np.float32, copy=False)

    body_pos_yup = body_pos_zup @ T
    flat_q = body_rot_zup.reshape(-1, 4)
    flat_Rz = R.from_quat(flat_q).as_matrix().astype(np.float32, copy=False)
    flat_Ry = np.einsum("ij,njk->nik", T.T, flat_Rz).astype(np.float32, copy=False)
    flat_qy_xyzw = R.from_matrix(flat_Ry).as_quat().astype(np.float32, copy=False)
    flat_qy_wxyz = flat_qy_xyzw[:, [3, 0, 1, 2]]
    body_rot_wxyz_yup = flat_qy_wxyz.reshape(entry.num_frames, len(kin_model.body_names), 4)

    entry.body_pos_yup = body_pos_yup
    entry.body_rot_wxyz_yup = body_rot_wxyz_yup


def _load_video_frames(video_path: Path, *, max_frames: int | None) -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(str(video_path))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if not np.isfinite(fps) or fps <= 1e-6:
        fps = 30.0

    frames: list[np.ndarray] = []
    while True:
        if max_frames is not None and len(frames) >= max_frames:
            break
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)

    cap.release()
    return frames, fps


def _maybe_resize_rgb(img: np.ndarray, *, img_maxsize: int) -> np.ndarray:
    if img_maxsize <= 0:
        return img
    h, w = img.shape[:2]
    if max(h, w) <= img_maxsize:
        return img
    scale = float(img_maxsize) / float(max(h, w))
    return cv2.resize(img, None, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _parse_floats(s: str | None, *, n: int | None = None, default: tuple[float, ...] | None = None) -> np.ndarray:
    if s is None:
        if default is None:
            raise ValueError("Missing attribute and no default provided")
        arr = np.asarray(default, dtype=np.float32)
    else:
        arr = np.fromstring(s, dtype=np.float32, sep=" ")
    if n is not None and arr.size != n:
        raise ValueError(f"Expected {n} floats, got {arr.size}: {s!r}")
    return arr


def _quat_wxyz_to_xyzw(q_wxyz: np.ndarray) -> np.ndarray:
    q = np.asarray(q_wxyz, dtype=np.float32).reshape(4)
    return np.array([q[1], q[2], q[3], q[0]], dtype=np.float32)


def _make_floor_mesh_from_root_traj(root_pos_yup: np.ndarray, *, margin: float = 1.0, y: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Simple square floor in XZ plane (Y-up)."""
    if root_pos_yup.ndim != 2 or root_pos_yup.shape[1] != 3:
        raise ValueError("root_pos_yup must be (N,3)")

    xs = root_pos_yup[:, 0]
    zs = root_pos_yup[:, 2]
    min_x = float(np.nanmin(xs)) - float(margin)
    max_x = float(np.nanmax(xs)) + float(margin)
    min_z = float(np.nanmin(zs)) - float(margin)
    max_z = float(np.nanmax(zs)) + float(margin)

    v = np.array(
        [
            [min_x, y, min_z],
            [max_x, y, min_z],
            [max_x, y, max_z],
            [min_x, y, max_z],
        ],
        dtype=np.float32,
    )
    # IMPORTANT:
    # Keep a consistent winding so the normal points +Y (up).
    # We render the mesh as double-sided via `side="double"` when adding it to the scene.
    f = np.array([[0, 2, 1], [0, 3, 2]], dtype=np.int32)  # +Y normal
    return v, f


def _load_mesh_as_trimesh(path: Path, scale: np.ndarray) -> trimesh.Trimesh:
    """Load mesh file and return trimesh object with smooth normals.

    Args:
        path: Path to STL/OBJ mesh file
        scale: Scale factors (3,) to apply to vertices

    Returns:
        trimesh.Trimesh object with fixed normals for smooth shading
    """
    mesh = trimesh.load(str(path), force='mesh')

    # Apply scale
    mesh.vertices = mesh.vertices * scale

    # Fix normals for smooth shading
    mesh.fix_normals()

    return mesh


def _load_robot_visual_geoms(xml_path: Path):
    """Parse MJCF and load visual meshes per body using trimesh for smooth normals.

    Returns:
        body_geoms: dict[str, list[dict]] where each geom has:
            - trimesh: trimesh.Trimesh object in BODY-local frame with smooth normals
            - color (tuple[int,int,int])
            - mesh_name: str
    """
    xml_path = Path(xml_path)
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    compiler = root.find("compiler")
    meshdir = compiler.attrib.get("meshdir", "") if compiler is not None else ""
    mesh_base = (xml_path.parent / meshdir).resolve() if meshdir else xml_path.parent.resolve()

    # Asset meshes: name -> (file_path, scale_xyz)
    asset_mesh: dict[str, tuple[Path, np.ndarray]] = {}
    asset = root.find("asset")
    if asset is not None:
        for m in asset.findall("mesh"):
            name = m.attrib.get("name")
            file = m.attrib.get("file")
            if not name or not file:
                continue
            scale = _parse_floats(m.attrib.get("scale"), n=3, default=(1.0, 1.0, 1.0))
            mesh_path = (mesh_base / file).resolve()
            asset_mesh[name] = (mesh_path, scale)

    body_geoms: dict[str, list[dict]] = {}
    mesh_cache: dict[tuple[str, float, float, float], trimesh.Trimesh] = {}

    worldbody = root.find("worldbody")
    if worldbody is None:
        return body_geoms

    def visit_body(body_node: ET.Element):
        body_name = body_node.attrib.get("name", "")
        if body_name:
            geoms = []
            seen_geom_keys: set[tuple] = set()
            for geom in body_node.findall("geom"):
                gtype = geom.attrib.get("type", "sphere")
                if gtype != "mesh":
                    continue
                mesh_name = geom.attrib.get("mesh")
                if not mesh_name or mesh_name not in asset_mesh:
                    continue

                mesh_path, mesh_scale = asset_mesh[mesh_name]
                if not mesh_path.exists():
                    # Mesh files may be gitignored; still should exist on disk.
                    raise FileNotFoundError(f"Mesh file not found: {mesh_path} (mesh={mesh_name})")

                cache_key = (str(mesh_path), float(mesh_scale[0]), float(mesh_scale[1]), float(mesh_scale[2]))
                if cache_key in mesh_cache:
                    base_mesh = mesh_cache[cache_key]
                else:
                    print(f"[RobotViser]   loading mesh: {mesh_path.name}")
                    base_mesh = _load_mesh_as_trimesh(mesh_path, mesh_scale)
                    mesh_cache[cache_key] = base_mesh

                # Geom local transform in the BODY frame
                pos = _parse_floats(geom.attrib.get("pos"), n=3, default=(0.0, 0.0, 0.0))
                quat_wxyz = _parse_floats(geom.attrib.get("quat"), n=4, default=(1.0, 0.0, 0.0, 0.0))
                quat_xyzw = _quat_wxyz_to_xyzw(quat_wxyz)

                # Deduplicate identical visual geoms (many MJCFs repeat the same mesh twice).
                key = (
                    str(mesh_name),
                    tuple(np.round(pos, 6).tolist()),
                    tuple(np.round(quat_xyzw, 6).tolist()),
                )
                if key in seen_geom_keys:
                    continue
                seen_geom_keys.add(key)

                # Create a copy and apply local transform
                mesh_copy = base_mesh.copy()

                # Build 4x4 transform matrix from quaternion and position
                rot_mat = R.from_quat(quat_xyzw).as_matrix()
                transform = np.eye(4, dtype=np.float64)
                transform[:3, :3] = rot_mat
                transform[:3, 3] = pos
                mesh_copy.apply_transform(transform)

                rgba = _parse_floats(geom.attrib.get("rgba"), n=4, default=(0.7, 0.7, 0.7, 1.0))
                color = (int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))

                geoms.append({"trimesh": mesh_copy, "color": color, "mesh_name": mesh_name})

            if geoms:
                body_geoms[body_name] = geoms

        for child in body_node.findall("body"):
            visit_body(child)

    for top_body in worldbody.findall("body"):
        visit_body(top_body)

    return body_geoms


def _torch_quat_mul(a, b):
    """Hamilton product for quaternions in xyzw (Torch)."""
    import torch

    ax, ay, az, aw = torch.unbind(a, dim=-1)
    bx, by, bz, bw = torch.unbind(b, dim=-1)
    x = aw * bx + ax * bw + ay * bz - az * by
    y = aw * by - ax * bz + ay * bw + az * bx
    z = aw * bz + ax * by - ay * bx + az * bw
    w = aw * bw - ax * bx - ay * by - az * bz
    return torch.stack([x, y, z, w], dim=-1)


def _torch_quat_rotate(q, v):
    """Rotate vectors by quaternion (xyzw) in Torch."""
    import torch

    q_vec = q[..., :3]
    q_w = q[..., 3:4]
    uv = torch.cross(q_vec, v, dim=-1)
    uuv = torch.cross(q_vec, uv, dim=-1)
    return v + 2.0 * (q_w * uv + uuv)


def _torch_quat_from_expmap(exp_map):
    """Convert exponential-map (axis-angle vector) to quaternion xyzw (Torch)."""
    import torch

    exp_map = exp_map
    angle = torch.linalg.norm(exp_map, dim=-1, keepdim=True).clamp(min=1e-9)
    half = 0.5 * angle
    sin_half_over_angle = torch.sin(half) / angle
    xyz = exp_map * sin_half_over_angle
    w = torch.cos(half)
    return torch.cat([xyz, w], dim=-1)


def _torch_quat_from_axis_angle(axis, angle):
    """Convert axis + angle(rad) to quaternion xyzw (Torch)."""
    import torch

    axis = axis / torch.linalg.norm(axis, dim=-1, keepdim=True).clamp(min=1e-9)
    half = 0.5 * angle.unsqueeze(-1)
    xyz = axis * torch.sin(half)
    w = torch.cos(half)
    return torch.cat([xyz, w], dim=-1)


class _JointLite:
    def __init__(self, name: str, dof_dim: int, axis):
        self.name = name
        self.dof_dim = int(dof_dim)
        self.axis = axis  # torch tensor (3,) on model device or None
        self.dof_idx = -1

    def set_dof_idx(self, idx: int) -> None:
        self.dof_idx = int(idx)

    def dof_to_quat(self, dof):
        import torch

        if self.dof_dim == 0:
            out = torch.zeros((*dof.shape[:-1], 4), dtype=dof.dtype, device=dof.device)
            out[..., 3] = 1.0
            return out
        if self.dof_dim == 1:
            ang = dof.squeeze(-1)
            axis = self.axis
            axis = torch.broadcast_to(axis, (*ang.shape, 3))
            return _torch_quat_from_axis_angle(axis, ang)
        if self.dof_dim == 3:
            return _torch_quat_from_expmap(dof)
        raise ValueError(f"Unsupported dof_dim={self.dof_dim} for joint={self.name}")


class KinematicsModelLite:
    """A minimal MJCF kinematics model (no GMR imports).

    Matches GMR's traversal order and quaternion conventions:
    - MJCF body `quat` is wxyz; internally we use xyzw.
    - Root pose is provided externally as (root_pos, root_rot_xyzw).
    - dof_pos ordering follows a DFS pre-order over bodies (same as GMR).
    """

    def __init__(self, xml_path: Path, *, device=None):
        import torch

        self.xml_path = Path(xml_path)
        self.device = device or torch.device("cpu")

        self.body_names: list[str] = []
        self.parent_indices: list[int] = []
        self.local_translation: list[np.ndarray] = []
        self.local_rotation: list[np.ndarray] = []
        self.joints: list[_JointLite] = []
        self._dof_size: list[int] = []

        self._build()
        self._set_dof_indices()

        self.local_translation_t = torch.tensor(np.asarray(self.local_translation), dtype=torch.float32, device=self.device)
        self.local_rotation_t = torch.tensor(np.asarray(self.local_rotation), dtype=torch.float32, device=self.device)

    def _build(self) -> None:
        tree = ET.parse(str(self.xml_path))
        root = tree.getroot()
        worldbody = root.find("worldbody")
        if worldbody is None:
            raise ValueError(f"worldbody not found in {self.xml_path}")
        body_root = worldbody.find("body")
        if body_root is None:
            raise ValueError(f"root <body> not found in {self.xml_path}")

        def add_body(node: ET.Element, parent_idx: int, body_index: int) -> int:
            name = node.attrib.get("name", f"body_{body_index}")
            pos = _parse_floats(node.attrib.get("pos"), n=3, default=(0.0, 0.0, 0.0))
            quat_wxyz = _parse_floats(node.attrib.get("quat"), n=4, default=(1.0, 0.0, 0.0, 0.0))
            quat_xyzw = _quat_wxyz_to_xyzw(quat_wxyz)

            if body_index == 0:
                joint = _JointLite(name=name, dof_dim=0, axis=None)
            else:
                joints = node.findall("joint")
                if len(joints) == 0:
                    joint = _JointLite(name=name, dof_dim=0, axis=None)
                elif len(joints) == 1:
                    axis_np = _parse_floats(joints[0].attrib.get("axis"), n=3, default=(0.0, 0.0, 1.0))
                    import torch

                    axis = torch.tensor(axis_np, dtype=torch.float32, device=self.device)
                    joint = _JointLite(name=name, dof_dim=1, axis=axis)
                elif len(joints) == 3:
                    joint = _JointLite(name=name, dof_dim=3, axis=None)
                else:
                    raise ValueError(f"Invalid number of joints ({len(joints)}) for body: {name}")

            self.body_names.append(name)
            self.parent_indices.append(int(parent_idx))
            self.local_translation.append(pos.astype(np.float32))
            self.local_rotation.append(quat_xyzw.astype(np.float32))
            self.joints.append(joint)
            self._dof_size.append(joint.dof_dim)

            curr_idx = body_index
            body_index += 1
            for child in node.findall("body"):
                body_index = add_body(child, curr_idx, body_index)
            return body_index

        add_body(body_root, -1, 0)

    def _set_dof_indices(self) -> None:
        idx = 0
        for j in self.joints:
            if j.dof_dim > 0:
                j.set_dof_idx(idx)
                idx += j.dof_dim
        self.num_dof = int(idx)
        self.num_joint = int(len(self.body_names))

    def forward_kinematics(self, root_pos, root_rot_xyzw, dof_pos):
        """Compute (body_pos, body_rot) in world frame.

        Args:
            root_pos: (N,3) torch
            root_rot_xyzw: (N,4) torch
            dof_pos: (N,num_dof) torch
        Returns:
            body_pos: (N,B,3) torch
            body_rot: (N,B,4) torch (xyzw)
        """
        import torch

        if dof_pos.shape[-1] != self.num_dof:
            raise ValueError(f"dof_pos dim mismatch: expected {self.num_dof}, got {int(dof_pos.shape[-1])}")

        N = int(root_pos.shape[0])
        body_pos = [None] * self.num_joint
        body_rot = [None] * self.num_joint
        body_pos[0] = root_pos
        body_rot[0] = root_rot_xyzw

        # Joint rotations (per-body, in parent frame)
        joint_rot: list[torch.Tensor] = [None] * self.num_joint
        joint_rot[0] = torch.zeros((N, 4), dtype=root_pos.dtype, device=root_pos.device)
        joint_rot[0][:, 3] = 1.0
        for j in range(1, self.num_joint):
            joint = self.joints[j]
            if joint.dof_dim == 0:
                q = torch.zeros((N, 4), dtype=root_pos.dtype, device=root_pos.device)
                q[:, 3] = 1.0
                joint_rot[j] = q
            else:
                dof = dof_pos[:, joint.dof_idx : joint.dof_idx + joint.dof_dim]
                joint_rot[j] = joint.dof_to_quat(dof)

        for j in range(1, self.num_joint):
            parent = self.parent_indices[j]
            parent_pos = body_pos[parent]
            parent_rot = body_rot[parent]

            local_t = self.local_translation_t[j].expand_as(parent_pos)
            local_r = self.local_rotation_t[j].expand_as(parent_rot)
            jr = joint_rot[j]

            world_t = _torch_quat_rotate(parent_rot, local_t)
            curr_pos = parent_pos + world_t
            curr_rot = _torch_quat_mul(parent_rot, _torch_quat_mul(local_r, jr))

            body_pos[j] = curr_pos
            body_rot[j] = curr_rot

        return torch.stack(body_pos, dim=-2), torch.stack(body_rot, dim=-2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize robot motion in PromptHMR viser scene")
    parser.add_argument("--project", "-p", required=True, help="Project folder (contains results.pkl, original.mp4)")
    parser.add_argument("--twist", action="store_true", help="Use robot_motion*_twist.pkl files if available")
    parser.add_argument("--total", type=int, default=1500, help="Max video frames to load")
    parser.add_argument("--subsample", type=int, default=1, help="Subsample video frames")
    parser.add_argument("--track-index", type=int, help="Legacy single track index (1-based)")
    parser.add_argument("--tracks", type=int, nargs="+", help="Specific track indices to visualize together")
    parser.add_argument("--all-tracks", action="store_true", help="Visualize every available track simultaneously")
    parser.add_argument("--img-maxsize", type=int, default=0, help="Max image size for viser frustum textures (0 = no resize)")

    parser.add_argument("--robot-type", default=None, help="Override robot type (default: from motion file)")
    parser.add_argument("--robot-xml", default=None, help="Override MJCF xml path")
    parser.add_argument("--proxy", action="store_true", help="Render as proxy cubes instead of real robot meshes")
    parser.add_argument("--cube-size", type=float, default=0.03, help="Cube size (meters) when using --proxy")
    parser.add_argument(
        "--material-mode",
        choices=["color", "metal"],
        default="color",
        help="Robot appearance: color=track colors, metal=original mesh color",
    )

    parser.add_argument("--no-floor", action="store_true", help="Disable floor rendering")
    parser.add_argument("--floor-margin", type=float, default=1.5, help="Floor extent margin around trajectories (meters)")
    parser.add_argument("--frustum-scale", type=float, default=0.4, help="Video camera frustum scale")
    parser.add_argument("--frustum-fov", type=float, default=0.96, help="Video camera frustum FOV (radians)")
    parser.add_argument("--frustum-image-stride", type=int, default=2, help="Update frustum image every N frames to reduce blur from bandwidth pressure")

    parser.add_argument("--host", default="0.0.0.0", help="Viser server host (default: 0.0.0.0 for external access)")
    parser.add_argument("--port", type=int, default=8789, help="Viser server port (default: 8789)")

    args = parser.parse_args()

    if args.track_index is not None and args.track_index < 1:
        raise SystemExit("--track-index must be >= 1")
    if args.tracks and any(idx < 1 for idx in args.tracks):
        raise SystemExit("--tracks entries must be >= 1")

    project_dir = Path(args.project)
    if not project_dir.exists():
        raise SystemExit(f"Project not found: {project_dir}")

    results_pkl = project_dir / "results.pkl"
    video_path = project_dir / "original.mp4"
    if not results_pkl.exists():
        raise SystemExit(f"results.pkl not found: {results_pkl}")
    if not video_path.exists():
        raise SystemExit(f"original.mp4 not found: {video_path}")

    print(f"[RobotViser] Project: {project_dir}")
    print(f"[RobotViser] results: {results_pkl}")
    print(f"[RobotViser] video: {video_path}")

    results = joblib.load(results_pkl)
    people = results.get("people", {})
    if not people:
        raise SystemExit("No people found in results.pkl")

    print("[RobotViser] Loading video frames...")
    frames, video_fps = _load_video_frames(video_path, max_frames=args.total)
    if args.subsample > 1:
        frames = frames[:: args.subsample]
    frames = [_maybe_resize_rgb(f, img_maxsize=int(args.img_maxsize)) for f in frames]
    num_vis_frames = len(frames)
    if num_vis_frames == 0:
        raise SystemExit("No frames to visualize")

    print(f"[RobotViser] Video FPS: {video_fps:.3f} (subsample={args.subsample})")
    print(f"[RobotViser] Visualized frames: {num_vis_frames}")

    explicit_tracks = args.tracks or ([args.track_index] if args.track_index else None)
    selected_indices, index_to_key = _resolve_track_selection(
        project_dir,
        people,
        all_tracks=args.all_tracks,
        explicit_tracks=explicit_tracks,
        default_track=(args.track_index or 1),
    )

    entries: list[RobotEntry] = []
    for idx in selected_indices:
        track_key = index_to_key[idx]
        motion_path = _motion_path_for_track(project_dir, idx, twist=args.twist)
        if motion_path is None or not motion_path.exists():
            print(f"[RobotViser] Warning: robot motion for track #{idx} not found, skipping")
            continue
        entry = _prepare_robot_entry(
            track_index=idx,
            track_key=track_key,
            motion_path=motion_path,
            video_fps=video_fps,
            num_vis_frames=num_vis_frames,
            subsample=max(1, args.subsample),
        )
        entries.append(entry)

    if not entries:
        raise SystemExit("No robot motions available for the selected tracks.")

    print(f"[RobotViser] Selected tracks: {', '.join(str(e.track_index) for e in entries)}")
    for entry in entries:
        print(f"  - Track #{entry.track_index} (track_id={entry.track_key}) from {entry.motion_path.name}")

    robot_types = {entry.robot_type for entry in entries}
    if args.robot_type:
        robot_type = str(args.robot_type)
    elif len(robot_types) == 1:
        robot_type = robot_types.pop()
    else:
        robot_type = sorted(robot_types)[0]
        print(f"[RobotViser] Warning: multiple robot types found {robot_types}; using {robot_type}")

    if args.robot_xml:
        xml_path = Path(args.robot_xml).expanduser().resolve()
    else:
        if robot_type not in ROBOT_XML_DICT:
            raise SystemExit(f"Unknown robot type: {robot_type} (available: {sorted(ROBOT_XML_DICT.keys())})")
        xml_path = Path(ROBOT_XML_DICT[robot_type]).resolve()
    if not xml_path.exists():
        raise SystemExit(f"Robot xml not found: {xml_path}")

    use_proxy = bool(args.proxy)
    body_geoms: dict[str, list[dict]] = {}
    if not use_proxy:
        print(f"[RobotViser] Loading robot visual meshes from: {xml_path}")
        try:
            body_geoms = _load_robot_visual_geoms(xml_path)
        except Exception as exc:
            print(f"[RobotViser] Warning: failed to load robot meshes ({exc}); falling back to --proxy")
            use_proxy = True

    import torch

    device = torch.device("cpu")
    kin = KinematicsModelLite(xml_path, device=device)
    body_names = list(kin.body_names)
    body_name_to_idx = {n: i for i, n in enumerate(body_names)}
    T = _PROMPTHMR_TO_GMR_COORD_TRANSFORM.astype(np.float32)

    for entry in entries:
        _compute_body_poses(entry, kin, device=device, T=T)

    all_root_pos_yup = np.concatenate([entry.root_pos_yup for entry in entries], axis=0)
    primary_entry = entries[0]

    camera = results.get("camera_world", results.get("camera", {}))
    Rwc_all = camera.get("Rwc", None)
    Twc_all = camera.get("Twc", None)

    # --- Viser scene ---
    server = viser.ViserServer(host=args.host, port=args.port)
    server.scene.world_axes.visible = True
    server.scene.set_up_direction("+y")

    # Lighting: Viser's defaults can look harsh / "broken" on STL meshes (especially with culling).
    # Add a soft environment + a directional light to get closer to MuJoCo-style readability.
    server.scene.add_light_ambient("/lights/ambient", intensity=0.35, color=(255, 255, 255))
    server.scene.add_light_hemisphere(
        "/lights/hemi",
        intensity=0.65,
        sky_color=(255, 255, 255),
        ground_color=(110, 110, 110),
    )
    # A gentle key light from above-front.
    server.scene.add_light_directional("/lights/key", intensity=0.6, color=(255, 255, 255))

    # GUI (similar to PromptHMR, but we update objects dynamically)
    gui_timestep = server.gui.add_slider(
        "Timestep",
        min=0,
        max=num_vis_frames - 1,
        step=1,
        initial_value=0,
        disabled=True,
    )
    gui_next_frame = server.gui.add_button("Next Frame", disabled=True)
    gui_prev_frame = server.gui.add_button("Prev Frame", disabled=True)
    gui_playing = server.gui.add_checkbox("Playing", True)
    gui_framerate = server.gui.add_slider(
        "FPS",
        min=1,
        max=60,
        step=0.1,
        initial_value=min(float(video_fps) / float(args.subsample), 12.0),
    )
    last_frustum_image_idx = {"value": -1}

    @gui_next_frame.on_click
    def _(_) -> None:
        gui_timestep.value = (gui_timestep.value + 1) % num_vis_frames

    @gui_prev_frame.on_click
    def _(_) -> None:
        gui_timestep.value = (gui_timestep.value - 1) % num_vis_frames

    @gui_playing.on_update
    def _(_) -> None:
        gui_timestep.disabled = gui_playing.value
        gui_next_frame.disabled = gui_playing.value
        gui_prev_frame.disabled = gui_playing.value

    # Floor
    if not args.no_floor:
        fv, ff = _make_floor_mesh_from_root_traj(all_root_pos_yup, margin=float(args.floor_margin), y=-0.002)
        server.scene.add_mesh_simple(
            "/floor",
            vertices=fv,
            faces=ff,
            material="toon5",
            flat_shading=True,
            wireframe=False,
            color=(140, 140, 140),
            side="double",
        )

    # Camera frustum (we update pose+image each timestep).
    # We update BOTH a camera-axes frame and the frustum handle directly.
    # (Don't rely on path parenting semantics.)
    cam_axes = server.scene.add_frame("/video_cam_axes", show_axes=True, axes_length=0.3, axes_radius=0.02)
    img0 = frames[0]
    aspect0 = float(img0.shape[1]) / float(img0.shape[0]) if img0 is not None else 1.7
    frustum = server.scene.add_camera_frustum(
        "/video_cam_frustum",
        fov=float(args.frustum_fov),
        aspect=aspect0,
        scale=float(args.frustum_scale),
        line_width=1.5,
        color=(255, 127, 14),
        wxyz=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        position=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        image=img0,
    )

    # Helpful initial view:
    # PromptHMR's `viz_scale/viz_center` includes camera trajectory → often huge.
    # For interactive viewing, use the robot root trajectory instead (better orbit center & zoom).
    xs = all_root_pos_yup[:, 0]
    ys = all_root_pos_yup[:, 1]
    zs = all_root_pos_yup[:, 2]
    cx = float(0.5 * (np.nanmin(xs) + np.nanmax(xs)))
    cz = float(0.5 * (np.nanmin(zs) + np.nanmax(zs)))
    cy = float(np.nanmedian(ys))
    scale_x = float(np.nanmax(xs) - np.nanmin(xs))
    scale_z = float(np.nanmax(zs) - np.nanmin(zs))
    scene_scale = max(scale_x, scale_z, 1.0)
    scene_center = np.array([cx, cy, cz], dtype=np.float32)
    init_dist = max(scene_scale * 2.5, 3.0)
    init_height = max(scene_scale * 1.0, 1.5)
    init_pos = scene_center + np.array([0.0, init_height, init_dist], dtype=np.float32)

    def _apply_default_view(client) -> None:
        try:
            client.camera.position = init_pos
            client.camera.look_at = scene_center
            client.camera.up_direction = np.array([0.0, 1.0, 0.0], dtype=np.float32)
            # Slightly wider FOV feels better for large scenes.
            client.camera.fov = 0.9
            client.camera.near = 0.01
            client.camera.far = 5000.0
        except Exception:
            # If the camera isn't initialized yet, we'll try again on the next update.
            pass

    @server.on_client_connect
    def _(client) -> None:
        did_init = {"ok": False}

        @client.camera.on_update
        def _(_cam) -> None:
            if did_init["ok"]:
                return
            did_init["ok"] = True
            _apply_default_view(client)

    # Optional: view from the video camera (helps debug overlay alignment).
    gui_view_from_video = server.gui.add_checkbox("View from video camera", False)
    gui_reset_view = server.gui.add_button("Reset view")

    @gui_reset_view.on_click
    def _(_) -> None:
        for client in server.get_clients().values():
            _apply_default_view(client)

    for entry in entries:
        if len(entries) > 1:
            color_name = _color_name_for_track(entry.track_index)
            label = f"Track {entry.track_index} ({color_name})"
        else:
            label = f"Track {entry.track_index}"
        entry.visible_toggle = server.gui.add_checkbox(label, True)

    num_links = len(body_names)
    if use_proxy:
        s = float(args.cube_size) * 0.5
        cube_v = np.array(
            [
                [-s, -s, -s],
                [-s, -s, +s],
                [-s, +s, -s],
                [-s, +s, +s],
                [+s, -s, -s],
                [+s, -s, +s],
                [+s, +s, -s],
                [+s, +s, +s],
            ],
            dtype=np.float32,
        )
        cube_f = np.array(
            [
                [0, 2, 3],
                [0, 3, 1],
                [4, 5, 7],
                [4, 7, 6],
                [0, 1, 5],
                [0, 5, 4],
                [2, 6, 7],
                [2, 7, 3],
                [0, 4, 6],
                [0, 6, 2],
                [1, 3, 7],
                [1, 7, 5],
            ],
            dtype=np.int32,
        )
        for entry in entries:
            entry.proxy_frames = []
            base_path = f"/robots/track_{entry.track_index}"
            for k in range(num_links):
                lf = server.scene.add_frame(f"{base_path}/link_{k}", show_axes=False)
                cube_color = entry.color if args.material_mode == "color" else (170, 170, 170)
                server.scene.add_mesh_simple(
                    f"{base_path}/link_{k}/cube",
                    vertices=cube_v,
                    faces=cube_f,
                    flat_shading=False,
                    wireframe=False,
                    color=cube_color,
                )
                entry.proxy_frames.append(lf)
    else:
        missing = []
        for entry in entries:
            entry.body_frames = {}
            base_path = f"/robots/track_{entry.track_index}"
            for body_name, geoms in body_geoms.items():
                if body_name not in body_name_to_idx:
                    if body_name not in missing:
                        missing.append(body_name)
                    continue
                frame_path = f"{base_path}/{body_name}"
                entry.body_frames[body_name] = server.scene.add_frame(frame_path, show_axes=False)
                for gi, geom in enumerate(geoms):
                    mesh_copy = geom["trimesh"].copy()
                    color = entry.color if args.material_mode == "color" else geom["color"]
                    mesh_copy.visual = trimesh.visual.ColorVisuals(
                        mesh=mesh_copy,
                        face_colors=[*color, 255],
                    )
                    server.scene.add_mesh_trimesh(f"{frame_path}/geom_{gi}", mesh_copy)
        if missing:
            print(f"[RobotViser] Warning: {len(missing)} bodies in xml but not in kinematics list (skipped).")

    def _update_scene(vis_idx: int) -> None:
        vis_idx = int(vis_idx)
        vis_idx = max(0, min(num_vis_frames - 1, vis_idx))
        orig_idx = vis_idx * max(1, int(args.subsample))

        if Rwc_all is not None and Twc_all is not None and orig_idx < len(Rwc_all) and orig_idx < len(Twc_all):
            cam_R = np.asarray(Rwc_all[orig_idx], dtype=np.float32)
            cam_T = np.asarray(Twc_all[orig_idx], dtype=np.float32)
        else:
            cam_R = np.eye(3, dtype=np.float32)
            cam_T = np.zeros(3, dtype=np.float32)
        cam_q_xyzw = R.from_matrix(cam_R).as_quat().astype(np.float32)
        cam_q_wxyz = np.concatenate([cam_q_xyzw[3:], cam_q_xyzw[:3]]).astype(np.float32)

        with server.atomic():
            cam_axes.position = cam_T
            cam_axes.wxyz = cam_q_wxyz
            frustum.position = cam_T
            frustum.wxyz = cam_q_wxyz

            # Hide frustum and camera axes when viewing from video camera
            frustum.visible = not gui_view_from_video.value
            cam_axes.visible = not gui_view_from_video.value

            if frustum.visible:
                try:
                    stride = max(1, int(args.frustum_image_stride))
                    should_update = (
                        vis_idx == 0
                        or vis_idx == (num_vis_frames - 1)
                        or (vis_idx % stride == 0)
                        or (not gui_playing.value)
                    )
                    if should_update and last_frustum_image_idx["value"] != vis_idx:
                        frustum.image = frames[vis_idx]
                        last_frustum_image_idx["value"] = vis_idx
                except Exception:
                    pass

            for entry in entries:
                is_visible = not entry.visible_toggle or entry.visible_toggle.value
                r_idx = entry.vis_to_robot[vis_idx]
                if use_proxy:
                    pos = entry.body_pos_yup[r_idx]
                    for k, lf in enumerate(entry.proxy_frames):
                        lf.visible = is_visible
                        if is_visible:
                            lf.position = pos[k]
                else:
                    for body_name, bf in entry.body_frames.items():
                        bf.visible = is_visible
                        if is_visible:
                            j = body_name_to_idx[body_name]
                            bf.position = entry.body_pos_yup[r_idx, j]
                            bf.wxyz = entry.body_rot_wxyz_yup[r_idx, j]

        server.flush()

        if gui_view_from_video.value:
            look_dir = cam_R[:, 2].astype(np.float32)
            primary_idx = primary_entry.vis_to_robot[vis_idx]
            v_to_robot = (primary_entry.root_pos_yup[primary_idx] - cam_T).astype(np.float32)
            if float(np.dot(v_to_robot, look_dir)) < 0.0:
                look_dir = -look_dir
            up_dir = (-cam_R[:, 1]).astype(np.float32)
            look_dist = 2.0
            look_at = cam_T + look_dir * float(look_dist)
            for client in server.get_clients().values():
                try:
                    client.camera.position = cam_T
                    client.camera.look_at = look_at
                    client.camera.up_direction = up_dir
                    client.camera.fov = float(args.frustum_fov)
                except Exception:
                    pass

    @gui_timestep.on_update
    def _(_) -> None:
        _update_scene(gui_timestep.value)

    # Initialize
    _update_scene(0)

    url = f"https://localhost:{server.get_port()}"
    print(f"\n[RobotViser] Open in browser: {url}")
    print("[RobotViser] Press Ctrl+C to stop")

    try:
        last_time = time.perf_counter()
        while True:
            if gui_playing.value:
                gui_timestep.value = (gui_timestep.value + 1) % num_vis_frames

            # Maintain consistent framerate by accounting for processing time
            target_dt = 1.0 / gui_framerate.value
            elapsed = time.perf_counter() - last_time
            sleep_time = max(0.0, target_dt - elapsed)
            time.sleep(sleep_time)
            last_time = time.perf_counter()
    except KeyboardInterrupt:
        print("\n[RobotViser] Interrupted.")


if __name__ == "__main__":
    main()
