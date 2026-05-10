#!/usr/bin/env python3
"""生成课程所需的架构图和流程图"""

from graphviz import Digraph
import os

# 输出目录
output_dir = os.path.expanduser("~/ros2_robot_simulation_ws/course/module1_1_robot_history/images/")
os.makedirs(output_dir, exist_ok=True)

# 1. ROS系统架构图
def create_ros_architecture():
    dot = Digraph(comment='ROS Architecture')
    dot.attr(rankdir='TB', splines='ortho')
    
    # 节点
    dot.node('User', '用户应用\n(User Node)', shape='box', style='rounded,filled', fillcolor='lightblue')
    dot.node('Master', 'ROS Master', shape='ellipse', style='filled', fillcolor='gold')
    dot.node('Talker', '发布者\n(Talker)', shape='box', style='rounded,filled', fillcolor='lightgreen')
    dot.node('Listener', '订阅者\n(Listener)', shape='box', style='rounded,filled', fillcolor='lightgreen')
    dot.node('Service', '服务节点\n(Service)', shape='box', style='rounded,filled', fillcolor='lightyellow')
    dot.node('Action', '动作节点\n(Action)', shape='box', style='rounded,filled', fillcolor='lightsalmon')
    
    # 边
    dot.edge('User', 'Master', style='dashed')
    dot.edge('Talker', 'Master', label='注册')
    dot.edge('Listener', 'Master', label='注册')
    dot.edge('Talker', 'Listener', label='话题通信', style='bold', color='blue')
    dot.edge('User', 'Service', label='调用')
    dot.edge('User', 'Action', label='目标')
    
    dot.render(f'{output_dir}ros_architecture', format='jpg', cleanup=True)
    print("ros_architecture.jpg created")

# 2. 具身智能概念图
def create_embodied_ai_concept():
    dot = Digraph(comment='Embodied AI Concept')
    dot.attr(rankdir='LR')
    
    dot.node('AI', '传统AI\n(大语言模型)', shape='box', style='rounded,filled', fillcolor='lightblue')
    dot.node('Body', '物理身体\n(机器人/设备)', shape='box', style='rounded,filled', fillcolor='lightgreen')
    dot.node('Sensor', '传感器\n(视觉/触觉)', shape='ellipse', fillcolor='yellow')
    dot.node('Actuator', '执行器\n(马达/机械臂)', shape='ellipse', fillcolor='orange')
    dot.node('Env', '物理世界\nEnvironment', shape='ellipse', fillcolor='pink')
    dot.node('Learn', '交互学习', shape='diamond', fillcolor='lightyellow')
    
    dot.edge('AI', 'Body', label='控制')
    dot.edge('Body', 'Sensor', label='感知')
    dot.edge('Sensor', 'AI', label='反馈')
    dot.edge('AI', 'Actuator', label='命令')
    dot.edge('Actuator', 'Env', label='作用')
    dot.edge('Env', 'Body', label='影响')
    dot.edge('Env', 'Learn', label='交互')
    dot.edge('Learn', 'AI', label='学习')
    
    dot.render(f'{output_dir}embodied_ai_concept', format='jpg', cleanup=True)
    print("embodied_ai_concept.jpg created")

# 3. LLM机器人架构图
def create_llm_robot():
    dot = Digraph(comment='LLM Robot Architecture')
    dot.attr(rankdir='TB')
    
    dot.node('User', '用户指令\n"把芯片放到盒子里"', shape='box', fillcolor='lightblue')
    dot.node('LLM', '大语言模型\n(PaLM-E)', shape='box', fillcolor='gold')
    dot.node('Plan', '任务规划\n(Task Planning)', shape='box', fillcolor='lightgreen')
    dot.node('Vision', '视觉感知\n(Vision)', shape='ellipse', fillcolor='yellow')
    dot.node('Control', '动作控制\n(Motion Control)', shape='ellipse', fillcolor='orange')
    dot.node('Robot', '机器人', shape='box', fillcolor='pink', style='rounded')
    
    dot.edge('User', 'LLM')
    dot.edge('LLM', 'Plan')
    dot.edge('Vision', 'LLM', style='dashed')
    dot.edge('Plan', 'Control')
    dot.edge('Control', 'Robot')
    dot.edge('Vision', 'Robot', style='dashed')
    
    dot.render(f'{output_dir}llm_robot', format='jpg', cleanup=True)
    print("llm_robot.jpg created")

# 4. VLM机器人架构图
def create_vlm_robot():
    dot = Digraph(comment='VLM Robot Architecture')
    dot.attr(rankdir='TB')
    
    dot.node('Image', '摄像头图像', shape='ellipse', fillcolor='lightblue')
    dot.node('Text', '文本指令', shape='ellipse', fillcolor='lightblue')
    dot.node('VLM', '视觉语言模型\n(RT-2/OK-Robot)', shape='box', fillcolor='gold')
    dot.node('Grasp', '抓取规划', shape='box', fillcolor='lightgreen')
    dot.node('Robot', '机械臂', shape='box', fillcolor='pink', style='rounded')
    
    dot.edge('Image', 'VLM')
    dot.edge('Text', 'VLM')
    dot.edge('VLM', 'Grasp')
    dot.edge('Grasp', 'Robot')
    
    dot.render(f'{output_dir}vlm_robot', format='jpg', cleanup=True)
    print("vlm_robot.jpg created")

