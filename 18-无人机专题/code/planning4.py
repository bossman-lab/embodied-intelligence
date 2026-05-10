import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import block_diag
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ============================================================
# Minimum Snap 闭式求解 vs KKT/QP 求解 —— 3航点（2段）对比验证
# 闭式解：d_P = -R_PP^{-1} R_FP^T d_F
# KKT解：通过拉格朗日乘子法求解等式约束QP
# ============================================================

N = 7   # 7阶多项式
M = 2   # 2段（3个航点）
n_c = N + 1  # 每段系数数 = 8

# --- 航点定义（一维 x 轴，简化演示） ---
waypoints = np.array([0.0, 5.0, 12.0])  # 起点、中间点、终点
T_seg = np.array([2.0, 3.0])            # 各段时间

def poly_coeff_vec(n, t, deriv=0):
    """n阶多项式在t处deriv阶导数的系数行向量"""
    c = np.zeros(n + 1)
    for i in range(deriv, n + 1):
        c[i] = np.prod(range(i, i - deriv, -1)) * t ** (i - deriv)
    return c

def build_Q_seg(n, T, kr=4):
    """构造单段 snap 代价矩阵"""
    Q = np.zeros((n + 1, n + 1))
    for i in range(kr, n + 1):
        for j in range(kr, n + 1):
            ci = np.prod(range(i, i - kr, -1))
            cj = np.prod(range(j, j - kr, -1))
            Q[i, j] = ci * cj * T ** (i + j - 2*kr + 1) / (i + j - 2*kr + 1)
    return Q

# ===================== 方法1：KKT 求解 =====================
Q_all = block_diag(*[build_Q_seg(N, T) for T in T_seg])
dim = M * n_c

rows, rhs = [], []
def add_eq(row, val):
    rows.append(row); rhs.append(val)

# 起点约束：p=0, v=0, a=0
for d in range(3):
    r = np.zeros(dim); r[:n_c] = poly_coeff_vec(N, 0, d)
    add_eq(r, waypoints[0] if d == 0 else 0.0)
# 终点约束：p=12, v=0, a=0
for d in range(3):
    r = np.zeros(dim); r[n_c:] = poly_coeff_vec(N, T_seg[1], d)
    add_eq(r, waypoints[2] if d == 0 else 0.0)
# 中间航点位置约束（段0终点）
r = np.zeros(dim); r[:n_c] = poly_coeff_vec(N, T_seg[0], 0)
add_eq(r, waypoints[1])
# 连续性约束（0~3阶导数）
for d in range(4):
    r = np.zeros(dim)
    r[:n_c] = poly_coeff_vec(N, T_seg[0], d)
    r[n_c:] = -poly_coeff_vec(N, 0, d)
    add_eq(r, 0.0)

Aeq = np.array(rows); beq = np.array(rhs)
n_eq = len(beq)
KKT = np.zeros((dim + n_eq, dim + n_eq))
KKT[:dim, :dim] = 2 * Q_all
KKT[:dim, dim:] = Aeq.T
KKT[dim:, :dim] = Aeq
rhs_kkt = np.zeros(dim + n_eq); rhs_kkt[dim:] = beq
P_kkt = np.linalg.solve(KKT, rhs_kkt)[:dim]

# ===================== 方法2：闭式解 =====================
# 构造映射矩阵 A_map: 每段端点导数值 -> 多项式系数
# 每段8个系数，端点处有 0~3阶导数（起点4个+终点4个=8个方程）
def build_A_seg(n, T):
    """构造单段的端点约束矩阵（8x8）"""
    A = np.zeros((2*4, n+1))
    for d in range(4):
        A[d, :] = poly_coeff_vec(n, 0, d)       # 起点 d 阶导数
        A[4+d, :] = poly_coeff_vec(n, T, d)     # 终点 d 阶导数
    return A

A_map = block_diag(*[build_A_seg(N, T) for T in T_seg])  # 16x16
# d_alpha: 按段排列的端点导数值 [seg0起(p,v,a,j), seg0终(p,v,a,j), seg1起(...), seg1终(...)]
# M矩阵：合并连续性（seg0终 = seg1起），将16维d_alpha映射为12维独立变量d
# 独立端点集：seg0起(4), 中间点(4，共享), seg1终(4) = 12 个变量
M_mat = np.zeros((16, 12))
M_mat[0:4, 0:4] = np.eye(4)     # seg0 起点 -> 独立变量 0~3
M_mat[4:8, 4:8] = np.eye(4)     # seg0 终点 -> 中间点变量 4~7
M_mat[8:12, 4:8] = np.eye(4)    # seg1 起点 -> 中间点变量 4~7（连续性）
M_mat[12:16, 8:12] = np.eye(4)  # seg1 终点 -> 独立变量 8~11

