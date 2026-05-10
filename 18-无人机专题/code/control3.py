import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ========== 微分平坦性验证：从圆形轨迹推导姿态角和推力 ==========

# --- 物理参数 ---
m = 0.5    # 无人机质量 (kg)
g = 9.81   # 重力加速度 (m/s^2)

# --- 定义圆形轨迹（平坦输出 σ = [x, y, z, ψ]） ---
T_total = 10.0              # 总时间 (s)
dt = 0.01
t = np.arange(0, T_total, dt)
omega_c = 2 * np.pi / T_total  # 圆轨迹角频率

# 位置轨迹：水平圆 + 缓慢上升 + 偏航跟随速度方向
radius = 2.0
x = radius * np.cos(omega_c * t)
y = radius * np.sin(omega_c * t)
z = 0.5 * t                                # 螺旋上升
psi = np.arctan2(np.gradient(y, dt), np.gradient(x, dt))  # 偏航角跟随速度方向

# --- 计算各阶导数 ---
ddx = np.gradient(np.gradient(x, dt), dt)  # x 的二阶导数（加速度）
ddy = np.gradient(np.gradient(y, dt), dt)  # y 的二阶导数
ddz = np.gradient(np.gradient(z, dt), dt)  # z 的二阶导数

# --- 由微分平坦性推导总推力 u1 ---
u1 = m * np.sqrt(ddx**2 + ddy**2 + (ddz + g)**2)

# --- 由加速度推导姿态角 φ (roll) 和 θ (pitch) ---
# 机体 z 轴方向（单位推力方向）
tx = ddx / (ddz + g + 1e-10)
ty = ddy / (ddz + g + 1e-10)

# 通过旋转矩阵关系推导欧拉角
phi   = np.arcsin(np.clip(tx * np.sin(psi) - ty * np.cos(psi), -1, 1))  # 滚转角
theta = np.arctan2(tx * np.cos(psi) + ty * np.sin(psi),
                   1 + ddz / g)  # 俯仰角

# --- 绘制结果 ---
fig = plt.figure(figsize=(15, 10))

# 子图 1：三维轨迹
ax1 = fig.add_subplot(2, 2, 1, projection='3d')
ax1.plot(x, y, z, 'b-', lw=1.5)
# 每隔一段标注无人机位置和朝向
step = len(t) // 8
for i in range(0, len(t), step):
    ax1.scatter(x[i], y[i], z[i], c='r', s=40, zorder=5)
    dx_arrow = 0.3 * np.cos(psi[i])
    dy_arrow = 0.3 * np.sin(psi[i])
    ax1.quiver(x[i], y[i], z[i], dx_arrow, dy_arrow, 0,
               color='r', arrow_length_ratio=0.3)
ax1.set_xlabel('X (m)'); ax1.set_ylabel('Y (m)'); ax1.set_zlabel('Z (m)')
ax1.set_title('螺旋上升轨迹 σ(t)')

# 子图 2：总推力 u1
ax2 = fig.add_subplot(2, 2, 2)
ax2.plot(t, u1, 'g-', lw=1.5)
ax2.axhline(y=m*g, color='k', ls='--', alpha=0.5, label=f'悬停推力 mg={m*g:.2f}N')
ax2.set_xlabel('时间 (s)'); ax2.set_ylabel('u₁ (N)')
ax2.set_title('总推力 u₁（由二阶导数推出）'); ax2.legend(); ax2.grid(True, alpha=0.3)

# 子图 3：滚转角 φ
ax3 = fig.add_subplot(2, 2, 3)
ax3.plot(t, np.degrees(phi), 'r-', lw=1.5, label='φ (roll)')
ax3.set_xlabel('时间 (s)'); ax3.set_ylabel('角度 (°)')
ax3.set_title('滚转角 φ（由 σ̈ 推出）'); ax3.legend(); ax3.grid(True, alpha=0.3)

# 子图 4：俯仰角 θ
ax4 = fig.add_subplot(2, 2, 4)
ax4.plot(t, np.degrees(theta), 'b-', lw=1.5, label='θ (pitch)')
ax4.set_xlabel('时间 (s)'); ax4.set_ylabel('角度 (°)')
ax4.set_title('俯仰角 θ（由 σ̈ 推出）'); ax4.legend(); ax4.grid(True, alpha=0.3)

plt.suptitle('微分平坦性验证：从轨迹 [x,y,z,ψ] 推导姿态与推力', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control3.png', dpi=150, bbox_inches='tight')
plt.show()
