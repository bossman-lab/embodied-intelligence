

Read file: /home/kewei/17robo/ManiSkill/mani_skill/agents/controllers/__init__.py

Read file: /home/kewei/17robo/ManiSkill/mani_skill/agents/controllers/pd_joint_pos.py
Panda机器人夹爪的控制方式如下：

1. **夹爪关节名称**：
   
   ```python
   gripper_joint_names = [
       "panda_finger_joint1",
       "panda_finger_joint2",
   ]
   ```
   
   Panda机器人有两个夹爪关节，分别是`panda_finger_joint1`和`panda_finger_joint2`。

2. **控制器配置**：
   
   ```python
   gripper_pd_joint_pos = PDJointPosMimicControllerConfig(
       self.gripper_joint_names,
       lower=-0.01,  # 一个技巧，当物体很薄时可以施加力
       upper=0.04,   # 完全打开的位置
       stiffness=self.gripper_stiffness,
       damping=self.gripper_damping,
       force_limit=self.gripper_force_limit,
   )
   ```

3. **控制方式**：
   
   - Panda使用`PDJointPosMimicController`，这是一个模拟(Mimic)控制器
   - 这意味着两个手指关节同步移动，输入一个值就能同时控制两个关节
   - 控制范围是从-0.01（稍微闭合）到0.04（完全打开）
   - 在初始姿态中，夹爪位置设为0.04（完全打开）：
     
     ```python
     keyframes = dict(
         rest=Keyframe(
             qpos=np.array([
                 0.0, np.pi/8, 0, -np.pi*5/8, 0, np.pi*3/4, np.pi/4,
                 0.04, 0.04,  # 夹爪两个关节，都设为完全打开
             ]),
             pose=sapien.Pose(),
         )
     )
     ```

4. **检测物体抓取**：
   Panda机器人通过`is_grasping`方法检测是否成功抓取物体，方法基于接触力和角度判断。

与GEN72-EG2机器人相比较：

- Panda只有2个夹爪关节，而GEN72-EG2有4个夹爪关节
- 两者都使用相同的`PDJointPosMimicController`控制器，这使得夹爪关节可以同步移动
- 控制范围相似：Panda是-0.01到0.04，而GEN72-EG2是0.0到0.04
- 使用时只需要输入一个值，就能同时控制所有夹爪关节

总结：在训练过程中，两种机器人的夹爪都可以通过输入单个范围在0.0-0.04之间的值来控制开合，0.0表示完全闭合，0.04表示完全打开。
