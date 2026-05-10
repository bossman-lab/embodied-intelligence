import os
import sys

import mujoco
import numpy as np
import open3d as o3d
import spatialmath as sm
import torch
from PIL import Image
from functools import lru_cache

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_PATH = os.path.join(ROOT_DIR, "temp", "logs", "log_rs", "checkpoint-rs.tar")
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "models"))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "dataset"))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "utils"))
sys.path.append(os.path.join(ROOT_DIR, "manipulator_grasp"))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "graspnetAPI"))

from manipulator_grasp.arm.motion_planning import (
    JointParameter,
    QuinticVelocityParameter,
    TrajectoryParameter,
    TrajectoryPlanner,
)
from manipulator_grasp.utils import mj as mj_utils

from graspnet import GraspNet, pred_decode
from graspnetAPI import GraspGroup
from collision_detector import ModelFreeCollisionDetector
from data_utils import CameraInfo, create_point_cloud_from_depth_image


SCENE_BODY_NAMES = {
    "apple": "apple_6",
    "apple_rack": "TieredBasket008",
    "banana": "Banana",
    # The visible SNICKERS-style chocolate bar the user points at is bar_2_1.
    "chocolate": "bar_2_1",
    "chocolate_bar": "bar_2_1",
    "snickers": "bar_2_1",
    "sponge": "sponge_7_1",
    "sponge_rack": "TieredBasket008",
    "hammer": "Hammer",
    "knife": "Knife",
    "duck": "Duck",
    "plate": "Plate",
    "shelf": "Shelf",
}

SCENE_OBJECT_RADII = {
    "apple": 0.035,
    "apple_rack": 0.18,
    "banana": 0.055,
    "hammer": 0.07,
    "knife": 0.07,
    "duck": 0.04,
    "plate": 0.10,
    "sponge": 0.04,
    "shelf": 0.18,
    "sponge_rack": 0.18,
}

TABLE_SURFACE_Z = float(os.getenv("OPENCLAW_TABLE_SURFACE_Z", "0.92"))
OPENCLAW_MAX_GRASP_DEPTH = float(os.getenv("OPENCLAW_MAX_GRASP_DEPTH", "6.0"))
OPENCLAW_MAX_MASK_DEPTH = float(os.getenv("OPENCLAW_MAX_MASK_DEPTH", "6.0"))
OPENCLAW_TRAVEL_Z = float(os.getenv("OPENCLAW_TRAVEL_Z", "1.26"))
OPENCLAW_PREGRASP_CLEARANCE = float(
    os.getenv("OPENCLAW_PREGRASP_CLEARANCE", "0.12")
)
OPENCLAW_PLACE_CLEARANCE = float(os.getenv("OPENCLAW_PLACE_CLEARANCE", "0.10"))
OPENCLAW_CONTACT_TOL = float(os.getenv("OPENCLAW_CONTACT_TOL", "0.003"))
OPENCLAW_TABLE_MARGIN = float(os.getenv("OPENCLAW_TABLE_MARGIN", "0.07"))
OPENCLAW_ENABLE_SCENE_COLLISION = os.getenv(
    "OPENCLAW_ENABLE_SCENE_COLLISION", "0"
).strip().lower() in {"1", "true", "yes"}

ROBOT_ROOT_BODIES = ("ur5e_base", "2f85_base")
ISLAND_BODY_NAME = "island_island_group_1_main"
STATIC_TABLETOP_OBSTACLES = {
    "Shelf",
    "MugTree",
    "KnifeBlock",
    "FlowerVase",
    "DigitalScale",
    "FlourBag",
    "FruitBowl",
    "GlassCup",
    "Plate",
}

TABLE_SPONGE_BODIES = ("sponge_7", "sponge_7_1")
RACK_SPONGE_BODIES = ("sponge_7_2", "sponge_7_3")
RACK_APPLE_BODIES = ("apple_6_1", "apple_6_2")


@lru_cache(maxsize=1)
def get_net():
    net = GraspNet(
        input_feature_dim=0,
        num_view=300,
        num_angle=12,
        num_depth=4,
        cylinder_radius=0.05,
        hmin=-0.02,
        hmax_list=[0.01, 0.02, 0.03, 0.04],
        is_training=False,
    )
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    net.to(device)
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"GraspNet checkpoint not found: {CHECKPOINT_PATH}")
    checkpoint = torch.load(CHECKPOINT_PATH)
    net.load_state_dict(checkpoint["model_state_dict"])
    net.eval()
    return net


def get_and_process_data(color_path, depth_path, mask_path, camera_fovy_deg: float = 45.0):
    if isinstance(color_path, str):
        color = np.array(Image.open(color_path), dtype=np.float32) / 255.0
    elif isinstance(color_path, np.ndarray):
        color = color_path.astype(np.float32) / 255.0
    else:
        raise TypeError("color_path must be a path or numpy array")

    if isinstance(depth_path, str):
        depth = np.array(Image.open(depth_path))
    elif isinstance(depth_path, np.ndarray):
        depth = depth_path
    else:
        raise TypeError("depth_path must be a path or numpy array")

    if isinstance(mask_path, str):
        workspace_mask = np.array(Image.open(mask_path))
    elif isinstance(mask_path, np.ndarray):
        workspace_mask = mask_path
    else:
        raise TypeError("mask_path must be a path or numpy array")

    height, width = color.shape[:2]
    fovy = np.deg2rad(float(camera_fovy_deg))
    focal = height / (2.0 * np.tan(fovy / 2.0))
    c_x = width / 2.0
    c_y = height / 2.0
    factor_depth = 1.0

    camera = CameraInfo(width, height, focal, focal, c_x, c_y, factor_depth)
    cloud = create_point_cloud_from_depth_image(depth, camera, organized=True)

    mask = (workspace_mask > 0) & np.isfinite(depth) & (depth > 0.0) & (
        depth < OPENCLAW_MAX_GRASP_DEPTH
    )
    cloud_masked = cloud[mask]
    color_masked = color[mask]

    if len(cloud_masked) == 0:
        valid_depth = depth[np.isfinite(depth) & (depth > 0.0)]
        depth_summary = "no valid depth values"
        if valid_depth.size > 0:
            depth_summary = (
                f"depth range=[{valid_depth.min():.3f}, {valid_depth.max():.3f}], "
                f"median={np.median(valid_depth):.3f}, "
                f"threshold={OPENCLAW_MAX_GRASP_DEPTH:.3f}"
            )
        raise RuntimeError(
            "No valid masked point cloud points after depth filtering; "
            + depth_summary
        )

    num_point = 5000
    if len(cloud_masked) >= num_point:
        idxs = np.random.choice(len(cloud_masked), num_point, replace=False)
    else:
        idxs1 = np.arange(len(cloud_masked))
        idxs2 = np.random.choice(
            len(cloud_masked), num_point - len(cloud_masked), replace=True
        )
        idxs = np.concatenate([idxs1, idxs2], axis=0)

    cloud_sampled = cloud_masked[idxs]
    color_sampled = color_masked[idxs]

    cloud_o3d = o3d.geometry.PointCloud()
    cloud_o3d.points = o3d.utility.Vector3dVector(cloud_masked.astype(np.float32))
    cloud_o3d.colors = o3d.utility.Vector3dVector(color_masked.astype(np.float32))

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    cloud_sampled = torch.from_numpy(
        cloud_sampled[np.newaxis].astype(np.float32)
    ).to(device)

    end_points = {
        "point_clouds": cloud_sampled,
        "cloud_colors": color_sampled,
    }
    return end_points, cloud_o3d


