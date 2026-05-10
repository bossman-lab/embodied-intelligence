import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ============================================================
# Corridor 约束可视化 + 时间分配对比
# 展示航点、安全走廊、障碍物以及两种时间分配策略的速度差异
# ============================================================

np.random.seed(42)

# --- 航点与障碍物定义 ---
waypoints = np.array([[0, 0], [3, 2], [6, 4], [9, 3], [12, 5]])
obstacles = [
    {"center": [1.5, 3.8], "w": 1.2, "h": 1.0},  # 障碍物1：走廊上方
    {"center": [4.5, 1.2], "w": 1.0, "h": 1.2},  # 障碍物2：走廊下方
    {"center": [7.5, 5.8], "w": 1.4, "h": 0.8},  # 障碍物3：走廊上方
    {"center": [10.5, 1.5], "w": 1.0, "h": 1.0}, # 障碍物4：走廊下方
]
corridor_half = 1.2  # 走廊半宽

# --- 生成一条穿过走廊的光滑曲线（用样条插值模拟） ---
from numpy.polynomial import polynomial as P_mod
t_wp = np.linspace(0, 1, len(waypoints))
t_dense = np.linspace(0, 1, 300)
# 简单参数化插值
degree = min(4, len(waypoints) - 1)
cx = np.polyfit(t_wp, waypoints[:, 0], degree)
cy = np.polyfit(t_wp, waypoints[:, 1], degree)
traj_x = np.polyval(cx, t_dense)
traj_y = np.polyval(cy, t_dense)

# ==================== 图1：Corridor 可视化 ====================
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
ax1 = axes[0]

# 绘制走廊矩形
for wp in waypoints:
    rect = Rectangle(
        (wp[0] - corridor_half, wp[1] - corridor_half),
        2 * corridor_half, 2 * corridor_half,
        linewidth=1.5, edgecolor='#2ca02c', facecolor='#2ca02c',
        alpha=0.15, linestyle='--', label='安全走廊' if wp is waypoints[0] else ''
    )
    ax1.add_patch(rect)

# 绘制障碍物
for i, obs in enumerate(obstacles):
    rect = Rectangle(
        (obs["center"][0] - obs["w"]/2, obs["center"][1] - obs["h"]/2),
        obs["w"], obs["h"],
        linewidth=1.5, edgecolor='red', facecolor='red', alpha=0.35,
        label='障碍物' if i == 0 else ''
    )
    ax1.add_patch(rect)

# 绘制轨迹和航点
ax1.plot(traj_x, traj_y, 'b-', linewidth=2, label='规划轨迹')
ax1.plot(waypoints[:, 0], waypoints[:, 1], 'ko', markersize=8, zorder=5, label='航点')
for i, wp in enumerate(waypoints):
    ax1.annotate(f'P{i}', wp, textcoords="offset points", xytext=(6, 8), fontsize=10)

ax1.set_xlabel('X (m)'); ax1.set_ylabel('Y (m)')
ax1.set_title('Corridor 约束示意 —— 轨迹在走廊内避开障碍物')
ax1.legend(loc='upper left', fontsize=9); ax1.grid(True, alpha=0.3)
ax1.set_aspect('equal'); ax1.set_xlim(-2, 14); ax1.set_ylim(-2, 9)

# ==================== 图2：两种时间分配的速度对比 ====================
ax2 = axes[1]
seg_lengths = np.linalg.norm(np.diff(waypoints, axis=0), axis=1)
T_total = 10.0  # 总飞行时间

# 方法一：匀速分配（各段时间相等）
T_uniform = np.full(len(seg_lengths), T_total / len(seg_lengths))
# 方法二：按距离等比例分配
T_prop = T_total * seg_lengths / seg_lengths.sum()

# 计算各段平均速度
v_uniform = seg_lengths / T_uniform
v_prop = seg_lengths / T_prop

# 绘制速度阶梯图
seg_labels = [f'段{i+1}\n({seg_lengths[i]:.1f}m)' for i in range(len(seg_lengths))]
x_pos = np.arange(len(seg_lengths))
width = 0.35
bars1 = ax2.bar(x_pos - width/2, v_uniform, width, color='#ff7f0e', alpha=0.8, label='匀速时间分配')
bars2 = ax2.bar(x_pos + width/2, v_prop, width, color='#1f77b4', alpha=0.8, label='按距离比例分配')

# 标注数值
for bar, v in zip(bars1, v_uniform):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f'{v:.2f}', ha='center', fontsize=8)
for bar, v in zip(bars2, v_prop):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f'{v:.2f}', ha='center', fontsize=8)

ax2.set_xticks(x_pos); ax2.set_xticklabels(seg_labels, fontsize=9)
ax2.set_ylabel('平均速度 (m/s)'); ax2.set_title('两种时间分配策略的速度对比')
ax2.legend(fontsize=9); ax2.grid(True, alpha=0.3, axis='y')

# 在图上添加时间信息
info_uniform = '  '.join([f'{t:.1f}s' for t in T_uniform])
info_prop = '  '.join([f'{t:.1f}s' for t in T_prop])
ax2.text(0.02, 0.95, f'匀速分配时间: [{info_uniform}]', transform=ax2.transAxes,
         fontsize=8, verticalalignment='top', color='#ff7f0e')
ax2.text(0.02, 0.88, f'比例分配时间: [{info_prop}]', transform=ax2.transAxes,
         fontsize=8, verticalalignment='top', color='#1f77b4')

plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/planning3.png', dpi=150, bbox_inches='tight')
plt.show()