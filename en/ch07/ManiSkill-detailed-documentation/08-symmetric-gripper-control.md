In reinforcement learning training, the symmetrical opening and closing of the Franka Panda gripper is ensured by the `PDJointPosMimicController` (mimic controller). The working principle of this special controller is as follows:

1. **Single Control Parameter**:
   Although Panda has two gripper joints (`panda_finger_joint1` and `panda_finger_joint2`), the mimic controller allows both joints to share the same control signal, requiring only one value to control the entire gripper's opening and closing.

2. **Code Implementation**:
   
   ```python
   class PDJointPosMimicController(PDJointPosController):
       def _get_joint_limits(self):
           joint_limits = super()._get_joint_limits()
           diff = joint_limits[0:-1] - joint_limits[1:]
           assert np.allclose(diff, 0), "Mimic joints should have the same limit"
           return joint_limits[0:1]
   ```
   
   This code shows that the mimic controller only needs to know the limits of the first joint, and then the same control signal is applied to all joints.

3. **Controller Configuration**:
   
   ```python
   gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
       self.gripper_joint_names,  # Contains two gripper joints
       lower=-0.01,  # Minimum position (slightly closed)
       upper=0.04,   # Maximum position (fully open)
       ...
   )
   ```

4. **Action Space Simplification**:
   
   - Although physically controlling two joints, only one dimension is needed in the action space
   - For example, when inputting 0.04, both joints move to the 0.04 position (fully open)
   - When inputting 0.0, both joints move to the 0.0 position (fully closed)

Advantages of this design:

- **Simplified Learning**: Reinforcement learning algorithms only need to learn to control one parameter, rather than controlling two fingers separately
- **Ensured Symmetry**: Regardless of the input value, the gripper always opens and closes symmetrically
- **Physical Realism**: The real Franka Panda gripper is physically designed to move synchronously and symmetrically

In your GEN72-EG2 robot, the same control method is used, and although it has 4 gripper joints, through the `PDJointPosMimicController`, they can also maintain synchronous symmetrical movement.