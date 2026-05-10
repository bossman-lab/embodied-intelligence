"""Tool router for the OpenClaw-like agent flow."""

import math
import os
import queue
import sys
import time

import cv2
import glfw
import mujoco
import mujoco.viewer
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "models"))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "dataset"))
sys.path.append(os.path.join(ROOT_DIR, "graspnet-baseline", "utils"))
sys.path.append(os.path.join(ROOT_DIR, "manipulator_grasp"))

from camera_view import save_view_config
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv


class _TeleopViewer:
    COLLISION_DEBUG_BODIES = {
        "apple_2",
        "Duck",
        "Knife",
        "Hammer",
        "Plate",
        "Banana",
        "DigitalScale",
        "GlassCup",
        "FlourBag",
        "FlowerVase",
        "Shelf",
        "MugTree",
        "KnifeBlock",
    }

    def __init__(self, env: UR5GraspEnv) -> None:
        self.env = env
        self.command_queue: queue.Queue[int] = queue.Queue()
        self.viewer = None
        self.running = False
        self.request_exit = False

        self.translation_step = float(os.getenv("OPENCLAW_TELEOP_STEP", "0.03"))
        self.rotation_step_deg = float(os.getenv("OPENCLAW_TELEOP_YAW_DEG", "10"))
        self.gripper_step = float(os.getenv("OPENCLAW_TELEOP_GRIP_STEP", "22"))
        self.settle_steps = int(os.getenv("OPENCLAW_TELEOP_SETTLE_STEPS", "10"))
        self.max_joint_jump = float(os.getenv("OPENCLAW_TELEOP_MAX_JOINT_JUMP", "1.25"))
        self.max_joint_jump_norm = float(os.getenv("OPENCLAW_TELEOP_MAX_JOINT_JUMP_NORM", "1.90"))
        self.current_gripper = 0.0
        self.action = np.zeros(7, dtype=np.float64)
        self.show_collision = False
        self.q_home = None
        self.home_xyz = None
        self.home_yaw = 0.0

    def _handle_key(self, keycode: int) -> None:
        self.command_queue.put(keycode)

    def _current_target_pose(self):
        from grasp_process import _build_topdown_pose_from_world

        axis = np.array(
            [math.cos(self.target_yaw), math.sin(self.target_yaw), 0.0],
            dtype=np.float64,
        )
        return _build_topdown_pose_from_world(self.target_xyz, axis)

    def _solve_pose_local(self, xyz: np.ndarray, yaw: float, seed_q: np.ndarray) -> np.ndarray:
        robot = self.env.robot
        target_pose = self._current_target_pose() if xyz is self.target_xyz and yaw == self.target_yaw else None
        if target_pose is None:
            from grasp_process import _build_topdown_pose_from_world

            axis = np.array([math.cos(yaw), math.sin(yaw), 0.0], dtype=np.float64)
            target_pose = _build_topdown_pose_from_world(xyz, axis)
        robot.set_joint(seed_q.tolist())
        q_target = np.array([])
        try:
            sol = robot.robot.ikine_LM(
                target_pose,
                q0=seed_q,
                ilimit=60,
                slimit=18,
                tol=5e-4,
                joint_limits=False,
                mask=[1, 1, 1, 1, 1, 1],
            )
            if getattr(sol, "success", False):
                q_target = np.array(sol.q, dtype=np.float64)
        except Exception:
            q_target = np.array([])
        if len(q_target) == 0:
            try:
                q_target = np.array(robot.ikine(target_pose), dtype=np.float64)
            except Exception:
                q_target = np.array([])
        robot.set_joint(seed_q.tolist())
        return q_target

    def _apply_joint_target(self, q_target: np.ndarray) -> None:
        q_target = np.array(q_target, dtype=np.float64)
        self.action[:6] = q_target
        for _ in range(self.settle_steps):
            self.env.step(self.action)
        self.env.robot.set_joint(q_target.tolist())

    def _fast_move_to_target(self, label: str, proposed_xyz=None, proposed_yaw=None) -> bool:
        previous_q = np.array(self.env.robot.get_joint(), dtype=np.float64)
        start_xyz = self.target_xyz.copy()
        start_yaw = float(self.target_yaw)
        goal_xyz = np.array(proposed_xyz if proposed_xyz is not None else self.target_xyz, dtype=np.float64)
        goal_yaw = float(proposed_yaw if proposed_yaw is not None else self.target_yaw)

        for scale in [1.0, 0.5, 0.25, 0.125]:
            cand_xyz = start_xyz + scale * (goal_xyz - start_xyz)
            cand_yaw = start_yaw + scale * (goal_yaw - start_yaw)
            q_target = self._solve_pose_local(cand_xyz, cand_yaw, previous_q)
            if len(q_target) == 0:
                continue

            wrapped = np.arctan2(np.sin(q_target - previous_q), np.cos(q_target - previous_q))
            if np.max(np.abs(wrapped)) > self.max_joint_jump or np.linalg.norm(wrapped) > self.max_joint_jump_norm:
                continue

            self._apply_joint_target(q_target)
            self.target_xyz[:] = cand_xyz
            self.target_yaw = cand_yaw
            if scale < 1.0:
                print(f"[teleop] clipped step for {label} by scale={scale:.3f}")
            return True

        print(f"[teleop] IK/jump failed for {label}")
        return True

    def _clamp_target(self) -> None:
        self.target_xyz[0] = float(
            np.clip(self.target_xyz[0], self.table_x[0], self.table_x[1])
        )
        self.target_xyz[1] = float(
            np.clip(self.target_xyz[1], self.table_y[0], self.table_y[1])
        )
        self.target_xyz[2] = float(
            np.clip(
                self.target_xyz[2],
                self.table_z + 0.08,
                self.table_z + 0.60,
            )
        )

    def _reset_home(self) -> None:
        if self.q_home is None:
            return
        self._apply_joint_target(self.q_home)
        self.target_xyz[:] = self.home_xyz
        self.target_yaw = self.home_yaw
        self._clamp_target()
        return

    def _initialize_home(self) -> None:
        from grasp_process import _build_topdown_pose_from_world

        seed_q = np.array([0.0, 0.0, np.pi / 2, 0.0, -np.pi / 2, 0.0], dtype=np.float64)
        self.home_xyz = np.array(
            [self.table_center[0], self.table_center[1], self.table_z + 0.30],
            dtype=np.float64,
        )
        best = None
        for yaw in [0.0, math.pi / 2, -math.pi / 2, math.pi]:
            axis = np.array([math.cos(yaw), math.sin(yaw), 0.0], dtype=np.float64)
            pose = _build_topdown_pose_from_world(self.home_xyz, axis)
            robot = self.env.robot
            robot.set_joint(seed_q.tolist())
            try:
                sol = robot.robot.ikine_LM(
                    pose,
                    q0=seed_q,
                    ilimit=80,
                    slimit=20,
                    tol=1e-4,
                    joint_limits=False,
                    mask=[1, 1, 1, 1, 1, 1],
                )
                q_candidate = np.array(sol.q, dtype=np.float64) if getattr(sol, "success", False) else np.array([])
            except Exception:
                q_candidate = np.array([])
            robot.set_joint(seed_q.tolist())
            if len(q_candidate) == 0:
                continue
            diff = np.arctan2(np.sin(q_candidate - seed_q), np.cos(q_candidate - seed_q))
            score = float(np.linalg.norm(diff))
            if best is None or score < best[0]:
                best = (score, yaw, q_candidate)

        if best is None:
            self.q_home = seed_q.copy()
            self.home_yaw = 0.0
        else:
            self.home_yaw = float(best[1])
            self.q_home = np.array(best[2], dtype=np.float64)

    def _set_collision_debug_group(self, enabled: bool) -> None:
        model = self.env.mj_model
        for geom_id in range(model.ngeom):
            body_id = int(model.geom_bodyid[geom_id])
            body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
            if body_name in self.COLLISION_DEBUG_BODIES and model.geom_group[geom_id] in {0, 2}:
                model.geom_group[geom_id] = 2 if enabled else 0
                if model.geom_rgba[geom_id, 3] <= 0.0:
                    model.geom_rgba[geom_id] = np.array([0.2, 0.9, 0.2, 0.35], dtype=np.float32)

    def _set_overlay(self) -> None:
        if self.viewer is None:
            return
        left = "\n".join(
            [
                "OpenClaw Teleop",
                "",
                "Move XY: Arrow keys",
                "Move Z: PageUp/PageDown",
                "Rotate Z(yaw): F9 / F10",
                "Gripper: O open / C close",
                "Step size: - / =",
                "Home: H",
                "Collision debug: F3",
                "Save view: F12",
                "Quit: Esc / Q",
            ]
        )
        right = "\n".join(
            [
                f"xyz = [{self.target_xyz[0]:.3f}, {self.target_xyz[1]:.3f}, {self.target_xyz[2]:.3f}]",
                f"yaw = {math.degrees(self.target_yaw):.1f} deg",
                f"gripper = {self.action[-1]:.1f}",
                "",
                f"translate step = {self.translation_step:.3f} m",
                f"rotate step = {self.rotation_step_deg:.1f} deg",
                f"settle steps = {self.settle_steps}",
                f"jump limit = {self.max_joint_jump:.2f} rad",
                f"collision debug = {self.show_collision}",
                f"scene = {self.env.scene_path.name if self.env.scene_path else 'unknown'}",
            ]
        )
        texts = [
            (
                mujoco.mjtFontScale.mjFONTSCALE_150,
                mujoco.mjtGridPos.mjGRID_TOPLEFT,
                left,
                right,
            )
        ]
        self.viewer.set_texts(texts)

    def _save_current_view(self) -> None:
        if self.viewer is None or self.env.scene_path is None:
            return
        path = save_view_config(
            self.env.scene_path,
            lookat=self.viewer.cam.lookat,
            azimuth=self.viewer.cam.azimuth,
            elevation=self.viewer.cam.elevation,
            distance=self.viewer.cam.distance,
        )
        print(f"[teleop] saved view: {path}")

    def _process_commands(self) -> bool:
        moved = False
        delta_xyz = np.zeros(3, dtype=np.float64)
        delta_yaw = 0.0
        while True:
            try:
                keycode = self.command_queue.get_nowait()
            except queue.Empty:
                break

            if keycode in (glfw.KEY_ESCAPE, glfw.KEY_Q):
                self.request_exit = True
                return False
            if keycode == glfw.KEY_UP:
                delta_xyz[0] += self.translation_step
                moved = True
            elif keycode == glfw.KEY_DOWN:
                delta_xyz[0] -= self.translation_step
                moved = True
            elif keycode == glfw.KEY_LEFT:
                delta_xyz[1] += self.translation_step
                moved = True
            elif keycode == glfw.KEY_RIGHT:
                delta_xyz[1] -= self.translation_step
                moved = True
            elif keycode == glfw.KEY_PAGE_UP:
                delta_xyz[2] += self.translation_step
                moved = True
            elif keycode == glfw.KEY_PAGE_DOWN:
                delta_xyz[2] -= self.translation_step
                moved = True
            elif keycode == glfw.KEY_F9:
                delta_yaw += math.radians(self.rotation_step_deg)
                moved = True
            elif keycode == glfw.KEY_F10:
                delta_yaw -= math.radians(self.rotation_step_deg)
                moved = True
            elif keycode in (ord("O"), ord("o")):
                self.current_gripper = float(
                    np.clip(self.current_gripper - self.gripper_step, 0.0, 255.0)
                )
                self.action[-1] = self.current_gripper
            elif keycode in (ord("C"), ord("c")):
                self.current_gripper = float(
                    np.clip(self.current_gripper + self.gripper_step, 0.0, 255.0)
                )
                self.action[-1] = self.current_gripper
            elif keycode in (ord("-"),):
                self.translation_step = max(0.005, self.translation_step - 0.005)
            elif keycode in (ord("="),):
                self.translation_step = min(0.08, self.translation_step + 0.005)
            elif keycode in (ord("H"), ord("h")):
                self._reset_home()
            elif keycode == glfw.KEY_F3:
                self.show_collision = not self.show_collision
                self._set_collision_debug_group(self.show_collision)
                try:
                    self.viewer.opt.geomgroup[2] = 1 if self.show_collision else 0
                except Exception:
                    pass
            elif keycode == glfw.KEY_F12:
                self._save_current_view()

        if moved:
            proposed_xyz = self.target_xyz.copy() + delta_xyz
            proposed_yaw = float(self.target_yaw + delta_yaw)
            old_xyz = self.target_xyz.copy()
            old_yaw = float(self.target_yaw)
            self.target_xyz[:] = proposed_xyz
            self.target_yaw = proposed_yaw
            self._clamp_target()
            proposed_xyz = self.target_xyz.copy()
            proposed_yaw = float(self.target_yaw)
            self.target_xyz[:] = old_xyz
            self.target_yaw = old_yaw
            self._fast_move_to_target("teleop", proposed_xyz=proposed_xyz, proposed_yaw=proposed_yaw)
        return True

    def run(self):
        from grasp_process import TABLE_SURFACE_Z, _table_workspace_bounds

        if self.env.mj_viewer is not None:
            try:
                self.env.mj_viewer.close()
            except Exception:
                pass
            self.env.mj_viewer = None

        self.table_z = TABLE_SURFACE_Z
        self.table_x, self.table_y = _table_workspace_bounds(self.env)
        self.table_center = np.array(
            [
                (self.table_x[0] + self.table_x[1]) * 0.5,
                (self.table_y[0] + self.table_y[1]) * 0.5,
            ],
            dtype=np.float64,
        )
        self.target_xyz = np.array([self.table_center[0], self.table_center[1], self.table_z + 0.30], dtype=np.float64)
        self.target_yaw = 0.0

        self.action[:] = 0.0
        self.action[:6] = np.array(self.env.robot.get_joint(), dtype=np.float64)
        self.action[-1] = self.current_gripper
        self._initialize_home()
        self._reset_home()

        print("[teleop] viewer mode started")

        with mujoco.viewer.launch_passive(
            self.env.mj_model,
            self.env.mj_data,
            key_callback=self._handle_key,
            show_left_ui=True,
            show_right_ui=True,
        ) as viewer:
            self.viewer = viewer
            self.request_exit = False
            self._set_collision_debug_group(False)
            try:
                self.viewer.opt.geomgroup[0] = 0
                self.viewer.opt.geomgroup[2] = 0
            except Exception:
                pass
            self.env._apply_saved_view(self.viewer)
            self.running = True

            while viewer.is_running() and self.running:
                with viewer.lock():
                    if not self._process_commands():
                        self.running = False
                    for _ in range(2):
                        self.env.step(self.action)
                    self._set_overlay()
                if self.request_exit:
                    break
                viewer.sync()
                time.sleep(1.0 / 60.0)

        self.viewer = None
        self.env._try_launch_viewer()
        return {"status": "ok", "task": "teleop"}


