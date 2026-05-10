#!/usr/bin/env python3
# Copyright (c) 2023-2026, AgiBot Inc. All Rights Reserved.
# Author: Genie Sim Team
# License: Mozilla Public License Version 2.0

import os
import sys
import time
import signal
import subprocess
import threading
import logging
import shutil
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np

from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore
from rosbags.image import compressed_image_to_cvimage

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("auto_record_extractor")

# Constant definitions
NANOSEC_TO_SEC = 1e-9
DEFAULT_JPEG_QUALITY = 85
DEFAULT_TIMEOUT = 10.0
DEFAULT_FPS = 30
DEFAULT_MAX_IO_WORKERS = 4
PROGRESS_LOG_INTERVAL = 500


def map_topic_to_camera_name(topic_name: str) -> str:
    name = topic_name.split("/")[-1]
    if "camera_rgb" == name:
        return "world_img"
    if "Head" in name or "head" in name:
        return "head"
    if "Right" in name or "right" in name:
        return "hand_right"
    if "Left" in name or "left" in name:
        return "hand_left"
    return name


class ImageForwardRecorderNode(Node):
    def __init__(
        self,
        output_dir,
        timeout=DEFAULT_TIMEOUT,
        jpeg_quality=DEFAULT_JPEG_QUALITY,
        final_output_dir: str | None = None,
        delete_db3_after: bool = False,
    ):
        super().__init__("image_forward_recorder")
        self.output_dir = output_dir
        self.timeout = timeout
        self.jpeg_quality = jpeg_quality
        self.final_output_dir = final_output_dir
        self.delete_db3_after = delete_db3_after
        self.max_io_workers = DEFAULT_MAX_IO_WORKERS

​        os.makedirs(self.output_dir, exist_ok=True)
​        self.bridge = CvBridge()
​        self.subscribers = {}
​        self.genie_sim_subscribers = {}
​        self.record_publishers = {}
​        self.last_genie_sim_message_time = time.time()
​        self.message_lock = threading.Lock()
​        self.record_process = None
​        self.is_recording = False
​        self.should_stop = False
​        self.sub_task_name = ""
​        self.sub_task_name_received = False
​        self.sub_task_name_lock = threading.Lock()
​        
​        self.sub_task_name_subscription = self.create_subscription(
​            String, "/record/sub_task_name", self.sub_task_name_callback, 10
​        )
​        self.topic_discovery_timer = self.create_timer(2.0, self.discover_topics)
​        self.timeout_check_timer = self.create_timer(1.0, self.check_timeout)

​    def sub_task_name_callback(self, msg):
​        if self.should_stop: return
​        with self.sub_task_name_lock:
​            if msg and hasattr(msg, "data"):
​                self.sub_task_name = msg.data
​                self.sub_task_name_received = True

​    def discover_topics(self):
​        topic_names_and_types = self.get_topic_names_and_types()
​        for topic_name, topic_types in topic_names_and_types:
​            if topic_name.startswith("/record/") and "sensor_msgs/msg/CompressedImage" in topic_types:
​                if topic_name not in self.subscribers:
​                    self.subscribers[topic_name] = self.create_subscription(
​                        CompressedImage, topic_name, lambda msg, tn=topic_name: self.image_callback(msg, tn), 10
​                    )
​            if topic_name.startswith("/genie_sim/") and "sensor_msgs/msg/Image" in topic_types:
​                if topic_name not in self.genie_sim_subscribers:
​                    suffix = topic_name.split("/genie_sim/")[-1]
​                    rt = f"/record/{suffix}"
​                    self.genie_sim_subscribers[topic_name] = self.create_subscription(
​                        Image, topic_name, lambda msg, tn=topic_name, rt=rt: self.genie_sim_callback(msg, tn, rt), 10
​                    )
​                    if rt not in self.record_publishers:
​                        self.record_publishers[rt] = self.create_publisher(CompressedImage, rt, 10)

