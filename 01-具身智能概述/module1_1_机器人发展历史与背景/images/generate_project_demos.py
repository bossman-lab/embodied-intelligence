#!/usr/bin/env python3
"""生成具身智能项目demo示意图"""

from graphviz import Digraph
import os

output_dir = os.path.expanduser("~/ros2_robot_simulation_ws/course/module1_1_robot_history/images/")
os.makedirs(output_dir, exist_ok=True)

# 1. 机器人技术发展趋势 - 四大趋势
def create_robot_trends():
    dot = Digraph(comment='Robot Technology Trends')
    dot.attr(rankdir='TB', dpi='300', size='12,10')
    
    # 中心
    dot.node('center', '机器人技术\n发展趋势', shape='doublecircle', 
             fillcolor='lightblue', style='filled', fontsize='24')
    
    # 四大趋势
    with dot.subgraph(name='cluster1') as s:
        s.attr(label='智能化', style='filled', fillcolor='lightyellow')
        s.node('AI', 'AI赋能\n(大模型/深度学习)', shape='box', style='rounded,filled', fillcolor='gold')
        s.node('Auto', '自主决策', shape='ellipse', fillcolor='lightgreen')
    
    with dot.subgraph(name='cluster2') as s:
        s.attr(label='协作化', style='filled', fillcolor='lightcyan')
        s.node('Cobot', '协作机器人\n(Cobot)', shape='box', style='rounded,filled', fillcolor='lightblue')
        s.node('Human', '人机协同', shape='ellipse', fillcolor='lightgreen')
    
    with dot.subgraph(name='cluster3') as s:
        s.attr(label='平台化', style='filled', fillcolor='lightpink')
        s.node('ROS', 'ROS/ROS2\n开源框架', shape='box', style='rounded,filled', fillcolor='orange')
        s.node('Module', '模块化设计', shape='ellipse', fillcolor='lightgreen')
    
    with dot.subgraph(name='cluster4') as s:
        s.attr(label='自主化', style='filled', fillcolor='lightgray')
        s.node('SLAM', 'SLAM\n自主导航', shape='box', style='rounded,filled', fillcolor='purple', fontcolor='white')
        s.node('L4', 'L4自动驾驶', shape='ellipse', fillcolor='lightgreen')
    
    dot.edge('center', 'AI')
    dot.edge('center', 'Cobot')
    dot.edge('center', 'ROS')
    dot.edge('center', 'SLAM')
    
    dot.render(f'{output_dir}robot_trends', format='jpg', cleanup=True)
    print("robot_trends.jpg created")

# 2. PaLM-E 项目示意图
def create_palm_e_demo():
    dot = Digraph(comment='PaLM-E Demo')
    dot.attr(rankdir='LR', dpi='300')
    
    # 用户
    dot.node('User', '用户指令:\n"把抽屉里的芯片\n放到盒子里"', 
             shape='box', fillcolor='lightblue', style='rounded', fontsize='14')
    
    # PaLM-E
    dot.node('PaLM', 'PaLM-E\n(Embodied LM)', shape='box', fillcolor='gold', fontsize='18')
    dot.attr(label='大语言模型理解+视觉感知', fontcolor='gray')
    
    # 输出
    dot.node('Task', '任务分解:\n1. 打开抽屉\n2. 找到芯片\n3. 抓取芯片\n4. 放入盒子', 
             shape='box', fillcolor='lightgreen', style='rounded')
    
    # 机器人执行
    dot.node('Robot', '机器人执行', shape='ellipse', fillcolor='orange', fontsize='14')
    
    dot.edge('User', 'PaLM')
    dot.edge('PaLM', 'Task')
    dot.edge('Task', 'Robot')
    
    dot.render(f'{output_dir}palm_e_demo', format='jpg', cleanup=True)
    print("palm_e_demo.jpg created")

# 3. RT-2 项目示意图
def create_rt2_demo():
    dot = Digraph(comment='RT-2 Demo')
    dot.attr(rankdir='LR', dpi='300')
    
    # 输入
    dot.node('Vision', '摄像头\n视觉输入', shape='ellipse', fillcolor='lightblue')
    dot.node('Cmd', '指令:\n"把零食放到\n最近的人手里"', shape='box', fillcolor='lightyellow')
    
    # RT-2
    dot.node('RT2', 'RT-2\n(Vision-Language-Action)', shape='box', fillcolor='gold', fontsize='16')
    
    # 输出
    dot.node('Action', '动作输出:\n移动手臂→抓取→放置', shape='box', fillcolor='lightgreen')
    
    # 理解推理
    dot.node('Reason', '语义推理:\n理解"人"的概念\n理解空间关系', 
             shape='note', fillcolor='lightpink', fontsize='12')
    
    dot.edge('Vision', 'RT2')
    dot.edge('Cmd', 'RT2')
    dot.edge('RT2', 'Action')
    dot.edge('RT2', 'Reason', style='dashed')
    
    dot.render(f'{output_dir}rt2_demo', format='jpg', cleanup=True)
    print("rt2_demo.jpg created")

