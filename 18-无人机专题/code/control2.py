import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ========== 四旋翼电机模型：推力/力矩计算与可视化 ==========

# --- 电机参数 ---
kF = 6.11e-8   # 推力系数 (N/(rad/s)^2)
kM = 1.5e-9    # 力矩系数 (N·m/(rad/s)^2)
L  = 0.175     # 臂长 (m)

# --- 四个电机转速 (rad/s)，模拟非对称飞行 ---
omega = np.array([4000, 4200, 3800, 4100])  # ω1, ω2, ω3, ω4

# --- 计算各电机推力和反扭矩 ---
F = kF * omega**2     # 各电机推力
M = kM * omega**2     # 各电机反扭矩

# --- 计算总推力和控制力矩 ---
u1 = np.sum(F)                       # 总推力
u2 = L * (F[1] - F[3])              # 滚转力矩
u3 = L * (F[2] - F[0])              # 俯仰力矩
u4 = M[0] - M[1] + M[2] - M[3]     # 偏航力矩

print(f"各电机推力: F = {F} N")
print(f"总推力 u1 = {u1:.4f} N")
print(f"滚转力矩 u2 = {u2:.6f} N·m")
print(f"俯仰力矩 u3 = {u3:.6f} N·m")
print(f"偏航力矩 u4 = {u4:.8f} N·m")

# --- 可视化：俯视图（电机位置 + 推力）和 3D 推力箭头 ---
fig = plt.figure(figsize=(14, 5))

# 子图 1：俯视图，四个电机位置和推力大小
ax1 = fig.add_subplot(1, 2, 1)
motor_pos = np.array([[0, L], [-L, 0], [0, -L], [L, 0]])  # 电机 1前 2左 3后 4右
colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
for i in range(4):
    circle = plt.Circle(motor_pos[i], 0.04, color=colors[i], zorder=5)
    ax1.add_patch(circle)
    ax1.annotate(f'M{i+1}\nω={omega[i]}\nF={F[i]:.3f}N',
                 motor_pos[i], textcoords="offset points",
                 xytext=(15, 10), fontsize=8, color=colors[i])
# 画机体十字
ax1.plot([motor_pos[1,0], motor_pos[3,0]],
         [motor_pos[1,1], motor_pos[3,1]], 'k-', lw=2)
ax1.plot([motor_pos[0,0], motor_pos[2,0]],
         [motor_pos[0,1], motor_pos[2,1]], 'k-', lw=2)
ax1.set_xlim(-0.35, 0.35); ax1.set_ylim(-0.35, 0.35)
ax1.set_aspect('equal'); ax1.grid(True, alpha=0.3)
ax1.set_title('俯视图：电机分布与推力'); ax1.set_xlabel('Y (m)'); ax1.set_ylabel('X (m)')

# 子图 2：3D 视图，显示推力箭头
ax2 = fig.add_subplot(1, 2, 2, projection='3d')
for i in range(4):
    x, y = motor_pos[i]
    # 各电机推力箭头（沿 Z 轴向上）
    scale = F[i] / np.max(F) * 0.3  # 归一化显示
    ax2.quiver(x, y, 0, 0, 0, scale, color=colors[i],
               arrow_length_ratio=0.2, lw=2, label=f'M{i+1}: {F[i]:.3f}N')
    ax2.scatter(x, y, 0, color=colors[i], s=60)
# 总推力箭头（从中心出发）
ax2.quiver(0, 0, 0, 0, 0, 0.4, color='k', arrow_length_ratio=0.15,
           lw=3, label=f'总推力 u1={u1:.3f}N')
ax2.set_xlabel('Y'); ax2.set_ylabel('X'); ax2.set_zlabel('Z（推力方向）')
ax2.set_title('3D 视图：推力矢量'); ax2.legend(fontsize=7, loc='upper left')

plt.suptitle('四旋翼电机模型可视化', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control2.png', dpi=150, bbox_inches='tight')
plt.show()