​    def genie_sim_callback(self, msg, topic_name, record_topic):
​        with self.message_lock: self.last_genie_sim_message_time = time.time()
​        try:
​            cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
​            _, compressed_data = cv2.imencode(".jpg", cv_img, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
​            c_msg = CompressedImage()
​            c_msg.header, c_msg.format, c_msg.data = msg.header, "jpeg", compressed_data.tobytes()
​            if record_topic in self.record_publishers: self.record_publishers[record_topic].publish(c_msg)
​        except Exception as e: logger.error(f"Error forwarding: {e}")

​    def image_callback(self, msg, topic_name):
​        if not self.is_recording: self.start_recording()

​    def start_recording(self):
​        with self.sub_task_name_lock:
​            if not self.sub_task_name_received or not self.sub_task_name: return
​            sub_task_name = self.sub_task_name
​        
​        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
​        recording_dir = os.path.join(self.output_dir, "recording_data", sub_task_name)
​        os.makedirs(recording_dir, exist_ok=True)
​        bag_path = os.path.join(recording_dir, f"recording_{timestamp}")
​        topics = " ".join(self.subscribers.keys())
​        cmd = f"source /opt/ros/jazzy/setup.bash && ros2 bag record -o {bag_path} {topics}"
​        self.record_process = subprocess.Popen(cmd, shell=True, executable="/bin/bash", preexec_fn=os.setsid)
​        self.is_recording, self.bag_path = True, bag_path
​        logger.info(f"Started recording to {bag_path}")

​    def check_timeout(self):
​        if self.should_stop: return
​        with self.message_lock: elapsed = time.time() - self.last_genie_sim_message_time
​        if elapsed > self.timeout:
​            if self.is_recording: self.stop_recording()
​            self.should_stop = True

​    def stop_recording(self):
​        if not self.is_recording: return
​        os.killpg(os.getpgid(self.record_process.pid), signal.SIGINT)
​        self.record_process.wait(timeout=10)
​        self.is_recording = False
​        time.sleep(2)
​        extract_and_convert_standalone(self.bag_path, self.final_output_dir, self.delete_db3_after)

​    def cleanup(self):
​        self.should_stop = True
​        if self.is_recording: self.stop_recording()
​        try:
​            self.topic_discovery_timer.cancel()
​            self.timeout_check_timer.cancel()
​            self.sub_task_name_subscription.destroy()
​        except: pass


def extract_and_convert_standalone(bag_path, final_output_dir=None, delete_db3=False):
    """Standalone extraction function to avoid memory issues and allow manual trigger."""
    logger.info(f"Starting extraction for bag: {bag_path}")
    bag_path_obj = Path(bag_path)
    images_dir = bag_path_obj / "camera"
    video_dir = bag_path_obj / "video"
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)

​    typestore = get_typestore(Stores.ROS2_JAZZY)
​    
    # --- Pass 1: Collect timestamps for alignment ---
​    logger.info("Pass 1: Collecting timestamps...")
​    camera_timestamps = {} # camera_name -> [(header_ts, raw_ts)]
​    topic_to_cam = {}
​    
​    with AnyReader([bag_path_obj], default_typestore=typestore) as reader:
​        for connection in reader.connections:
​            if connection.msgtype == "sensor_msgs/msg/CompressedImage" and connection.topic.startswith("/record/"):
​                cam_name = map_topic_to_camera_name(connection.topic.replace("/record/", ""))
​                topic_to_cam[connection.topic] = cam_name
​                camera_timestamps[cam_name] = []

​        for connection, timestamp, msg in reader.messages():
​            if connection.topic in topic_to_cam:
​                c_msg = reader.deserialize(msg, "sensor_msgs/msg/CompressedImage")
​                header_ts = c_msg.header.stamp.sec + c_msg.header.stamp.nanosec * NANOSEC_TO_SEC
​                camera_timestamps[topic_to_cam[connection.topic]].append((header_ts, timestamp))

​    if not camera_timestamps:
​        logger.error("No camera data found in bag.")
​        return

    # --- Alignment Logic ---
​    cam_names = list(camera_timestamps.keys())
​    global_start = max(ts[0][0] for ts in camera_timestamps.values())
​    global_end = min(ts[-1][0] for ts in camera_timestamps.values())
​    
​    ref_cam = "world_img" if "world_img" in camera_timestamps else cam_names[0]
​    ref_data = [t for t in camera_timestamps[ref_cam] if global_start <= t[0] <= global_end]
​    
​    logger.info(f"Aligned range: {global_start:.2f} to {global_end:.2f}. Frames: {len(ref_data)}")
​    
    # Map raw_timestamp -> list of (camera_name, frame_idx)