def run_grasp_inference(color_path, depth_path, sam_mask_path=None, camera_fovy_deg: float = 45.0):
    net = get_net()
    end_points, cloud_o3d = get_and_process_data(
        color_path,
        depth_path,
        sam_mask_path,
        camera_fovy_deg=camera_fovy_deg,
    )

    with torch.no_grad():
        end_points = net(end_points)
        grasp_preds = pred_decode(end_points)

    gg = GraspGroup(grasp_preds[0].detach().cpu().numpy())
    gg = gg.nms().sort_by_score()

    max_candidates = int(os.getenv("OPENCLAW_GRASP_MAX_CANDIDATES", "256"))
    if len(gg) > max_candidates:
        gg = gg[:max_candidates]
        print(f"[grasp] capped candidates to top {max_candidates} before collision check.")

    collision_thresh = 0.01
    if collision_thresh > 0:
        try:
            mfcdetector = ModelFreeCollisionDetector(
                np.asarray(cloud_o3d.points, dtype=np.float32), voxel_size=0.01
            )
            collision_mask = mfcdetector.detect(
                gg, approach_dist=0.05, collision_thresh=collision_thresh
            )
            gg = gg[~collision_mask]
        except Exception as exc:
            print(f"[grasp] collision check skipped: {exc}")

    gg = gg.sort_by_score()

    all_grasps = list(gg)
    vertical = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    angle_threshold = np.deg2rad(30)
    filtered = []
    for grasp in all_grasps:
        approach_dir = grasp.rotation_matrix[:, 0]
        cos_angle = np.clip(np.dot(approach_dir, vertical), -1.0, 1.0)
        angle = np.arccos(cos_angle)
        if angle < angle_threshold:
            filtered.append(grasp)

    if len(filtered) == 0:
        print("\n[warning] No vertical grasps found. Using all predictions.")
        filtered = all_grasps
    else:
        print(
            f"\n[DEBUG] Filtered {len(filtered)} grasps within 卤30掳 of vertical out of "
            f"{len(all_grasps)} total predictions."
        )

    points = np.asarray(cloud_o3d.points)
    object_center = np.mean(points, axis=0) if len(points) > 0 else np.zeros(3)
    distances = [np.linalg.norm(grasp.translation - object_center) for grasp in filtered]
    grasp_with_distances = list(zip(filtered, distances))
    max_distance = max(distances) if distances else 1.0

    scored_grasps = []
    for grasp, distance in grasp_with_distances:
        distance_score = 1 - (distance / max_distance)
        composite_score = grasp.score * 0.1 + distance_score * 0.9
        scored_grasps.append((grasp, composite_score))

    scored_grasps.sort(key=lambda item: item[1], reverse=True)
    best_grasp = scored_grasps[0][0]

    new_gg = GraspGroup()
    new_gg.add(best_grasp)

    visual = os.getenv("OPENCLAW_SHOW_GRASP", "0").lower() in {"1", "true", "yes"}
    if visual:
        grippers = new_gg.to_open3d_geometry_list()
        o3d.visualization.draw_geometries([cloud_o3d, *grippers])

    return new_gg


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm < 1e-8:
        return vec
    return vec / norm


def _camera_info_from_depth(env, depth: np.ndarray) -> CameraInfo:
    height, width = depth.shape[:2]
    fovy = np.deg2rad(float(getattr(env, "camera_fovy_deg", 45.0)))
    focal = height / (2.0 * np.tan(fovy / 2.0))
    c_x = width / 2.0
    c_y = height / 2.0
    return CameraInfo(width, height, focal, focal, c_x, c_y, 1.0)


def _camera_pose(env) -> sm.SE3:
    cam_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_CAMERA, "cam")
    if cam_id < 0:
        raise RuntimeError("Camera 'cam' not found in MuJoCo scene.")
    cam_pos = np.array(env.mj_data.cam_xpos[cam_id], dtype=np.float64)
    cam_rot = np.array(env.mj_data.cam_xmat[cam_id], dtype=np.float64).reshape(3, 3)
    return sm.SE3.Rt(sm.SO3(cam_rot), cam_pos)


def _camera_intrinsics(env, height: int, width: int) -> CameraInfo:
    fovy = np.deg2rad(float(getattr(env, "camera_fovy_deg", 45.0)))
    focal = height / (2.0 * np.tan(fovy / 2.0))
    c_x = width / 2.0
    c_y = height / 2.0
    return CameraInfo(width, height, focal, focal, c_x, c_y, 1.0)


