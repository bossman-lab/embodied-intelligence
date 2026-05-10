import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ============================================================
# 五次多项式两点插值 —— 无人机从静止起飞到目标点
# 给定起点和终点的位置、速度、加速度，求解6x6矩阵方程得到多项式系数
# ============================================================

# --- 边界条件设置（模拟无人机垂直起飞） ---
T = 3.0          # 飞行时间 3 秒
# t=0 时刻：地面静止
pos0, vel0, acc0 = 0.0, 0.0, 0.0
# t=T 时刻：到达 10m 高度，悬停（速度和加速度均为零）
posT, velT, accT = 10.0, 0.0, 0.0

# --- 构造 6x6 约束矩阵 ---
# X(t) = p0 + p1*t + p2*t^2 + p3*t^3 + p4*t^4 + p5*t^5
A = np.array([
    [1, 0,   0,       0,         0,          0        ],   # X(0)   = pos0
    [0, 1,   0,       0,         0,          0        ],   # X'(0)  = vel0
    [0, 0,   2,       0,         0,          0        ],   # X''(0) = acc0
    [1, T,   T**2,    T**3,      T**4,       T**5     ],   # X(T)   = posT
    [0, 1,   2*T,     3*T**2,    4*T**3,     5*T**4   ],   # X'(T)  = velT
    [0, 0,   2,       6*T,       12*T**2,    20*T**3  ],   # X''(T) = accT
])
b = np.array([pos0, vel0, acc0, posT, velT, accT])

# --- 求解多项式系数 ---
coeffs = np.linalg.solve(A, b)
print("多项式系数 [p0, p1, p2, p3, p4, p5]:", np.round(coeffs, 4))

# --- 在时间轴上采样并计算 位置/速度/加速度 ---
t = np.linspace(0, T, 200)
pos = sum(coeffs[i] * t**i for i in range(6))
vel = sum(i * coeffs[i] * t**(i-1) for i in range(1, 6))
acc = sum(i * (i-1) * coeffs[i] * t**(i-2) for i in range(2, 6))

# --- 绘图 ---
fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
titles = ["位置 (m)", "速度 (m/s)", "加速度 (m/s²)"]
data = [pos, vel, acc]
colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

for ax, title, y, c in zip(axes, titles, data, colors):
    ax.plot(t, y, color=c, linewidth=2)
    ax.set_ylabel(title, fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='gray', linewidth=0.5)

# 标注起点和终点
axes[0].plot(0, pos0, 'ko', markersize=8, label='起飞点')
axes[0].plot(T, posT, 'r*', markersize=12, label='目标悬停点')
axes[0].legend(fontsize=10)

axes[-1].set_xlabel("时间 (s)", fontsize=12)
fig.suptitle("五次多项式轨迹 —— 无人机从地面起飞到 10m 悬停", fontsize=13)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/planning1.png', dpi=150, bbox_inches='tight')
plt.show()