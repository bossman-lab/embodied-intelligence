import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题

# ========== 可视化无人机"+"十字形绕 Z/Y/X 轴旋转 ==========

# --- 构造无人机"+"形状（4 个臂端 + 中心） ---
L = 1.0  # 臂长
drone = np.array([
    [ L, 0, 0],  # 右臂端
    [-L, 0, 0],  # 左臂端
    [ 0, L, 0],  # 前臂端
    [ 0,-L, 0],  # 后臂端
    [ 0, 0, 0],  # 中心
]).T  # 3×5 矩阵，每列一个点

# --- 三维旋转矩阵 ---
def Rz(psi):
    """绕 Z 轴旋转（偏航角 ψ）"""
    c, s = np.cos(psi), np.sin(psi)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def Ry(theta):
    """绕 Y 轴旋转（俯仰角 θ）"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def Rx(phi):
    """绕 X 轴旋转（滚转角 φ）"""
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

angle = np.radians(45)  # 旋转 45°

# --- 绘制 4 个子图：原始 + 3 种旋转 ---
titles = ['原始姿态', f'绕 Z 轴旋转 {int(np.degrees(angle))}°（偏航）',
          f'绕 Y 轴旋转 {int(np.degrees(angle))}°（俯仰）',
          f'绕 X 轴旋转 {int(np.degrees(angle))}°（滚转）']
rotations = [np.eye(3), Rz(angle), Ry(angle), Rx(angle)]

fig = plt.figure(figsize=(14, 10))
for i, (R, title) in enumerate(zip(rotations, titles)):
    ax = fig.add_subplot(2, 2, i + 1, projection='3d')
    pts = R @ drone  # 旋转后的点坐标

    # 画两条臂（十字形）
    ax.plot([pts[0,0], pts[0,1]], [pts[1,0], pts[1,1]],
            [pts[2,0], pts[2,1]], 'b-o', lw=3, label='臂 1')
    ax.plot([pts[0,2], pts[0,3]], [pts[1,2], pts[1,3]],
            [pts[2,2], pts[2,3]], 'r-o', lw=3, label='臂 2')
    # 标注中心
    ax.scatter(*pts[:, 4], color='k', s=80, zorder=5)

    # 画旋转后的机体坐标轴
    axis_len = 0.6
    for j, (color, lbl) in enumerate(zip(['r','g','b'], ['Xb','Yb','Zb'])):
        axis_vec = R @ (axis_len * np.eye(3)[:, j])
        ax.quiver(0, 0, 0, *axis_vec, color=color, arrow_length_ratio=0.15)

    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.5); ax.set_zlim(-1.5, 1.5)
    ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
    ax.set_title(title)

plt.suptitle('无人机"+"十字形的三维旋转演示', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control1.png', dpi=150, bbox_inches='tight')
plt.show()