def mask_to_world_points(env, depth_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if mask is None:
        return np.zeros((0, 3), dtype=np.float64)

    camera = _camera_intrinsics(env, depth_img.shape[0], depth_img.shape[1])
    cloud = create_point_cloud_from_depth_image(depth_img, camera, organized=True)
    valid_mask = (
        (mask > 0)
        & np.isfinite(depth_img)
        & (depth_img > 0.0)
        & (depth_img < OPENCLAW_MAX_MASK_DEPTH)
    )
    if not np.any(valid_mask):
        return np.zeros((0, 3), dtype=np.float64)

    camera_points = cloud[valid_mask].astype(np.float64)
    camera_to_mujoco = np.diag([1.0, -1.0, -1.0])
    camera_points = (camera_to_mujoco @ camera_points.T).T

    T_wc = _camera_pose(env)
    world_points = (T_wc.R @ camera_points.T).T + T_wc.t
    return world_points


def estimate_mask_world_geometry(env, depth_img: np.ndarray, mask: np.ndarray) -> dict:
    world_points = mask_to_world_points(env, depth_img, mask)
    if len(world_points) == 0:
        raise RuntimeError("Failed to estimate world geometry from mask.")

    centroid = np.mean(world_points, axis=0)
    planar_offsets = world_points[:, :2] - centroid[:2]
    planar_radii = np.linalg.norm(planar_offsets, axis=1)
    planar_radius = float(np.percentile(planar_radii, 90)) if len(planar_radii) else 0.04
    z_top = float(np.percentile(world_points[:, 2], 90))
    z_bottom = float(np.percentile(world_points[:, 2], 10))
    return {
        "centroid": centroid,
        "planar_radius": max(planar_radius, 0.02),
        "z_top": z_top,
        "z_bottom": z_bottom,
        "height": max(z_top - z_bottom, 0.02),
        "points": world_points,
    }


def estimate_body_image_bbox(
    env,
    name: str,
    image_shape: tuple[int, int],
    padding_px: int = 8,
) -> list[int] | None:
    body_name = _resolve_scene_body_name(env, name)
    if body_name is None:
        return None
    body_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        return None

    height, width = image_shape[:2]
    camera = _camera_intrinsics(env, height, width)
    T_wc = _camera_pose(env)
    camera_to_mujoco = np.diag([1.0, -1.0, -1.0])
    mujoco_to_camera = camera_to_mujoco

    geom_adr = int(env.mj_model.body_geomadr[body_id])
    geom_num = int(env.mj_model.body_geomnum[body_id])
    if geom_num <= 0:
        return None

    x_mins, y_mins, x_maxs, y_maxs = [], [], [], []
    for geom_id in range(geom_adr, geom_adr + geom_num):
        center_world = np.array(env.mj_data.geom_xpos[geom_id], dtype=np.float64)
        radius = float(env.mj_model.geom_rbound[geom_id])
        if radius <= 1e-6:
            size = np.array(env.mj_model.geom_size[geom_id], dtype=np.float64)
            radius = float(np.linalg.norm(size))
        if radius <= 1e-6:
            radius = 0.01

        point_mujoco = T_wc.R.T @ (center_world - T_wc.t)
        point_camera = mujoco_to_camera @ point_mujoco
        if point_camera[2] <= 0.03:
            continue

        u = camera.fx * (point_camera[0] / point_camera[2]) + camera.cx
        v = camera.fy * (point_camera[1] / point_camera[2]) + camera.cy
        pixel_radius = max(camera.fx * radius / point_camera[2], 2.0)

        x_mins.append(u - pixel_radius)
        y_mins.append(v - pixel_radius)
        x_maxs.append(u + pixel_radius)
        y_maxs.append(v + pixel_radius)

    if not x_mins:
        return None

    x1 = max(0, int(np.floor(min(x_mins) - padding_px)))
    y1 = max(0, int(np.floor(min(y_mins) - padding_px)))
    x2 = min(width - 1, int(np.ceil(max(x_maxs) + padding_px)))
    y2 = min(height - 1, int(np.ceil(max(y_maxs) + padding_px)))
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def _resolve_scene_body_name(env, name: str) -> str | None:
    hint = SCENE_BODY_NAMES.get(name, name)
    if not hint:
        return None

    body_names = [
        mujoco.mj_id2name(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        for body_id in range(env.mj_model.nbody)
    ]
    body_names = [body_name for body_name in body_names if body_name]

    for candidate in (hint, name):
        if candidate and candidate in body_names:
            return candidate

    hint_lower = hint.lower()
    exact_ci = [body_name for body_name in body_names if body_name.lower() == hint_lower]
    if exact_ci:
        return exact_ci[0]

    prefix_matches = [
        body_name
        for body_name in body_names
        if body_name.lower().startswith(hint_lower + "_")
        or body_name.lower().startswith(hint_lower)
    ]
    if prefix_matches:
        return sorted(prefix_matches, key=len)[0]

    substring_matches = [
        body_name for body_name in body_names if hint_lower in body_name.lower()
    ]
    if substring_matches:
        return sorted(substring_matches, key=len)[0]

    return None


def get_named_scene_geometry(env, name: str) -> dict | None:
    body_name = _resolve_scene_body_name(env, name)
    if body_name is None:
        return None
    geometry = _estimate_body_geometry(env, body_name)
    if geometry is None:
        return None
    radius = SCENE_OBJECT_RADII.get(name)
    if radius is not None:
        geometry["planar_radius"] = max(float(radius), geometry["planar_radius"] * 0.6)
    return geometry


def get_named_body_world_pose(env, name: str) -> tuple[np.ndarray, np.ndarray] | None:
    body_name = _resolve_scene_body_name(env, name)
    if body_name is None:
        return None
    body_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        return None
    # MuJoCo 3.x no longer exposes body_xpos/body_xquat arrays directly on MjData.
    body_state = env.mj_data.body(body_id)
    pos = np.array(body_state.xpos, dtype=np.float64)
    quat = np.array(body_state.xquat, dtype=np.float64)
    return pos, quat


def get_available_table_sponge_bodies(env) -> list[str]:
    available: list[str] = []
    for name in TABLE_SPONGE_BODIES:
        pose = get_named_body_world_pose(env, name)
        if pose is not None:
            available.append(name)
    return available


def get_sponge_rack_slot_world(env, slot_index: int = 0) -> np.ndarray | None:
    anchors: list[np.ndarray] = []
    for name in RACK_SPONGE_BODIES:
        pose = get_named_body_world_pose(env, name)
        if pose is not None:
            anchors.append(np.array(pose[0], dtype=np.float64))
    if len(anchors) >= 2:
        anchors.sort(key=lambda item: float(item[0]))
        step = anchors[1] - anchors[0]
        step[2] = 0.0
        slots = [
            anchors[-1] + step,
            anchors[0] - step,
            anchors[-1] + step * 2.0,
            anchors[0] - step * 2.0,
        ]
        chosen = np.array(slots[min(slot_index, len(slots) - 1)], dtype=np.float64)
        chosen[2] = float(np.mean([anchor[2] for anchor in anchors]) + 0.008)
        return chosen
    if len(anchors) == 1:
        chosen = anchors[0] + np.array([0.08 * float(slot_index + 1), 0.0, 0.0], dtype=np.float64)
        chosen[2] = float(anchors[0][2] + 0.008)
        return chosen
    rack_pose = get_named_body_world_pose(env, "sponge_rack")
    if rack_pose is None:
        return None
    base = np.array(rack_pose[0], dtype=np.float64)
    return base + np.array([0.18 + 0.08 * float(slot_index), 0.58, 0.02], dtype=np.float64)


def get_apple_rack_slot_world(env, slot_index: int = 0) -> np.ndarray | None:
    anchors: list[np.ndarray] = []
    for name in RACK_APPLE_BODIES:
        pose = get_named_body_world_pose(env, name)
        if pose is not None:
            anchors.append(np.array(pose[0], dtype=np.float64))

    rack_pose = get_named_body_world_pose(env, "apple_rack")
    rack_center = np.array(rack_pose[0], dtype=np.float64) if rack_pose is not None else None

    if len(anchors) >= 2:
        center = np.mean(np.asarray(anchors, dtype=np.float64), axis=0)
        candidates = [
            center,
            center + np.array([-0.045, 0.000, 0.000], dtype=np.float64),
            center + np.array([0.045, 0.000, 0.000], dtype=np.float64),
            center + np.array([0.000, 0.040, 0.000], dtype=np.float64),
        ]
        chosen = np.array(candidates[min(slot_index, len(candidates) - 1)], dtype=np.float64)
        chosen[2] = float(center[2] + 0.010)
        return chosen

    if len(anchors) == 1:
        chosen = np.array(anchors[0], dtype=np.float64)
        if slot_index > 0:
            offsets = [
                np.array([-0.045, 0.000, 0.000], dtype=np.float64),
                np.array([0.045, 0.000, 0.000], dtype=np.float64),
                np.array([0.000, 0.040, 0.000], dtype=np.float64),
            ]
            chosen = chosen + offsets[min(slot_index - 1, len(offsets) - 1)]
        chosen[2] = float(anchors[0][2] + 0.010)
        return chosen

    if rack_center is None:
        return None
    fallback = rack_center + np.array([0.17, 0.00, 0.28], dtype=np.float64)
    fallback[2] = float(rack_center[2] + 0.18)
    return fallback


def get_named_site_pose(env, site_name: str) -> tuple[np.ndarray, np.ndarray] | None:
    site_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    if site_id < 0:
        return None
    pos = np.array(env.mj_data.site_xpos[site_id], dtype=np.float64)
    size = np.array(env.mj_model.site_size[site_id], dtype=np.float64)
    return pos, size


def _estimate_body_geometry(env, body_name_or_id) -> dict | None:
    body_id = (
        body_name_or_id
        if isinstance(body_name_or_id, int)
        else mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_name_or_id)
    )
    if body_id < 0:
        return None

    geom_adr = int(env.mj_model.body_geomadr[body_id])
    geom_num = int(env.mj_model.body_geomnum[body_id])
    if geom_num <= 0:
        return None

    centers = []
    radii = []
    for geom_id in range(geom_adr, geom_adr + geom_num):
        center = np.array(env.mj_data.geom_xpos[geom_id], dtype=np.float64)
        radius = float(env.mj_model.geom_rbound[geom_id])
        if radius <= 1e-6:
            size = np.array(env.mj_model.geom_size[geom_id], dtype=np.float64)
            radius = float(np.linalg.norm(size))
        if radius <= 1e-6:
            radius = 0.01
        centers.append(center)
        radii.append(radius)

    centers_np = np.asarray(centers, dtype=np.float64)
    centroid = np.mean(centers_np, axis=0)
    planar_radius = max(
        float(np.linalg.norm(center[:2] - centroid[:2]) + radius)
        for center, radius in zip(centers_np, radii)
    )
    z_tops = np.array(
        [float(center[2] + radius) for center, radius in zip(centers_np, radii)],
        dtype=np.float64,
    )
    z_bottoms = np.array(
        [float(center[2] - radius) for center, radius in zip(centers_np, radii)],
        dtype=np.float64,
    )
    z_top = float(np.percentile(z_tops, 85))
    z_bottom = float(np.percentile(z_bottoms, 15))
    return {
        "centroid": centroid,
        "planar_radius": max(planar_radius, 0.015),
        "z_top": z_top,
        "z_bottom": z_bottom,
        "height": max(z_top - z_bottom, 0.02),
        "points": np.zeros((0, 3), dtype=np.float64),
    }


def _table_workspace_bounds(env) -> tuple[tuple[float, float], tuple[float, float]]:
    island_geometry = _estimate_body_geometry(env, ISLAND_BODY_NAME)
    if island_geometry is not None:
        body_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, ISLAND_BODY_NAME)
        geom_adr = int(env.mj_model.body_geomadr[body_id])
        geom_num = int(env.mj_model.body_geomnum[body_id])
        x_min = np.inf
        x_max = -np.inf
        y_min = np.inf
        y_max = -np.inf
        for geom_id in range(geom_adr, geom_adr + geom_num):
            center = np.array(env.mj_data.geom_xpos[geom_id], dtype=np.float64)
            radius = float(env.mj_model.geom_rbound[geom_id])
            if radius <= 1e-6:
                size = np.array(env.mj_model.geom_size[geom_id], dtype=np.float64)
                radius = float(np.linalg.norm(size))
            x_min = min(x_min, center[0] - radius)
            x_max = max(x_max, center[0] + radius)
            y_min = min(y_min, center[1] - radius)
            y_max = max(y_max, center[1] + radius)

        margin = OPENCLAW_TABLE_MARGIN
        return (
            (float(x_min + margin), float(x_max - margin)),
            (float(y_min + margin), float(y_max - margin)),
        )

    return ((0.45, 1.35), (0.18, 1.02))