class ToolRouter:
    OBJECT_ALIASES = {
        "banana": ["banana", "bananas", "xiangjiao", "香蕉"],
        "apple": ["apple", "pingguo", "苹果"],
        "chocolate": ["chocolate", "choco", "chocolate bar", "巧克力", "巧克力棒", "巧克力块"],
        "duck": ["duck", "yellow duck", "little yellow duck", "toy duck", "duckie", "小黄鸭", "鸭子"],
        "hammer": ["hammer", "锤子"],
        "knife": ["knife", "刀", "小刀"],
        "plate": ["plate", "dish", "saucer", "盘子", "碟子", "餐盘"],
        "shelf": ["shelf", "rack", "layer shelf", "置物架", "架子", "层架"],
    }
    PLACE_KEYWORDS = ["place", "put", "move", "relocate", "放", "摆", "移到", "放到", "放在"]
    RELATION_KEYWORDS = {
        "in": ["in", "inside", "into", "放进", "放到里面", "放到盒子里", "里面"],
        "on_top_of": ["on top of", "on", "top of", "上面", "顶上", "架子上", "层板上"],
        "left_of": ["left of", "to the left of", "左边", "左侧"],
        "right_of": ["right of", "to the right of", "右边", "右侧"],
        "in_front_of": ["in front of", "front of", "前面", "前方"],
        "behind": ["behind", "at the back of", "后面", "后方"],
        "next_to": ["next to", "beside", "near", "旁边", "附近", "边上"],
    }
    DANCE_KEYWORDS = ["dance", "跳舞", "wave", "摇摆"]
    TELEOP_KEYWORDS = [
        "teleop",
        "tele-operation",
        "manual",
        "keyboard",
        "tail off",
        "遥操作",
        "手动",
        "键盘控制",
    ]

    def __init__(self) -> None:
        self.env = UR5GraspEnv()
        self.env.reset()

    def close(self) -> None:
        self.env.close()

    def _capture_rgbd(self):
        for _ in range(500):
            self.env.step()
        imgs = self.env.render()
        color_img = cv2.cvtColor(imgs["img"], cv2.COLOR_RGB2BGR)
        depth_img = imgs["depth"]
        return color_img, depth_img

    def _extract_objects(self, command_text: str):
        text = command_text.lower()
        hits = []
        for canonical, aliases in self.OBJECT_ALIASES.items():
            best_index = None
            for alias in aliases:
                index = text.find(alias.lower())
                if index >= 0 and (best_index is None or index < best_index):
                    best_index = index
            if best_index is not None:
                hits.append((best_index, canonical))
        hits.sort(key=lambda item: item[0])
        ordered = []
        for _, canonical in hits:
            if canonical not in ordered:
                ordered.append(canonical)
        return ordered

    def _parse_task(self, command_text: str):
        text = command_text.lower()
        if any(keyword in text for keyword in self.TELEOP_KEYWORDS):
            return {"type": "teleop", "source": None, "destination": None, "relation": None}
        if any(keyword in text for keyword in self.DANCE_KEYWORDS):
            return {"type": "dance", "source": None, "destination": None, "relation": None}

        objects = self._extract_objects(command_text)
        relation = "place"
        for relation_name, keywords in self.RELATION_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                relation = relation_name
                break

        has_place_verb = any(keyword in text for keyword in self.PLACE_KEYWORDS)
        has_to_connector = " to " in f" {text} "
        is_place = len(objects) >= 2 and (has_place_verb or relation != "place" or has_to_connector)

        if is_place:
            return {
                "type": "pick_place",
                "source": objects[0],
                "destination": objects[1],
                "relation": relation,
            }
        source = objects[0] if objects else command_text
        return {"type": "grasp", "source": source, "destination": None, "relation": None}

    def teleop_once(self):
        return _TeleopViewer(self.env).run()

    def dance_once(self):
        from grasp_process import _move_joint_waypoint

        robot = self.env.robot
        action = np.zeros(7)
        q_start = np.array(robot.get_joint(), dtype=np.float64)
        dance_targets = [
            np.array([0.4, -0.8, 1.6, -1.2, -1.2, 0.0], dtype=np.float64),
            np.array([-0.4, -0.8, 1.6, -1.2, -1.2, 0.0], dtype=np.float64),
            np.array([0.5, -1.1, 1.3, -0.8, -1.5, 0.8], dtype=np.float64),
            np.array([-0.5, -1.1, 1.3, -0.8, -1.5, -0.8], dtype=np.float64),
            q_start,
        ]
        for q_target in dance_targets:
            _move_joint_waypoint(self.env, robot, action, q_target, 0.8)
        return {"status": "ok", "task": "dance"}

    def grasp_once(self, command_text: str):
        from grasp_process import (
            estimate_body_image_bbox,
            estimate_direct_grasp_target_world,
            estimate_place_target_world,
            execute_grasp,
            run_grasp_inference,
        )
        from vlm_process import segment_image

        color_img, depth_img = self._capture_rgbd()
        task = self._parse_task(command_text)
        if task["type"] == "teleop":
            return self.teleop_once()
        if task["type"] == "dance":
            return self.dance_once()

        source_bbox = (
            estimate_body_image_bbox(self.env, task["source"], color_img.shape)
            if isinstance(task["source"], str)
            else None
        )
        source_mask = segment_image(
            color_img,
            output_mask="mask_source.png",
            command_text=task["source"],
            bbox_override=source_bbox,
            label_override=task["source"] if isinstance(task["source"], str) else None,
        )
        gg = run_grasp_inference(
            color_img,
            depth_img,
            source_mask,
            camera_fovy_deg=getattr(self.env, "camera_fovy_deg", 45.0),
        )
        source_target_world = None
        if task["source"] in {"apple", "duck"}:
            source_target_world, _ = estimate_direct_grasp_target_world(
                self.env,
                depth_img,
                source_mask,
                source_name=task["source"],
            )
            print(f"[grasp] direct top-down target for {task['source']}: {source_target_world.tolist()}")

        place_target_world = None
        place_mode = None
        if task["type"] == "pick_place":
            if task["destination"] == "plate" and task["relation"] == "in":
                task["relation"] = "on_top_of"
            if task["destination"] == "plate":
                place_mode = "drop_above_plate"
            destination_bbox = (
                estimate_body_image_bbox(self.env, task["destination"], color_img.shape)
                if isinstance(task["destination"], str)
                else None
            )
            destination_mask = segment_image(
                color_img,
                output_mask="mask_destination.png",
                command_text=task["destination"],
                bbox_override=destination_bbox,
                label_override=task["destination"] if isinstance(task["destination"], str) else None,
            )
            place_target_world = estimate_place_target_world(
                self.env,
                depth_img,
                destination_mask,
                source_mask=source_mask,
                relation=task["relation"],
                source_name=task["source"],
                destination_name=task["destination"],
            )
            print(
                f"[place] source={task['source']} destination={task['destination']} "
                f"relation={task['relation']} target={place_target_world.tolist()}"
            )

        execute_grasp(
            self.env,
            gg,
            place_target_world=place_target_world,
            grasp_target_world=source_target_world,
            source_name=task["source"] if isinstance(task["source"], str) else None,
            place_mode=place_mode,
        )
        from workflow_hooks import get_inventory_store, record_task_success_effects

        inventory_event = record_task_success_effects(
            task=task,
            command=command_text,
            session_id=None,
        )
        return {
            "status": "ok",
            "task": task["type"],
            "source": task["source"],
            "destination": task["destination"],
            "grasp_count": len(gg),
            "inventory_event": inventory_event,
            "inventory": get_inventory_store().snapshot(),
        }
