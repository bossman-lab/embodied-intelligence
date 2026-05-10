import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ========== 2D 无人机（Y-Z 平面）前馈 + PD 控制仿真 ==========

# --- 物理参数 ---
m = 0.5          # 质量 (kg)
g = 9.81         # 重力加速度 (m/s^2)
Ixx = 0.002      # 绕 x 轴转动惯量 (kg·m^2)
dt = 0.002       # 仿真步长 (s)
T_sim = 6.0      # 总仿真时间
N = int(T_sim / dt)

# --- PD 增益 ---
kp_z, kd_z = 15.0, 8.0       # Z 轴位置 PD
kp_y, kd_y = 8.0, 6.0        # Y 轴位置 PD
kp_phi, kd_phi = 150.0, 20.0 # 姿态角 PD

# --- 期望轨迹：悬停 2s 后移动到目标位置 ---
y_des = np.where(np.arange(N) * dt < 2.0, 0.0, 2.0)
z_des = np.where(np.arange(N) * dt < 2.0, 1.0, 2.5)

# --- 状态初始化 [y, z, phi, dy, dz, dphi] ---
state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
hist_y, hist_z, hist_u1, hist_u2, hist_phi = [], [], [], [], []

for i in range(N):
    y, z, phi, dy, dz, dphi = state

    # 外环：Z 轴 PD + 重力前馈
    ddz_c = kp_z * (z_des[i] - z) + kd_z * (0 - dz)
    u1 = m * (g + ddz_c) / (np.cos(phi) + 1e-6)  # 前馈：mg/cos(φ)
    u1 = np.clip(u1, 0, 3 * m * g)  # 推力限幅

    # 外环：Y 轴 PD → 期望滚转角
    ddy_c = kp_y * (y_des[i] - y) + kd_y * (0 - dy)
    phi_c = -ddy_c / g  # 由线性化关系 ÿ = -g·φ
    phi_c = np.clip(phi_c, -0.5, 0.5)  # 限制期望角度

    # 内环：姿态 PD
    u2 = Ixx * (kp_phi * (phi_c - phi) + kd_phi * (0 - dphi))

    # 非线性动力学更新
    ddy = -(u1 / m) * np.sin(phi)
    ddz = (u1 / m) * np.cos(phi) - g
    ddphi = u2 / Ixx

    state += np.array([dy, dz, dphi, ddy, ddz, ddphi]) * dt

    hist_y.append(y); hist_z.append(z)
    hist_u1.append(u1); hist_u2.append(u2); hist_phi.append(phi)

t_arr = np.arange(N) * dt

# --- 绘图：2 行 2 列 ---
fig, axes = plt.subplots(2, 2, figsize=(13, 9))

# Y-Z 轨迹
axes[0, 0].plot(hist_y, hist_z, 'b-', lw=1.5, label='实际轨迹')
axes[0, 0].plot(y_des[0], z_des[0], 'go', ms=10, label='起始目标')
axes[0, 0].plot(y_des[-1], z_des[-1], 'r*', ms=14, label='终点目标')
axes[0, 0].set_xlabel('Y (m)'); axes[0, 0].set_ylabel('Z (m)')
axes[0, 0].set_title('Y-Z 平面飞行轨迹'); axes[0, 0].legend(); axes[0, 0].grid(True, alpha=0.3)

# 高度与水平位置响应
axes[0, 1].plot(t_arr, hist_z, 'b-', label='z 实际')
axes[0, 1].plot(t_arr, z_des, 'b--', alpha=0.5, label='z 期望')
axes[0, 1].plot(t_arr, hist_y, 'r-', label='y 实际')
axes[0, 1].plot(t_arr, y_des, 'r--', alpha=0.5, label='y 期望')
axes[0, 1].set_xlabel('时间 (s)'); axes[0, 1].set_ylabel('位置 (m)')
axes[0, 1].set_title('位置跟踪响应'); axes[0, 1].legend(); axes[0, 1].grid(True, alpha=0.3)

# 控制输入
axes[1, 0].plot(t_arr, hist_u1, 'g-', label='u₁ (总推力)')
axes[1, 0].axhline(y=m * g, color='k', ls='--', alpha=0.4, label=f'悬停推力 mg={m*g:.2f}')
axes[1, 0].set_xlabel('时间 (s)'); axes[1, 0].set_ylabel('推力 (N)')
axes[1, 0].set_title('总推力 u₁'); axes[1, 0].legend(); axes[1, 0].grid(True, alpha=0.3)

# 滚转角
axes[1, 1].plot(t_arr, np.degrees(hist_phi), 'm-', label='φ (滚转角)')
axes[1, 1].set_xlabel('时间 (s)'); axes[1, 1].set_ylabel('角度 (°)')
axes[1, 1].set_title('滚转角 φ 响应'); axes[1, 1].legend(); axes[1, 1].grid(True, alpha=0.3)

plt.suptitle('第五章：2D 无人机前馈 + PD 控制仿真（悬停→移动）', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control5.png', dpi=150, bbox_inches='tight')
plt.show()