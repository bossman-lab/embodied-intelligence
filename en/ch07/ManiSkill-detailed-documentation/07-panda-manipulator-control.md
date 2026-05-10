Read file: /home/kewei/17robo/ManiSkill/mani_skill/agents/controllers/__init__.py

Read file: /home/kewei/17robo/ManiSkill/mani_skill/agents/controllers/pd_joint_pos.py
The control method for the Panda robot gripper is as follows:

1. **Gripper Joint Names**:
   
   ```python
   gripper_joint_names = [
       "panda_finger_joint1",
       "panda_finger_joint2",
   ]
   ```
   
   The Panda robot has two gripper joints, namely `panda_finger_joint1` and `panda_finger_joint2`.

2. **Controller Configuration**:
   
   ```python
   gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
       self.gripper_joint_names,
       lower=-0.01,  # A trick to apply force when objects are thin
       upper=0.04,   # Fully open position
       stiffness=self.gripper_stiffness,
       damping=self.gripper_damping,
       force_limit=self.gripper_force_limit,
   )
   ```

3. **Control Method**:
   
   - Panda uses `PDJointPosMimicController`, which is a mimic controller
   - This means the two finger joints move synchronously, and inputting a single value can control both joints simultaneously
   - The control range is from -0.01 (slightly closed) to 0.04 (fully open)
   - In the initial pose, the gripper position is set to 0.04 (fully open):
     
     ```python
     keyframes = dict(
         rest=Keyframe(
             qpos=np.array([
                 0.0, np.pi/8, 0, -np.pi*5/8, 0, np.pi*3/4, np.pi/4,
                 0.04, 0.04,  # Both gripper joints set to fully open
             ]),
             pose=sapien.Pose(),
         )
     )
     ```

4. **Detecting Object Grasping**:
   The Panda robot detects successful grasping of objects through the `is_grasping` method, which is based on contact force and angle judgment.

Comparison with your GEN72-EG2 robot:

- Panda has only 2 gripper joints, while GEN72-EG2 has 4 gripper joints
- Both use the same `PDJointPosMimicController` controller, which allows the gripper joints to move synchronously
- The control range is similar: Panda is -0.01 to 0.04, while GEN72-EG2 is 0.0 to 0.04
- In use, only a single value needs to be input to simultaneously control all gripper joints

Summary: During training, both robots' grippers can be controlled for opening and closing by inputting a single value in the range of 0.0-0.04, where 0.0 means fully closed and 0.04 means fully open.