# 5. VLA模型架构图
def create_vla_architecture():
    dot = Digraph(comment='VLA Architecture')
    dot.attr(rankdir='TB')
    
    dot.node('Input', '视觉输入\n+ 语言指令', shape='box', fillcolor='lightblue')
    dot.node('Encoder', '视觉/语言\n编码器', shape='box', fillcolor='lightgreen')
    dot.node('Transformer', 'Transformer\n骨干网络', shape='ellipse', fillcolor='gold')
    dot.node('ActionHead', '动作输出\n头', shape='box', fillcolor='orange')
    dot.node('Output', '机器人动作\n(位置/旋转/抓取)', shape='box', fillcolor='pink')
    
    dot.edge('Input', 'Encoder')
    dot.edge('Encoder', 'Transformer')
    dot.edge('Transformer', 'ActionHead')
    dot.edge('ActionHead', 'Output')
    
    dot.render(f'{output_dir}vla_architecture', format='jpg', cleanup=True)
    print("vla_architecture.jpg created")

# 6. 强化学习流程图
def create_rl_flow():
    dot = Digraph(comment='Reinforcement Learning')
    dot.attr(rankdir='LR')
    
    dot.node('Start', '智能体\n(Agent)', shape='box', fillcolor='lightblue')
    dot.node('Env', '环境\n(Environment)', shape='ellipse', fillcolor='lightgreen')
    dot.node('State', '状态 s', shape='point')
    dot.node('Action', '动作 a', shape='point')
    dot.node('Reward', '奖励 r', shape='diamond', fillcolor='yellow')
    dot.node('Policy', '策略更新\n(Policy Update)', shape='box', fillcolor='orange')
    
    dot.edge('Start', 'State', label='观察')
    dot.edge('State', 'Action', label='选择动作')
    dot.edge('Action', 'Env', label='执行')
    dot.edge('Env', 'Reward', label='获得反馈')
    dot.edge('Reward', 'Policy', label='学习')
    dot.edge('Policy', 'Start', label='更新策略')
    dot.edge('Env', 'State', label='新状态')
    
    dot.render(f'{output_dir}rl_flow', format='jpg', cleanup=True)
    print("rl_flow.jpg created")

# 7. 模仿学习示意图
def create_imitation_learning():
    dot = Digraph(comment='Imitation Learning')
    dot.attr(rankdir='TB')
    
    dot.node('Human', '人类演示者', shape='box', fillcolor='lightblue')
    dot.node('Demo', '演示数据\n(轨迹/动作)', shape='box', fillcolor='lightgreen')
    dot.node('BC', '行为克隆\n(Behavior Clone)', shape='ellipse', fillcolor='gold')
    dot.node('Policy', '策略网络\n(Policy)', shape='box', fillcolor='orange')
    dot.node('Robot', '机器人', shape='box', fillcolor='pink', style='rounded')
    dot.node('Loss', '损失函数', shape='diamond', fillcolor='yellow')
    
    dot.edge('Human', 'Demo', label='演示')
    dot.edge('Demo', 'BC')
    dot.edge('BC', 'Policy')
    dot.edge('Policy', 'Robot', label='执行')
    dot.edge('Robot', 'Loss', label='评估')
    dot.edge('Loss', 'BC', label='反向传播')
    
    dot.render(f'{output_dir}imitation_learning', format='jpg', cleanup=True)
    print("imitation_learning.jpg created")

# 8. 空间智能3D感知图
def create_spatial_intelligence():
    dot = Digraph(comment='Spatial Intelligence')
    dot.attr(rankdir='TB')
    
    dot.node('Camera', '深度相机', shape='ellipse', fillcolor='lightblue')
    dot.node('Lidar', '激光雷达', shape='ellipse', fillcolor='lightblue')
    dot.node('PointCloud', '点云数据\n(Point Cloud)', shape='box', fillcolor='lightgreen')
    dot.node('PointNet', 'PointNet\n3D深度学习', shape='ellipse', fillcolor='gold')
    dot.node('3D理解', '3D目标检测\n/分割/位姿估计', shape='box', fillcolor='orange')
    dot.node('Robot', '机器人导航\n/抓取', shape='box', fillcolor='pink', style='rounded')
    
    dot.edge('Camera', 'PointCloud')
    dot.edge('Lidar', 'PointCloud')
    dot.edge('PointCloud', 'PointNet')
    dot.edge('PointNet', '3D理解')
    dot.edge('3D理解', 'Robot')
    
    dot.render(f'{output_dir}spatial_intelligence', format='jpg', cleanup=True)
    print("spatial_intelligence.jpg created")

if __name__ == '__main__':
    print("Generating diagrams...")
    create_ros_architecture()
    create_embodied_ai_concept()
    create_llm_robot()
    create_vlm_robot()
    create_vla_architecture()
    create_rl_flow()
    create_imitation_learning()
    create_spatial_intelligence()
    print("All diagrams generated!")
