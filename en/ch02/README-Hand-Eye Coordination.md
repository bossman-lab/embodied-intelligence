# Hand-Eye Coordination Tutorial

This directory contains technical tutorials related to robot hand-eye coordination, focusing on hand-eye calibration and visual servoing.

## Table of Contents

### Hand-Eye Calibration
- [Hand-Eye Calibration Tutorial](6.1 Hand-Eye Calibration.md) - Detailed introduction to the principles and implementation methods of hand-eye calibration
- [Figure Resources](Figure/) - Image resources related to hand-eye calibration

### Visual Servoing
- Position-based visual servoing (comming soon)
- Image-based visual servoing (comming soon)
- Hybrid visual servoing (comming soon)

## Learning Path
1. First, study the [Hand-Eye Calibration Tutorial](6.1 Hand-Eye Calibration.md) to grasp basic concepts
2. Learn how to calibrate camera intrinsic and extrinsic parameters.
3. Learn the conversion between robot coordinate system and camera coordinate system
4. Understand the principles of visual feedback control.
5. Practice hand-eye coordination tasks, such as vision-guided grasping

## Technical Background
Hand-eye coordination is a crucial technology that integrates robot vision and control, enabling precise operations by defining the spatial relationship between the robot's end effector and the camera.Some common applications include:

- Vision-guided grasping
- Assembly operations
- Visual inspection and quality control
- Automated production lines

## Common Tools and Libraries
- OpenCV - Computer vision library
- ROS/ROS2 - Robot operating system
- MoveIt - Robot motion planning framework
- PCL - Point cloud processing library

## Requirements for the Experimental Environment
- Industrial camera or high-quality USB camera
- Manipulator or robot platform
- Calibration board (such as chessboard)
- Computing platform (supporting real-time image processing)