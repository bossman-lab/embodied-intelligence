import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ========== 3D "8"字轨迹跟踪仿真 ==========

# --- 物理参数 ---
m = 0.5; g = 9.81; dt = 0.005; T_sim = 12.0
N = int(T_sim / dt)
t = np.arange(N) * dt
Kp = np.diag([6.0, 6.0, 10.0])    # 位置 PD 增益
Kd = np.diag([4.0, 4.0, 6.0])
kp_att, kd_att = 80.0, 15.0       # 姿态 PD 增益
Ixx = Iyy = 0.002; Izz = 0.004

# --- 期望 "8" 字轨迹 ---
omega_t = 2 * np.pi / T_sim
x_des = 2.0 * np.sin(omega_t * t)
y_des = 1.5 * np.sin(2 * omega_t * t)
z_des = 1.0 + 0.3 * np.sin(omega_t * t)

# 期望速度、加速度（解析求导）
dx_des = 2.0 * omega_t * np.cos(omega_t * t)
dy_des = 1.5 * 2 * omega_t * np.cos(2 * omega_t * t)
dz_des = 0.3 * omega_t * np.cos(omega_t * t)
ddx_des = -2.0 * omega_t**2 * np.sin(omega_t * t)
ddy_des = -1.5 * (2*omega_t)**2 * np.sin(2 * omega_t * t)
ddz_des = -0.3 * omega_t**2 * np.sin(omega_t * t)

# --- 状态初始化 ---
pos = np.array([0.0, 0.0, 0.0])   # 位置
vel = np.array([0.0, 0.0, 0.0])   # 速度
phi, theta, psi = 0.0, 0.0, 0.0   # 欧拉角
dphi, dtheta, dpsi = 0.0, 0.0, 0.0

hist_pos = np.zeros((N, 3))
for i in range(N):
    p_des = np.array([x_des[i], y_des[i], z_des[i]])
    v_des = np.array([dx_des[i], dy_des[i], dz_des[i]])
    a_des = np.array([ddx_des[i], ddy_des[i], ddz_des[i]])

    # 位置 PD 控制 → 期望加速度
    ep = p_des - pos; ev = v_des - vel
    acc_cmd = a_des + Kp @ ep + Kd @ ev

    # 总推力（前馈 + PD）
    u1 = m * np.sqrt(acc_cmd[0]**2 + acc_cmd[1]**2 + (acc_cmd[2] + g)**2)
    u1 = np.clip(u1, 0.1, 4 * m * g)

    # 期望姿态角（考虑 ψ≈0 简化）
    phi_c = np.clip((acc_cmd[0]*np.sin(psi) - acc_cmd[1]*np.cos(psi)) / g, -0.5, 0.5)
    theta_c = np.clip((acc_cmd[0]*np.cos(psi) + acc_cmd[1]*np.sin(psi)) / g, -0.5, 0.5)

    # 姿态 PD 控制
    u2 = Ixx * (kp_att * (phi_c - phi) + kd_att * (0 - dphi))
    u3 = Iyy * (kp_att * (theta_c - theta) + kd_att * (0 - dtheta))

    # 简化 3D 动力学更新
    cphi, sphi = np.cos(phi), np.sin(phi)
    cth, sth = np.cos(theta), np.sin(theta)
    cpsi, spsi = np.cos(psi), np.sin(psi)
    ax = (u1/m) * (cpsi*sth*cphi + spsi*sphi)
    ay = (u1/m) * (spsi*sth*cphi - cpsi*sphi)
    az = (u1/m) * cphi*cth - g

    vel += np.array([ax, ay, az]) * dt
    pos += vel * dt
    dphi += (u2 / Ixx) * dt; phi += dphi * dt
    dtheta += (u3 / Iyy) * dt; theta += dtheta * dt

    hist_pos[i] = pos

# --- 绘图：3D 轨迹对比 ---
fig = plt.figure(figsize=(12, 8))
ax3d = fig.add_subplot(1, 1, 1, projection='3d')
ax3d.plot(x_des, y_des, z_des, 'b--', lw=1.5, alpha=0.6, label='期望轨迹（"8"字）')
ax3d.plot(hist_pos[:, 0], hist_pos[:, 1], hist_pos[:, 2],
          'r-', lw=1.2, label='实际轨迹')

# 标注起点和终点
ax3d.scatter(*hist_pos[0], c='g', s=100, marker='o', zorder=5, label='起点')
ax3d.scatter(*hist_pos[-1], c='k', s=100, marker='*', zorder=5, label='终点')

# 每隔一段绘制位置标记
step = N // 10
for j in range(0, N, step):
    ax3d.plot([x_des[j], hist_pos[j, 0]], [y_des[j], hist_pos[j, 1]],
              [z_des[j], hist_pos[j, 2]], 'k-', alpha=0.2, lw=0.8)

ax3d.set_xlabel('X (m)'); ax3d.set_ylabel('Y (m)'); ax3d.set_zlabel('Z (m)')
ax3d.set_title('第六章：3D "8"字轨迹跟踪（PD 控制）', fontsize=14)
ax3d.legend(fontsize=10)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control6.png', dpi=150, bbox_inches='tight')
plt.show()