​    needed_raw_ts = {} 
​    for frame_idx, (ref_header_ts, _) in enumerate(ref_data):
​        for cam in cam_names:
            # Find closest frame in this camera
​            closest = min(camera_timestamps[cam], key=lambda x: abs(x[0] - ref_header_ts))
​            needed_raw_ts.setdefault(closest[1], []).append((cam, frame_idx))

    # --- Pass 2: Extract and write images ---
​    logger.info(f"Pass 2: Extracting {len(needed_raw_ts)} unique messages...")
​    topic_images = {cam: [] for cam in cam_names}
​    
​    with AnyReader([bag_path_obj], default_typestore=typestore) as reader:
​        count = 0
​        for connection, timestamp, msg in reader.messages():
​            if timestamp in needed_raw_ts:
​                c_msg = reader.deserialize(msg, "sensor_msgs/msg/CompressedImage")
​                cv_img = compressed_image_to_cvimage(c_msg, "bgr8")
​                
​                for cam_name, frame_idx in needed_raw_ts[timestamp]:
​                    frame_dir = images_dir / str(frame_idx)
​                    os.makedirs(frame_dir, exist_ok=True)
​                    img_path = frame_dir / f"{cam_name}.jpg"
​                    cv2.imwrite(str(img_path), cv_img)
​                    topic_images[cam_name].append(str(img_path))
​                
​                count += 1
​                if count % PROGRESS_LOG_INTERVAL == 0:
​                    logger.info(f"Extracted {count} messages...")

    # --- Video Conversion ---
​    for cam, paths in topic_images.items():
​        if not paths: continue
​        logger.info(f"Converting {cam} to video...")
​        out_video = video_dir / f"{cam}.webm"
        # Create symlinks for ffmpeg
​        tmp_cam_dir = images_dir / cam
​        os.makedirs(tmp_cam_dir, exist_ok=True)
​        sorted_paths = sorted(paths, key=lambda x: int(Path(x).parent.name))
​        for i, p in enumerate(sorted_paths):
​            target = tmp_cam_dir / f"frame_{i:06d}.jpg"
​            if target.exists(): target.unlink()
​            os.link(p, target)
​        
​        subprocess.run([
​            "ffmpeg", "-y", "-framerate", str(DEFAULT_FPS), "-i", str(tmp_cam_dir / "frame_%06d.jpg"),
​            "-c:v", "libvpx-vp9", "-b:v", "2000k", "-crf", "28", "-speed", "4", "-an", "-loglevel", "error", str(out_video)
​        ])
​        logger.info(f"Video saved: {out_video}")

​    if delete_db3:
​        for f in bag_path_obj.glob("*.db3"): f.unlink()
​    
​    if final_output_dir:
​        dst = Path(final_output_dir) / bag_path_obj.name
​        if dst.exists(): shutil.rmtree(dst)
​        shutil.move(str(bag_path_obj), str(dst))
​        logger.info(f"Moved to final destination: {dst}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="auto_recordings")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--jpeg_quality", type=int, default=85)
    parser.add_argument("--final_output_dir", type=str, default=None)
    parser.add_argument("--delete_db3_after", action="store_true")
    parser.add_argument("--bag_path", type=str, help="Manual extraction mode: path to an existing rosbag directory")
    
    args = parser.parse_args()

​    if args.bag_path:
        # Manual extraction mode
​        extract_and_convert_standalone(args.bag_path, args.final_output_dir, args.delete_db3_after)
​        return

    # Normal recording mode
​    rclpy.init()
​    node = ImageForwardRecorderNode(args.output_dir, args.timeout, args.jpeg_quality, args.final_output_dir, args.delete_db3_after)
​    try:
​        while rclpy.ok() and not node.should_stop:
​            rclpy.spin_once(node, timeout_sec=0.1)
​        node.cleanup()
​    except KeyboardInterrupt:
​        node.cleanup()
​    finally:
​        node.destroy_node()
​        rclpy.shutdown()

if __name__ == "__main__":
    main()