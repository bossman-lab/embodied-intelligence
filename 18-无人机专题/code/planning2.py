import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ============================================================
# Minimum Snap 轨迹生成 —— 无人机依次飞过多个航点
# 使用 KKT 系统（拉格朗日乘子法）求解等式约束 QP 的闭式解
# ============================================================

# --- 航点定义（二维：x, y） ---
waypoints = np.array([
    [0.0, 0.0],   # 起点
    [2.0, 2.5],   # 中间点1
    [5.0, 4.0],   # 中间点2
    [8.0, 3.0],   # 中间点3
    [10.0, 5.0],  # 终点
])
M = len(waypoints) - 1  # 4 段
N = 7                    # 7阶多项式（8个系数，minimum snap）

# --- 时间分配（按段长等比例分配，总时间8秒） ---
dists = np.linalg.norm(np.diff(waypoints, axis=0), axis=1)
T_total = 8.0
T_seg = T_total * dists / dists.sum()  # 各段时间

def build_Q_seg(n, T, kr=4):
    """构造单段 snap 代价矩阵 Q（相对时间，t in [0, T]）"""
    Q = np.zeros((n+1, n+1))
    for i in range(kr, n+1):
        for j in range(kr, n+1):
            ci = np.prod(range(i, i-kr, -1))   # i!/(i-kr)!
            cj = np.prod(range(j, j-kr, -1))
            Q[i, j] = ci * cj * T**(i+j-2*kr+1) / (i+j-2*kr+1)
    return Q

def poly_coeff_vec(n, t, deriv=0):
    """返回 n 阶多项式在 t 处 deriv 阶导数的系数行向量"""
    c = np.zeros(n+1)
    for i in range(deriv, n+1):
        c[i] = np.prod(range(i, i-deriv, -1)) * t**(i-deriv)
    return c

# --- 构造总 Q 矩阵（分块对角） ---
dim_total = M * (N+1)
Q_all = np.zeros((dim_total, dim_total))
for k in range(M):
    idx = k * (N+1)
    Q_all[idx:idx+N+1, idx:idx+N+1] = build_Q_seg(N, T_seg[k])

# --- 构造等式约束矩阵 Aeq @ P = beq ---
constraints_rows = []
constraints_rhs_x = []
constraints_rhs_y = []

def add_constraint(row_vec, rhs_x, rhs_y):
    constraints_rows.append(row_vec)
    constraints_rhs_x.append(rhs_x)
    constraints_rhs_y.append(rhs_y)

# 起始点约束：位置、速度、加速度、jerk（段0，t=0）
for d in range(4):
    row = np.zeros(dim_total)
    row[0:N+1] = poly_coeff_vec(N, 0, d)
    val = waypoints[0] if d == 0 else np.array([0.0, 0.0])
    add_constraint(row, val[0], val[1])

# 终端约束：位置、速度、加速度、jerk（最后一段，t=T_M）
for d in range(4):
    row = np.zeros(dim_total)
    idx = (M-1)*(N+1)
    row[idx:idx+N+1] = poly_coeff_vec(N, T_seg[-1], d)
    val = waypoints[-1] if d == 0 else np.array([0.0, 0.0])
    add_constraint(row, val[0], val[1])

# 中间航点位置约束 + 连续性约束
for k in range(M-1):
    # 第 k 段终点位置 = waypoints[k+1]
    row = np.zeros(dim_total)
    idx = k * (N+1)
    row[idx:idx+N+1] = poly_coeff_vec(N, T_seg[k], 0)
    add_constraint(row, waypoints[k+1, 0], waypoints[k+1, 1])
    # 连续性：第 k 段终点 = 第 k+1 段起点（0~3阶导数）
    for d in range(4):
        row = np.zeros(dim_total)
        row[idx:idx+N+1] = poly_coeff_vec(N, T_seg[k], d)
        idx2 = (k+1) * (N+1)
        row[idx2:idx2+N+1] = -poly_coeff_vec(N, 0, d)
        add_constraint(row, 0.0, 0.0)

Aeq = np.array(constraints_rows)
beq_x = np.array(constraints_rhs_x)
beq_y = np.array(constraints_rhs_y)

# --- KKT 系统求解：[2Q, A^T; A, 0] [P; lam] = [0; b] ---
n_eq = Aeq.shape[0]
KKT = np.zeros((dim_total + n_eq, dim_total + n_eq))
KKT[:dim_total, :dim_total] = 2 * Q_all
KKT[:dim_total, dim_total:] = Aeq.T
KKT[dim_total:, :dim_total] = Aeq

def solve_axis(beq):
    rhs = np.zeros(dim_total + n_eq)
    rhs[dim_total:] = beq
    sol = np.linalg.solve(KKT, rhs)
    return sol[:dim_total]

Px = solve_axis(beq_x)
Py = solve_axis(beq_y)

# --- 采样轨迹并计算各阶导数 ---
t_all, x_all, y_all = [], [], []
derivs = {d: ([], []) for d in range(5)}  # 0~4阶
t_cum = 0.0
for k in range(M):
    ts = np.linspace(0, T_seg[k], 100)
    idx = k * (N+1)
    px, py = Px[idx:idx+N+1], Py[idx:idx+N+1]
    for d in range(5):
        cx = np.array([poly_coeff_vec(N, t, d) @ px for t in ts])
        cy = np.array([poly_coeff_vec(N, t, d) @ py for t in ts])
        derivs[d][0].extend(cx)
        derivs[d][1].extend(cy)
    t_all.extend(ts + t_cum)
    t_cum += T_seg[k]

# --- 绘图 ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 左图：二维轨迹
ax = axes[0]
ax.plot(derivs[0][0], derivs[0][1], 'b-', linewidth=2, label='Minimum Snap 轨迹')
ax.plot(waypoints[:, 0], waypoints[:, 1], 'ro-', markersize=8, linewidth=1, label='航点')
for i, wp in enumerate(waypoints):
    ax.annotate(f'P{i}', wp, textcoords="offset points", xytext=(5, 8), fontsize=10)
ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)')
ax.set_title('无人机 Minimum Snap 二维轨迹'); ax.legend(); ax.grid(True, alpha=0.3)
ax.set_aspect('equal')

# 右图：各阶导数随时间变化（仅 x 轴分量）
ax2 = axes[1]
labels = ['位置 (m)', '速度 (m/s)', '加速度 (m/s²)', 'Jerk', 'Snap']
for d in range(5):
    ax2.plot(t_all, derivs[d][0], label=labels[d], alpha=0.85)
ax2.set_xlabel('时间 (s)'); ax2.set_ylabel('X 轴分量')
ax2.set_title('X 轴各阶导数曲线'); ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)

plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/planning2.png', dpi=150, bbox_inches='tight')
plt.show()