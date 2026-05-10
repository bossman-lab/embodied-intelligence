import numpy as np
import matplotlib.pyplot as plt

# ========== 简化 1D MPC 高度控制（滚动优化 + 推力约束） ==========
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# --- 系统参数 ---
m = 0.5; g = 9.81; dt_ctrl = 0.05  # 控制周期 50ms
N_horizon = 20                       # 预测步长
T_sim = 6.0; N_sim = int(T_sim / dt_ctrl)
z_target = 2.0                       # 目标高度

# 推力约束（物理限制）
a_min = -g          # 最小加速度（自由落体，推力=0）
a_max = 2.0 * g     # 最大加速度（推力上限）

# MPC 代价权重
Q_z, Q_v, R_a = 10.0, 5.0, 0.1  # 位置、速度、控制代价

def solve_mpc(z0, v0, z_ref, N_h):
    """
    求解 1D MPC：手动构造二次规划并用 numpy 求解
    状态：[z, v]，输入：a（加速度），离散模型：z+=v*dt, v+=a*dt
    """
    # 构造预测矩阵：X = Sx*x0 + Su*U
    Sx = np.zeros((2 * N_h, 2))  # 状态传播矩阵
    Su = np.zeros((2 * N_h, N_h))  # 输入影响矩阵

    A = np.array([[1, dt_ctrl], [0, 1]])
    B = np.array([[0.5 * dt_ctrl**2], [dt_ctrl]])

    # 逐步构造预测矩阵
    A_pow = np.eye(2)
    for k in range(N_h):
        A_pow = A_pow @ A
        Sx[2*k:2*k+2, :] = A_pow
        for j in range(k + 1):
            A_mid = np.linalg.matrix_power(A, k - j)
            Su[2*k:2*k+2, j] = (A_mid @ B).flatten()

    # 代价矩阵 Q_bar, R_bar
    Q_bar = np.zeros((2 * N_h, 2 * N_h))
    for k in range(N_h):
        Q_bar[2*k, 2*k] = Q_z      # 位置权重
        Q_bar[2*k+1, 2*k+1] = Q_v  # 速度权重
    R_bar = R_a * np.eye(N_h)

    # 参考轨迹向量
    X_ref = np.zeros(2 * N_h)
    for k in range(N_h):
        X_ref[2*k] = z_ref
        X_ref[2*k+1] = 0.0  # 期望速度为 0

    x0 = np.array([z0, v0])

    # 无约束最优解：U* = (Su'QSu + R)^{-1} Su'Q(Xref - Sx*x0)
    H = Su.T @ Q_bar @ Su + R_bar
    f = Su.T @ Q_bar @ (X_ref - Sx @ x0)
    U_star = np.linalg.solve(H, f)

    # 施加约束（简单裁剪）
    U_star = np.clip(U_star, a_min, a_max)
    return U_star

# --- 仿真主循环 ---
z, v = 0.0, 0.0  # 初始状态：地面静止
hist_z, hist_v, hist_a = [], [], []
hist_pred_z = []  # 记录每步的预测轨迹（用于可视化）

for i in range(N_sim):
    U_opt = solve_mpc(z, v, z_target, N_horizon)
    a_cmd = U_opt[0]  # 只执行第一步（滚动优化）

    # 记录预测轨迹
    if i % 20 == 0:
        pred_z = [z]
        pz, pv = z, v
        for k in range(N_horizon):
            ak = np.clip(U_opt[k], a_min, a_max)
            pv += ak * dt_ctrl
            pz += pv * dt_ctrl
            pred_z.append(pz)
        hist_pred_z.append((i * dt_ctrl, pred_z))

    # 状态更新
    v += a_cmd * dt_ctrl
    z += v * dt_ctrl
    hist_z.append(z); hist_v.append(v); hist_a.append(a_cmd)

t_arr = np.arange(N_sim) * dt_ctrl

# --- 绘图 ---
fig, axes = plt.subplots(2, 2, figsize=(14, 9))

# 高度响应 + 预测轨迹
ax = axes[0, 0]
ax.plot(t_arr, hist_z, 'b-', lw=2, label='实际高度')
ax.axhline(y=z_target, color='r', ls='--', lw=1.5, label=f'目标 z={z_target}m')
for (t0, pred) in hist_pred_z:
    t_pred = t0 + np.arange(len(pred)) * dt_ctrl
    ax.plot(t_pred, pred, 'g-', alpha=0.3, lw=0.8)
ax.plot([], [], 'g-', alpha=0.5, label='预测轨迹（滚动窗口）')
ax.set_xlabel('时间 (s)'); ax.set_ylabel('高度 (m)')
ax.set_title('MPC 高度控制响应'); ax.legend(); ax.grid(True, alpha=0.3)

# 速度
ax = axes[0, 1]
ax.plot(t_arr, hist_v, 'c-', lw=1.5)
ax.set_xlabel('时间 (s)'); ax.set_ylabel('速度 (m/s)')
ax.set_title('垂直速度'); ax.grid(True, alpha=0.3)

# 控制输入（加速度/推力）
ax = axes[1, 0]
ax.plot(t_arr, hist_a, 'm-', lw=1.5, label='MPC 输出 a')
ax.axhline(y=a_max, color='r', ls=':', label=f'最大加速度 {a_max:.1f}')
ax.axhline(y=a_min, color='b', ls=':', label=f'最小加速度 {a_min:.1f}')
ax.axhline(y=0, color='k', ls='-', alpha=0.2)
ax.set_xlabel('时间 (s)'); ax.set_ylabel('加速度 (m/s²)')
ax.set_title('控制输入（含约束裁剪）'); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

# 对应推力
ax = axes[1, 1]
thrust = [m * (a + g) for a in hist_a]
ax.plot(t_arr, thrust, 'g-', lw=1.5, label='推力 u₁ = m(a+g)')
ax.axhline(y=m * g, color='k', ls='--', alpha=0.4, label=f'悬停推力 {m*g:.2f}N')
ax.axhline(y=m * (a_max + g), color='r', ls=':', alpha=0.6, label='推力上限')
ax.axhline(y=0, color='b', ls=':', alpha=0.6, label='推力下限 (0N)')
ax.set_xlabel('时间 (s)'); ax.set_ylabel('推力 (N)')
ax.set_title('推力约束可视化'); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

plt.suptitle('第八章：1D MPC 高度控制 — 滚动优化 + 推力约束', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control8.png', dpi=150, bbox_inches='tight')
plt.show()