# 4. NVIDIA GR00T 示意图
def create_gr00t_demo():
    dot = Digraph(comment='GR00T Demo')
    dot.attr(rankdir='TB', dpi='300')
    
    dot.node('Title', 'NVIDIA GR00T\nGeneralist Robot 00', shape='none', fontsize='20', fontcolor='green')
    
    with dot.subgraph(name='c1') as s:
        s.attr(label='输入', style='filled', fillcolor='lightblue')
        s.node('Video', '互联网视频数据', shape='box')
        s.node('Robot', '机器人本体数据', shape='box')
        s.node('Sim', '仿真数据', shape='box')
    
    with dot.subgraph(name='c2') as s:
        s.attr(label='GR00T Foundation Model', style='filled', fillcolor='gold')
        s.node('Model', '通用机器人模型', shape='ellipse', fillcolor='orange', fontsize='14')
    
    with dot.subgraph(name='c3') as s:
        s.attr(label='输出', style='filled', fillcolor='lightgreen')
        s.node('Move', '运动控制', shape='box')
        s.node('Grasp', '精准抓取', shape='box')
        s.node('Nav', '自主导航', shape='box')
    
    dot.edge('Video', 'Model')
    dot.edge('Robot', 'Model')
    dot.edge('Sim', 'Model')
    dot.edge('Model', 'Move')
    dot.edge('Model', 'Grasp')
    dot.edge('Model', 'Nav')
    
    dot.render(f'{output_dir}gr00t_demo', format='jpg', cleanup=True)
    print("gr00t_demo.jpg created")

# 5. 斯坦福ALOHA示意图
def create_aloha_demo():
    dot = Digraph(comment='ALOHA Demo')
    dot.attr(rankdir='LR', dpi='300')
    
    # 数据收集
    dot.node('Data', '数据收集阶段', shape='none', fontsize='16', fontcolor='blue')
    dot.node('Human', '人类佩戴\n动作捕捉设备', shape='box', fillcolor='lightblue')
    dot.node('Teleop', '遥操作\n(Teleoperation)', shape='ellipse', fillcolor='yellow')
    dot.node('Dataset', '演示数据集\n(轨迹/触觉)', shape='box', fillcolor='lightgreen')
    
    # 训练
    dot.node('Train', '训练阶段', shape='none', fontsize='16', fontcolor='blue')
    dot.node('BC', '行为克隆\n(Behavior Clone)', shape='ellipse', fillcolor='gold')
    dot.node('Policy', '机器人策略', shape='box', fillcolor='orange')
    
    # 执行
    dot.node('Execute', '执行阶段', shape='none', fontsize='16', fontcolor='blue')
    dot.node('Robot', '机器人\n自主执行', shape='box', fillcolor='lightpink', style='rounded')
    
    dot.edge('Human', 'Teleop', label='演示')
    dot.edge('Teleop', 'Dataset', label='记录')
    dot.edge('Dataset', 'BC', label='训练')
    dot.edge('BC', 'Policy', label='学习')
    dot.edge('Policy', 'Robot', label='执行')
    
    dot.render(f'{output_dir}aloha_demo', format='jpg', cleanup=True)
    print("aloha_demo.jpg created")

# 6. 具身智能全景图
def create_embodied_overview():
    dot = Digraph(comment='Embodied AI Overview')
    dot.attr(rankdir='TB', dpi='300', size='14,12')
    
    dot.node('Title', '具身智能技术全景图', shape='none', fontsize='22', fontcolor='blue')
    
    # 底层技术
    with dot.subgraph(name='tech') as s:
        s.attr(label='核心技术', style='filled', fillcolor='lightyellow')
        s.node('LLM', 'LLM\n大语言模型', shape='box', fillcolor='gold')
        s.node('VLM', 'VLM\n视觉语言模型', shape='box', fillcolor='gold')
        s.node('VLA', 'VLA\n视觉语言动作', shape='box', fillcolor='gold')
        s.node('RL', 'RL\n强化学习', shape='box', fillcolor='lightgreen')
        s.node('IL', 'IL\n模仿学习', shape='box', fillcolor='lightgreen')
    
    # 代表项目
    with dot.subgraph(name='projects') as s:
        s.attr(label='代表项目', style='filled', fillcolor='lightcyan')
        s.node('PaLM_E', 'PaLM-E\n(Google)', shape='box', fillcolor='lightblue')
        s.node('RT2', 'RT-2\n(DeepMind)', shape='box', fillcolor='lightblue')
        s.node('GR00T', 'GR00T\n(NVIDIA)', shape='box', fillcolor='lightblue')
        s.node('ALOHA', 'ALOHA\n(Stanford)', shape='box', fillcolor='lightblue')
        s.node('Figure', 'Figure 01\n(Figure AI)', shape='box', fillcolor='lightblue')
    
    # 应用
    with dot.subgraph(name='apps') as s:
        s.attr(label='应用场景', style='filled', fillcolor='lightpink')
        s.node('Home', '家用服务', shape='ellipse')
        s.node('Factory', '工业制造', shape='ellipse')
        s.node('Medical', '医疗手术', shape='ellipse')
        s.node('Auto', '自动驾驶', shape='ellipse')
    
    dot.edge('LLM', 'PaLM_E')
    dot.edge('VLM', 'RT2')
    dot.edge('VLA', 'RT2')
    dot.edge('VLA', 'GR00T')
    dot.edge('IL', 'ALOHA')
    dot.edge('RL', 'GR00T')
    dot.edge('PaLM_E', 'Figure')
    dot.edge('RT2', 'Home')
    dot.edge('GR00T', 'Factory')
    dot.edge('ALOHA', 'Home')
    
    dot.render(f'{output_dir}embodied_overview', format='jpg', cleanup=True)
    print("embodied_overview.jpg created")

if __name__ == '__main__':
    print("Generating project demo diagrams...")
    create_robot_trends()
    create_palm_e_demo()
    create_rt2_demo()
    create_gr00t_demo()
    create_aloha_demo()
    create_embodied_overview()
    print("All project demos generated!")
