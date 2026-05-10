import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
# ========== 对比：欧拉角控制 vs SE(3) 控制在大角度翻转中的表现 ==========

def vee(M):
    """反对称矩阵 → 向量"""
    return np.array([M[2,1], M[0,2], M[1,0]])

def Ry(a):
    """绕 Y 轴旋转矩阵"""
    c, s = np.cos(a), np.sin(a)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])

# --- 仿真参数（使用单位惯量简化，聚焦控制差异） ---
dt = 0.005; T_sim = 6.0; N = int(T_sim / dt)
t = np.arange(N) * dt
I_mat = np.diag([1.0, 1.0, 1.0])  # 单位惯量

# 目标：绕 Y 轴翻转 170°（接近 pitch ±90° 万向节锁区域）
flip_angle = np.deg2rad(170)
R_des = Ry(flip_angle)

# --- 方法 1：欧拉角 PD 控制 ---
euler = np.zeros(3)   # [phi, theta, psi]
deuler = np.zeros(3)
kp_e, kd_e = 4.0, 3.0

# 从 R_des 提取目标欧拉角（ZYX 顺序）
theta_des = np.arctan2(-R_des[2,0], np.sqrt(R_des[0,0]**2 + R_des[1,0]**2))
phi_des = np.arctan2(R_des[2,1], R_des[2,2])
psi_des = np.arctan2(R_des[1,0], R_des[0,0])
euler_des = np.array([phi_des, theta_des, psi_des])

err_euler = np.zeros(N)
for i in range(N):
    e_ang = euler_des - euler
    err_euler[i] = np.linalg.norm(e_ang)
    tau = kp_e * e_ang + kd_e * (-deuler)
    deuler += tau * dt
    euler += deuler * dt

# --- 方法 2：SE(3) 控制 ---
R_cur = np.eye(3)
omega = np.zeros(3)
kR, kw = 4.0, 3.0
err_se3 = np.zeros(N)
for i in range(N):
    eR_mat = R_des.T @ R_cur - R_cur.T @ R_des
    eR = 0.5 * vee(eR_mat)
    err_se3[i] = np.linalg.norm(eR)
    tau_se3 = -kR * eR - kw * omega
    omega += tau_se3 * dt
    # Rodrigues 公式更新旋转矩阵
    wx = omega * dt
    ang = np.linalg.norm(wx)
    if ang > 1e-12:
        K = np.array([[0,-wx[2],wx[1]],[wx[2],0,-wx[0]],[-wx[1],wx[0],0]]) / ang
        dR = np.eye(3) + np.sin(ang)*K + (1-np.cos(ang))*(K@K)
    else:
        dR = np.eye(3)
    R_cur = R_cur @ dR

# --- 绘图对比 ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(t, err_euler, 'r-', lw=1.5, label='欧拉角 PD 误差')
axes[0].plot(t, err_se3, 'b-', lw=1.5, label='SE(3) 姿态误差')
axes[0].set_xlabel('时间 (s)'); axes[0].set_ylabel('姿态误差范数')
axes[0].set_title('姿态误差对比（目标：绕 Y 轴翻转 170°）')
axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].semilogy(t, np.clip(err_euler, 1e-10, None), 'r-', lw=1.5, label='欧拉角 PD')
axes[1].semilogy(t, np.clip(err_se3, 1e-10, None), 'b-', lw=1.5, label='SE(3)')
axes[1].set_xlabel('时间 (s)'); axes[1].set_ylabel('姿态误差（对数）')
axes[1].set_title('对数尺度对比'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

plt.suptitle('第七章：欧拉角 vs SE(3) 控制 — 大角度翻转机动', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control7.png', dpi=150, bbox_inches='tight')
plt.show()