def _robot_body_ids(env) -> set[int]:
    root_ids = {
        mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, root_name)
        for root_name in ROBOT_ROOT_BODIES
    }
    root_ids = {root_id for root_id in root_ids if root_id >= 0}
    if not root_ids:
        return set()
    robot_bodies = set()
    for body_id in range(env.mj_model.nbody):
        current = body_id
        while current > 0:
            if current in root_ids:
                robot_bodies.add(body_id)
                break
            current = int(env.mj_model.body_parentid[current])
        if body_id in root_ids:
            robot_bodies.add(body_id)
    return robot_bodies


def _collect_scene_obstacles(env, exclude_names: set[str] | None = None):
    exclude_names = exclude_names or set()
    table_x, table_y = _table_workspace_bounds(env)
    robot_body_ids = _robot_body_ids(env)
    obstacles = []
    for body_id in range(1, env.mj_model.nbody):
        if body_id in robot_body_ids:
            continue
        body_name = mujoco.mj_id2name(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if not body_name or body_name in exclude_names:
            continue
        if body_name in {"mocap", ISLAND_BODY_NAME}:
            continue
        body_jnt_num = int(env.mj_model.body_jntnum[body_id])
        is_free_body = False
        if body_jnt_num > 0:
            jnt_adr = int(env.mj_model.body_jntadr[body_id])
            is_free_body = env.mj_model.jnt_type[jnt_adr] == mujoco.mjtJoint.mjJNT_FREE
        if not is_free_body and body_name not in STATIC_TABLETOP_OBSTACLES:
            continue
        geometry = _estimate_body_geometry(env, body_id)
        if geometry is None:
            continue
        centroid = geometry["centroid"]
        if not (
            table_x[0] - 0.15 <= centroid[0] <= table_x[1] + 0.15
            and table_y[0] - 0.15 <= centroid[1] <= table_y[1] + 0.15
        ):
            continue
        if geometry["z_top"] < TABLE_SURFACE_Z + 0.01:
            continue
        if geometry["planar_radius"] > 0.45:
            continue
        obstacles.append(
            {
                "name": body_name,
                "xy": centroid[:2],
                "radius": geometry["planar_radius"],
                "z_top": geometry["z_top"],
            }
        )
    return obstacles


def estimate_place_target_world(
    env,
    depth_img: np.ndarray,
    destination_mask: np.ndarray,
    source_mask: np.ndarray | None = None,
    relation: str = "next_to",
    source_name: str | None = None,
    destination_name: str | None = None,
) -> np.ndarray:
    destination = get_named_scene_geometry(env, destination_name or "") if destination_name else None
    if destination is None:
        destination = estimate_mask_world_geometry(env, depth_img, destination_mask)
    if destination_name == "plate":
        body_pose = get_named_body_world_pose(env, destination_name)
        if body_pose is not None:
            destination["centroid"] = body_pose[0].copy()

    source = get_named_scene_geometry(env, source_name or "") if source_name else None
    if source is None and source_mask is not None and np.any(source_mask > 0):
        source = estimate_mask_world_geometry(env, depth_img, source_mask)

    destination_xy = destination["centroid"][:2]
    source_xy = source["centroid"][:2] if source is not None else None

    source_radius = source["planar_radius"] if source else 0.04
    source_height = source["height"] if source else 0.04
    gap = destination["planar_radius"] + source_radius + 0.025
    gap = float(np.clip(gap, 0.06, 0.11))
    table_x, table_y = _table_workspace_bounds(env)

    T_wc = _camera_pose(env)
    camera_right = _normalize(T_wc.R[:, 0][:2])
    camera_front = destination_xy - T_wc.t[:2]
    if np.linalg.norm(camera_front) < 1e-8:
        camera_front = np.array([0.0, -1.0], dtype=np.float64)
    camera_front = _normalize(camera_front)

    relation_vectors = {
        "left_of": -camera_right,
        "right_of": camera_right,
        "in_front_of": camera_front,
        "behind": -camera_front,
    }
    if relation == "in":
        xy = destination_xy.copy()
        place_z = destination["z_top"] + max(0.012, source_height * 0.30)
        return np.array([xy[0], xy[1], place_z], dtype=np.float64)

    if relation == "on_top_of":
        xy = destination_xy.copy()
        place_z = destination["z_top"] + max(0.012, source_height * 0.30)
        return np.array([xy[0], xy[1], place_z], dtype=np.float64)

    if relation in relation_vectors:
        xy = destination_xy + gap * relation_vectors[relation]
        xy[0] = np.clip(xy[0], table_x[0], table_x[1])
        xy[1] = np.clip(xy[1], table_y[0], table_y[1])
        place_z = TABLE_SURFACE_Z + max(0.018, source_height * 0.45)
        return np.array([xy[0], xy[1], place_z], dtype=np.float64)

    if relation == "place":
        place_z = TABLE_SURFACE_Z + max(0.018, source_height * 0.45)
        return np.array([destination_xy[0], destination_xy[1], place_z], dtype=np.float64)

    directions = [
        np.array([-1.0, 0.0], dtype=np.float64),
        np.array([1.0, 0.0], dtype=np.float64),
        np.array([0.0, -1.0], dtype=np.float64),
        np.array([0.0, 1.0], dtype=np.float64),
        _normalize(np.array([-1.0, -1.0], dtype=np.float64)),
        _normalize(np.array([-1.0, 1.0], dtype=np.float64)),
        _normalize(np.array([1.0, -1.0], dtype=np.float64)),
        _normalize(np.array([1.0, 1.0], dtype=np.float64)),
    ]

    obstacles = _collect_scene_obstacles(
        env,
        exclude_names={
            name
            for name in [SCENE_BODY_NAMES.get(source_name or ""), SCENE_BODY_NAMES.get(destination_name or "")]
            if name
        },
    )
    candidates = []
    for direction in directions:
        xy = destination_xy + gap * direction
        if not (table_x[0] <= xy[0] <= table_x[1] and table_y[0] <= xy[1] <= table_y[1]):
            continue
        min_clearance = 1e9
        for obstacle in obstacles:
            clearance = float(np.linalg.norm(xy - obstacle["xy"]) - (gap + obstacle["radius"]))
            min_clearance = min(min_clearance, clearance)
        score = 0.0
        if source_xy is not None:
            score = float(np.linalg.norm(xy - source_xy))
        edge_margin = min(xy[0] - table_x[0], table_x[1] - xy[0], xy[1] - table_y[0], table_y[1] - xy[1])
        if min_clearance < 0.01:
            continue
        candidates.append((score - 0.2 * edge_margin - 0.5 * min_clearance, xy))

    if not candidates:
        xy = destination_xy + np.array([-gap, 0.0], dtype=np.float64)
    else:
        xy = min(candidates, key=lambda item: item[0])[1]

    place_z = TABLE_SURFACE_Z + max(0.018, source_height * 0.45)
    return np.array([xy[0], xy[1], place_z], dtype=np.float64)


def estimate_direct_grasp_target_world(
    env,
    depth_img: np.ndarray,
    mask: np.ndarray,
    source_name: str | None = None,
) -> tuple[np.ndarray, dict]:
    geometry = None
    if source_name:
        geometry = get_named_scene_geometry(env, source_name)
    if geometry is None:
        geometry = estimate_mask_world_geometry(env, depth_img, mask)
    target = geometry["centroid"].copy()
    descend_fraction = 0.35
    min_descend = 0.010
    max_descend = 0.022
    if source_name == "duck":
        descend_fraction = 0.12
        min_descend = 0.004
        max_descend = 0.010
    elif source_name == "apple":
        descend_fraction = 0.18
        min_descend = 0.006
        max_descend = 0.014
    descend_offset = float(
        np.clip(geometry["height"] * descend_fraction, min_descend, max_descend)
    )
    target[2] = float(
        np.clip(
            geometry["z_top"] - descend_offset,
            TABLE_SURFACE_Z + 0.020,
            geometry["z_top"] - 0.004,
        )
    )
    return target, geometry


def _move_joint_waypoint(
    env,
    robot,
    action: np.ndarray,
    q_target: np.ndarray,
    duration: float,
    frame_callback=None,
    stage_name: str | None = None,
):
    q_start = np.array(robot.get_joint(), dtype=np.float64)
    q_target = np.array(q_target, dtype=np.float64)
    parameter = JointParameter(q_start, q_target)
    velocity_parameter = QuinticVelocityParameter(duration)
    trajectory_parameter = TrajectoryParameter(parameter, velocity_parameter)
    planner = TrajectoryPlanner(trajectory_parameter)

    total_time = duration
    time_step_num = round(total_time / 0.002) + 1
    times = np.linspace(0.0, total_time, time_step_num)
    frame_every = max(1, len(times) // 12)
    for index, timei in enumerate(times):
        if timei == 0.0:
            continue
        joint = planner.interpolate(timei)
        robot.move_joint(joint)
        action[:6] = joint
        env.step(action)
        if frame_callback is not None and (index % frame_every == 0 or index == len(times) - 1):
            try:
                frame_callback(stage_name or "motion", env)
            except Exception:
                pass


def _solve_ik_waypoint(robot, target_pose: sm.SE3, seed_q, label: str) -> np.ndarray:
    previous_q = np.array(robot.get_joint(), dtype=np.float64)
    try:
        robot.set_joint(list(np.array(seed_q, dtype=np.float64)))
        q = robot.ikine(target_pose)
    finally:
        robot.set_joint(list(previous_q))

    if len(q) == 0:
        raise RuntimeError(f"IK failed for {label}")

    return np.array(q, dtype=np.float64)


def _scratch_data_with_robot_configuration(env, q: np.ndarray) -> mujoco.MjData:
    q = np.array(q, dtype=np.float64)
    scratch = mujoco.MjData(env.mj_model)
    scratch.qpos[:] = env.mj_data.qpos[:]
    scratch.qvel[:] = env.mj_data.qvel[:]
    if env.mj_model.na > 0:
        scratch.act[:] = env.mj_data.act[:]
    for i, joint_name in enumerate(env.joint_names):
        mj_utils.set_joint_q(env.mj_model, scratch, joint_name, q[i])
    mujoco.mj_forward(env.mj_model, scratch)
    return scratch


def _describe_robot_scene_collision(
    env,
    robot,
    q: np.ndarray,
    allowed_body_names: set[str] | None = None,
) -> str | None:
    allowed_body_names = allowed_body_names or set()
    robot_body_ids = _robot_body_ids(env)
    scratch = _scratch_data_with_robot_configuration(env, q)
    for contact_idx in range(scratch.ncon):
        contact = scratch.contact[contact_idx]
        body1 = int(env.mj_model.geom_bodyid[contact.geom1])
        body2 = int(env.mj_model.geom_bodyid[contact.geom2])
        if body1 not in robot_body_ids and body2 not in robot_body_ids:
            continue

        if body1 in robot_body_ids and body2 in robot_body_ids:
            continue

        other_body = body2 if body1 in robot_body_ids else body1
        other_name = mujoco.mj_id2name(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, other_body)
        if other_name in allowed_body_names:
            continue
        if contact.dist < OPENCLAW_CONTACT_TOL:
            robot_body = body1 if body1 in robot_body_ids else body2
            robot_name = mujoco.mj_id2name(
                env.mj_model, mujoco.mjtObj.mjOBJ_BODY, robot_body
            )
            return f"{robot_name} vs {other_name}: dist={contact.dist:.4f}"
    return None


def _configuration_has_robot_scene_collision(
    env,
    robot,
    q: np.ndarray,
    allowed_body_names: set[str] | None = None,
) -> bool:
    return (
        _describe_robot_scene_collision(
            env,
            robot,
            q,
            allowed_body_names=allowed_body_names,
        )
        is not None
    )


def _solve_pose_candidates(
    robot,
    candidates,
    seed_q,
    label: str,
    env=None,
    allowed_body_names: set[str] | None = None,
):
    last_error = None
    for idx, (target_pose, note) in enumerate(candidates):
        try:
            q = _solve_ik_waypoint(robot, target_pose, seed_q, f"{label} [{note}]")
            if env is not None and OPENCLAW_ENABLE_SCENE_COLLISION:
                collision_detail = _describe_robot_scene_collision(
                    env,
                    robot,
                    q,
                    allowed_body_names=allowed_body_names,
                )
                if collision_detail is not None:
                    raise RuntimeError(
                        f"scene collision for {label} [{note}] -> {collision_detail}"
                    )
            print(f"[ik] {label}: using candidate '{note}'")
            return target_pose, q
        except Exception as exc:
            last_error = exc
            continue

    if last_error is None:
        raise RuntimeError(f"No candidate poses generated for {label}")
    raise last_error


def _build_topdown_pose_from_world(
    world_point: np.ndarray,
    finger_axis_hint: np.ndarray | None = None,
) -> sm.SE3:
    finger_axis = np.array(
        finger_axis_hint if finger_axis_hint is not None else [1.0, 0.0, 0.0],
        dtype=np.float64,
    )
    finger_axis[2] = 0.0
    if np.linalg.norm(finger_axis) < 1e-8:
        finger_axis = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    finger_axis = _normalize(finger_axis)

    approach_axis = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    lateral_axis = np.cross(approach_axis, finger_axis)
    if np.linalg.norm(lateral_axis) < 1e-8:
        finger_axis = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        lateral_axis = np.cross(approach_axis, finger_axis)
    lateral_axis = _normalize(lateral_axis)
    finger_axis = _normalize(np.cross(lateral_axis, approach_axis))

    rotation_world = np.column_stack((approach_axis, finger_axis, lateral_axis))
    return sm.SE3.Rt(sm.SO3(rotation_world), np.array(world_point, dtype=np.float64))


def _build_topdown_grasp_pose(T_wc: sm.SE3, gg: GraspGroup) -> sm.SE3:
    grasp_translation_camera = np.array(gg.translations[0], dtype=np.float64)
    # GraspNet uses the standard CV camera frame (x right, y down, z forward),
    # while MuJoCo camera poses follow an OpenGL-style frame (x right, y up, z backward).
    camera_to_mujoco = np.diag([1.0, -1.0, -1.0])
    grasp_translation_world = (
        T_wc * sm.SE3.Trans(camera_to_mujoco @ grasp_translation_camera)
    ).t

    raw_rotation_world = T_wc.R @ camera_to_mujoco @ gg.rotation_matrices[0]
    finger_axis = raw_rotation_world[:, 1].copy()
    return _build_topdown_pose_from_world(grasp_translation_world, finger_axis)


def _make_local_x_rotation_candidates(base_pose: sm.SE3, offsets, yaw_values):
    candidates = []
    for offset in offsets:
        for yaw in yaw_values:
            pose = base_pose * sm.SE3(offset, 0.0, 0.0) * sm.SE3.Rx(yaw)
            candidates.append((pose, f"x={offset:.3f}, rx={yaw:.3f}"))
    return candidates


def _make_world_translation_candidates(base_pose: sm.SE3, xyz_offsets, yaw_values):
    candidates = []
    base_translation = np.array(base_pose.t, dtype=np.float64)
    base_rotation = sm.SO3(base_pose.R)
    for offset in xyz_offsets:
        offset = np.array(offset, dtype=np.float64)
        for yaw in yaw_values:
            pose = sm.SE3.Trans(*(base_translation + offset)) * sm.SE3(base_rotation) * sm.SE3.Rx(yaw)
            candidates.append(
                (
                    pose,
                    f"world=({offset[0]:.3f},{offset[1]:.3f},{offset[2]:.3f}), rx={yaw:.3f}",
                )
            )
    return candidates


def _compute_safe_travel_z(env, xy_points: list[np.ndarray]) -> float:
    travel_z = max(OPENCLAW_TRAVEL_Z, TABLE_SURFACE_Z + 0.30)
    obstacles = _collect_scene_obstacles(env)
    for xy in xy_points:
        for obstacle in obstacles:
            clearance = np.linalg.norm(np.array(xy, dtype=np.float64) - obstacle["xy"])
            if clearance <= obstacle["radius"] + 0.20:
                travel_z = max(travel_z, obstacle["z_top"] + 0.08)
    return float(np.clip(travel_z, TABLE_SURFACE_Z + 0.25, 1.38))


def _transit_hub_xy(env, fallback_xy: np.ndarray) -> np.ndarray:
    base_id = mujoco.mj_name2id(env.mj_model, mujoco.mjtObj.mjOBJ_BODY, "ur5e_base")
    if base_id < 0:
        return np.array(fallback_xy, dtype=np.float64)
    base_xy = np.array(env.mj_data.xpos[base_id][:2], dtype=np.float64)
    table_x, table_y = _table_workspace_bounds(env)
    hub_xy = base_xy + np.array([0.22, 0.34], dtype=np.float64)
    hub_xy[0] = np.clip(hub_xy[0], table_x[0], table_x[1])
    hub_xy[1] = np.clip(hub_xy[1], table_y[0], table_y[1])
    return hub_xy


def execute_grasp(
    env,
    gg,
    place_target_world: np.ndarray | None = None,
    grasp_target_world: np.ndarray | None = None,
    source_name: str | None = None,
    place_mode: str | None = None,
    frame_callback=None,
):
    robot = env.robot

    T_wc = _camera_pose(env)
    if grasp_target_world is None:
        T_wo = _build_topdown_grasp_pose(T_wc, gg)
    else:
        T_wo = _build_topdown_pose_from_world(np.array(grasp_target_world, dtype=np.float64))

    source_body_name = SCENE_BODY_NAMES.get(source_name or "")
    finger_axis_hint = np.array(T_wo.R[:, 1], dtype=np.float64)

    action = np.zeros(7)
    durations = {
        "home": 0.8,
        "hub": 0.9,
        "hover_pick": 0.9,
        "pregrasp": 0.8,
        "grasp": 0.7,
        "lift": 0.9,
        "hover_place": 0.9,
        "place": 0.8,
        "retreat": 0.8,
        "reset": 1.0,
    }

    q0 = np.array(robot.get_joint(), dtype=np.float64)
    q_home = np.array([0.0, 0.0, np.pi / 2, 0.0, -np.pi / 2, 0.0], dtype=np.float64)
    _move_joint_waypoint(env, robot, action, q_home, durations["home"], frame_callback=frame_callback, stage_name="home")

    yaw_values = [0.0, np.pi / 2, -np.pi / 2, np.pi]
    pick_xy = np.array(T_wo.t[:2], dtype=np.float64)
    place_xy = (
        np.array(place_target_world[:2], dtype=np.float64)
        if place_target_world is not None
        else pick_xy.copy()
    )
    travel_z = _compute_safe_travel_z(env, [pick_xy, place_xy])
    hub_xy = _transit_hub_xy(env, pick_xy)

    T_hub = _build_topdown_pose_from_world(
        np.array([hub_xy[0], hub_xy[1], travel_z], dtype=np.float64),
        finger_axis_hint,
    )
    hub_candidates = _make_world_translation_candidates(
        T_hub,
        xyz_offsets=[
            (0.0, 0.0, 0.0),
            (0.03, 0.0, 0.0),
            (-0.03, 0.0, 0.0),
            (0.0, 0.03, 0.0),
            (0.0, -0.03, 0.0),
        ],
        yaw_values=yaw_values,
    )
    T_hub, q_hub = _solve_pose_candidates(
        robot, hub_candidates, q_home, "hub", env=env
    )
    _move_joint_waypoint(env, robot, action, q_hub, durations["hub"], frame_callback=frame_callback, stage_name="hub")

    T_hover_pick = _build_topdown_pose_from_world(
        np.array([pick_xy[0], pick_xy[1], travel_z], dtype=np.float64),
        finger_axis_hint,
    )
    hover_pick_candidates = _make_world_translation_candidates(
        T_hover_pick,
        xyz_offsets=[
            (0.0, 0.0, 0.0),
            (0.02, 0.0, 0.0),
            (-0.02, 0.0, 0.0),
            (0.0, 0.02, 0.0),
            (0.0, -0.02, 0.0),
        ],
        yaw_values=yaw_values,
    )
    T_hover_pick, q_hover_pick = _solve_pose_candidates(
        robot, hover_pick_candidates, q_hub, "hover_pick", env=env
    )
    _move_joint_waypoint(env, robot, action, q_hover_pick, durations["hover_pick"], frame_callback=frame_callback, stage_name="hover_pick")

    pregrasp_z = max(T_wo.t[2] + OPENCLAW_PREGRASP_CLEARANCE, TABLE_SURFACE_Z + 0.10)
    T_pregrasp = _build_topdown_pose_from_world(
        np.array([pick_xy[0], pick_xy[1], pregrasp_z], dtype=np.float64),
        finger_axis_hint,
    )
    pregrasp_candidates = _make_world_translation_candidates(
        T_pregrasp,
        xyz_offsets=[
            (0.0, 0.0, 0.0),
            (0.01, 0.0, 0.0),
            (-0.01, 0.0, 0.0),
            (0.0, 0.01, 0.0),
            (0.0, -0.01, 0.0),
            (0.0, 0.0, 0.02),
        ],
        yaw_values=yaw_values,
    )
    T_pregrasp, q_pregrasp = _solve_pose_candidates(
        robot,
        pregrasp_candidates,
        q_hover_pick,
        "pregrasp",
        env=env,
        allowed_body_names={source_body_name} if source_body_name else None,
    )
    _move_joint_waypoint(env, robot, action, q_pregrasp, durations["pregrasp"], frame_callback=frame_callback, stage_name="pregrasp")

    grasp_candidates = _make_world_translation_candidates(
        T_wo,
        xyz_offsets=[
            (0.0, 0.0, 0.0),
            (0.006, 0.0, 0.0),
            (-0.006, 0.0, 0.0),
            (0.0, 0.006, 0.0),
            (0.0, -0.006, 0.0),
            (0.0, 0.0, 0.008),
        ],
        yaw_values=yaw_values,
    )
    T_grasp, q_grasp = _solve_pose_candidates(
        robot,
        grasp_candidates,
        q_pregrasp,
        "grasp",
        env=env,
        allowed_body_names={source_body_name} if source_body_name else None,
    )
    _move_joint_waypoint(env, robot, action, q_grasp, durations["grasp"], frame_callback=frame_callback, stage_name="grasp")

    for _ in range(1000):
        action[-1] = min(action[-1] + 0.2, 255)
        env.step(action)
    if frame_callback is not None:
        try:
            frame_callback("grasp_close", env)
        except Exception:
            pass

    T_lift = _build_topdown_pose_from_world(
        np.array([pick_xy[0], pick_xy[1], travel_z], dtype=np.float64),
        finger_axis_hint,
    )
    lift_candidates = _make_world_translation_candidates(
        T_lift,
        xyz_offsets=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.04)],
        yaw_values=yaw_values,
    )
    T_lift, q_lift = _solve_pose_candidates(
        robot,
        lift_candidates,
        q_grasp,
        "lift",
        env=env,
        allowed_body_names={source_body_name} if source_body_name else None,
    )
    _move_joint_waypoint(env, robot, action, q_lift, durations["lift"], frame_callback=frame_callback, stage_name="lift")

    if place_target_world is None:
        place_xyz = np.array(
            [T_grasp.t[0], T_grasp.t[1], max(T_grasp.t[2] + 0.02, TABLE_SURFACE_Z + 0.02)],
            dtype=np.float64,
        )
    else:
        place_target_world = np.array(place_target_world, dtype=np.float64)
        place_xyz = place_target_world

    T_hover_place = _build_topdown_pose_from_world(
        np.array([place_xyz[0], place_xyz[1], travel_z], dtype=np.float64),
        finger_axis_hint,
    )
    if place_mode and place_mode.startswith("drop_above"):
        hover_place_candidates = _make_world_translation_candidates(
            T_hover_place,
            xyz_offsets=[
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.05),
            ],
            yaw_values=yaw_values,
        )
    else:
        hover_place_candidates = _make_world_translation_candidates(
            T_hover_place,
            xyz_offsets=[
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.05),
                (0.03, 0.0, 0.0),
                (-0.03, 0.0, 0.0),
                (0.0, 0.03, 0.0),
                (0.0, -0.03, 0.0),
            ],
            yaw_values=yaw_values,
        )
    T_hover_place, q_hover_place = _solve_pose_candidates(
        robot,
        hover_place_candidates,
        q_lift,
        "hover_place",
        env=env,
        allowed_body_names={source_body_name} if source_body_name else None,
    )
    _move_joint_waypoint(env, robot, action, q_hover_place, durations["hover_place"], frame_callback=frame_callback, stage_name="hover_place")

    if place_mode == "drop_above":
        preplace_z = float(place_xyz[2])
    elif place_mode == "drop_above_plate":
        preplace_z = float(place_xyz[2])
    else:
        preplace_z = max(place_xyz[2] + OPENCLAW_PLACE_CLEARANCE, TABLE_SURFACE_Z + 0.09)
    T_preplace = _build_topdown_pose_from_world(
        np.array([place_xyz[0], place_xyz[1], preplace_z], dtype=np.float64),
        finger_axis_hint,
    )
    if place_mode and place_mode.startswith("drop_above"):
        preplace_candidates = _make_world_translation_candidates(
            T_preplace,
            xyz_offsets=[
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.03),
            ],
            yaw_values=yaw_values,
        )
    else:
        preplace_candidates = _make_world_translation_candidates(
            T_preplace,
            xyz_offsets=[
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.03),
                (0.02, 0.0, 0.0),
                (-0.02, 0.0, 0.0),
                (0.0, 0.02, 0.0),
                (0.0, -0.02, 0.0),
            ],
            yaw_values=yaw_values,
        )
    T_preplace, q_preplace = _solve_pose_candidates(
        robot,
        preplace_candidates,
        q_hover_place,
        "preplace",
        env=env,
        allowed_body_names={source_body_name} if source_body_name else None,
    )
    _move_joint_waypoint(env, robot, action, q_preplace, durations["place"], frame_callback=frame_callback, stage_name="preplace")

    if place_mode and place_mode.startswith("drop_above"):
        place_exec_xyz = np.array([place_xyz[0], place_xyz[1], preplace_z], dtype=np.float64)
        T_place = _build_topdown_pose_from_world(place_exec_xyz, finger_axis_hint)
        q_place = q_preplace
    else:
        place_exec_xyz = np.array([place_xyz[0], place_xyz[1], place_xyz[2]], dtype=np.float64)
        T_place = _build_topdown_pose_from_world(place_exec_xyz, finger_axis_hint)
        place_candidates = _make_world_translation_candidates(
            T_place,
            xyz_offsets=[
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.03),
                (0.02, 0.0, 0.0),
                (-0.02, 0.0, 0.0),
                (0.0, 0.02, 0.0),
                (0.0, -0.02, 0.0),
            ],
            yaw_values=yaw_values,
        )
        T_place, q_place = _solve_pose_candidates(
            robot,
            place_candidates,
            q_preplace,
            "place",
            env=env,
            allowed_body_names={source_body_name} if source_body_name else None,
        )
        _move_joint_waypoint(env, robot, action, q_place, durations["place"], frame_callback=frame_callback, stage_name="place")

    for _ in range(1000):
        action[-1] = max(action[-1] - 0.2, 0)
        env.step(action)
    if frame_callback is not None:
        try:
            frame_callback("release", env)
        except Exception:
            pass

    T_retreat = _build_topdown_pose_from_world(
        np.array([place_xyz[0], place_xyz[1], travel_z], dtype=np.float64),
        finger_axis_hint,
    )
    retreat_candidates = _make_world_translation_candidates(
        T_retreat,
        xyz_offsets=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.05)],
        yaw_values=yaw_values,
    )
    T_retreat, q_retreat = _solve_pose_candidates(
        robot, retreat_candidates, q_place, "retreat", env=env
    )
    _move_joint_waypoint(env, robot, action, q_retreat, durations["retreat"], frame_callback=frame_callback, stage_name="retreat")

    hub_return_candidates = _make_world_translation_candidates(
        T_hub,
        xyz_offsets=[
            (0.0, 0.0, 0.0),
            (0.03, 0.0, 0.0),
            (-0.03, 0.0, 0.0),
            (0.0, 0.03, 0.0),
            (0.0, -0.03, 0.0),
        ],
        yaw_values=yaw_values,
    )
    _, q_hub_return = _solve_pose_candidates(
        robot, hub_return_candidates, q_retreat, "hub_return", env=env
    )
    _move_joint_waypoint(env, robot, action, q_hub_return, durations["hub"], frame_callback=frame_callback, stage_name="hub_return")

    _move_joint_waypoint(env, robot, action, q0, durations["reset"], frame_callback=frame_callback, stage_name="reset")