# C矩阵：将独立变量重排为 [Fixed; Free]
# Fixed: seg0起_p(0), seg0起_v(0), seg0起_a(0), 中间_p(5), seg1终_p(12), seg1终_v(0), seg1终_a(0) = 7个
# Free:  seg0起_j, 中间_v, 中间_a, 中间_j, seg1终_j = 5个
fixed_idx = [0, 1, 2, 4, 8, 9, 10]  # 在12维独立变量中的索引
free_idx  = [3, 5, 6, 7, 11]
d_F = np.array([waypoints[0], 0, 0, waypoints[1], waypoints[2], 0, 0])
n_fixed, n_free = len(fixed_idx), len(free_idx)

C_mat = np.zeros((12, 12))
for i, fi in enumerate(fixed_idx):
    C_mat[fi, i] = 1.0
for i, fi in enumerate(free_idx):
    C_mat[fi, n_fixed + i] = 1.0

# K = A_map^{-1} @ M @ C
K = np.linalg.solve(A_map, M_mat @ C_mat)

# R = K^T Q K，分块为 R_FF, R_FP, R_PF, R_PP
R_full = K.T @ Q_all @ K
R_FF = R_full[:n_fixed, :n_fixed]
R_FP = R_full[:n_fixed, n_fixed:]
R_PP = R_full[n_fixed:, n_fixed:]

# 闭式解核心公式
d_P = -np.linalg.solve(R_PP, R_FP.T @ d_F)
d_prime = np.concatenate([d_F, d_P])
P_closed = K @ d_prime

# ===================== 采样与对比绘图 =====================
def sample_traj(P_vec, T_seg, N):
    t_all, pos_kkt, vel_kkt = [], [], []
    t_offset = 0.0
    for k in range(len(T_seg)):
        ts = np.linspace(0, T_seg[k], 150)
        p = P_vec[k*n_c:(k+1)*n_c]
        pos_kkt.extend([poly_coeff_vec(N, t, 0) @ p for t in ts])
        vel_kkt.extend([poly_coeff_vec(N, t, 1) @ p for t in ts])
        t_all.extend(ts + t_offset)
        t_offset += T_seg[k]
    return np.array(t_all), np.array(pos_kkt), np.array(vel_kkt)

t1, pos1, vel1 = sample_traj(P_kkt, T_seg, N)
t2, pos2, vel2 = sample_traj(P_closed, T_seg, N)

fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
# 位置对比
axes[0].plot(t1, pos1, 'b-', linewidth=2.5, label='KKT/QP 求解')
axes[0].plot(t2, pos2, 'r--', linewidth=2, label='闭式解')
t_wp = [0, T_seg[0], T_seg[0]+T_seg[1]]
axes[0].plot(t_wp, waypoints, 'ko', markersize=8, zorder=5, label='航点')
axes[0].set_ylabel('位置 (m)'); axes[0].legend(); axes[0].grid(True, alpha=0.3)
axes[0].set_title('Minimum Snap 闭式解 vs KKT 求解 —— 轨迹完全重合验证')

# 速度对比
axes[1].plot(t1, vel1, 'b-', linewidth=2.5, label='KKT/QP 速度')
axes[1].plot(t2, vel2, 'r--', linewidth=2, label='闭式解速度')
axes[1].set_ylabel('速度 (m/s)'); axes[1].set_xlabel('时间 (s)')
axes[1].legend(); axes[1].grid(True, alpha=0.3)

# 打印误差
err = np.max(np.abs(P_kkt - P_closed))
print(f"两种方法系数最大绝对误差: {err:.2e}")
fig.text(0.5, 0.01, f'系数最大绝对误差: {err:.2e}（验证两种方法等价）',
         ha='center', fontsize=11, color='green')
plt.tight_layout(rect=[0, 0.03, 1, 1])
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/planning4.png', dpi=150, bbox_inches='tight')
plt.show()