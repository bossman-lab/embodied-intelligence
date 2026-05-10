import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 自带黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示为方框的问题
# ========== PID 参数调节对二阶系统阶跃响应的影响 ==========
# 被控对象：无人机高度方向简化模型  m * z̈ = u - mg
# 等效二阶系统：ë + (Kd/m)*ė + (Kp/m)*e = -(Ki/m)*∫e dt

def simulate_pid(Kp, Kd, Ki, dt=0.001, T=5.0):
    """仿真 PID 控制的二阶系统阶跃响应"""
    steps = int(T / dt)
    z = 0.0       # 当前位置（高度）
    dz = 0.0      # 当前速度
    z_des = 1.0   # 期望高度（阶跃输入）
    m = 0.5       # 无人机质量
    g = 9.81      # 重力加速度
    integral = 0.0  # 积分项

    z_hist = np.zeros(steps)
    for i in range(steps):
        e = z_des - z           # 位置误差
        de = -dz                # 速度误差（期望速度为 0）
        integral += e * dt      # 误差积分

        # PID 控制律：u = mg + Kp*e + Kd*ė + Ki*∫e
        u = m * g + Kp * e + Kd * de + Ki * integral

        # 动力学：m * z̈ = u - mg
        ddz = (u - m * g) / m
        dz += ddz * dt
        z += dz * dt
        z_hist[i] = z
    return z_hist

dt = 0.001; T = 5.0
t = np.arange(0, T, dt)

# --- 子图 1：改变 Kp（固定 Kd=2, Ki=0） ---
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

ax = axes[0]
for Kp in [1, 5, 15, 30]:
    z_hist = simulate_pid(Kp=Kp, Kd=2.0, Ki=0.0, dt=dt, T=T)
    ax.plot(t, z_hist, label=f'Kp={Kp}')
ax.axhline(y=1.0, color='k', ls='--', alpha=0.4, label='目标')
ax.set_title('改变 Kp（Kd=2, Ki=0）')
ax.set_xlabel('时间 (s)'); ax.set_ylabel('高度 z (m)')
ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
ax.set_ylim(-0.1, 1.8)

# --- 子图 2：改变 Kd（固定 Kp=15, Ki=0） ---
ax = axes[1]
for Kd in [0, 1, 3, 8]:
    z_hist = simulate_pid(Kp=15.0, Kd=Kd, Ki=0.0, dt=dt, T=T)
    ax.plot(t, z_hist, label=f'Kd={Kd}')
ax.axhline(y=1.0, color='k', ls='--', alpha=0.4, label='目标')
ax.set_title('改变 Kd（Kp=15, Ki=0）')
ax.set_xlabel('时间 (s)'); ax.set_ylabel('高度 z (m)')
ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
ax.set_ylim(-0.1, 1.8)

# --- 子图 3：改变 Ki（固定 Kp=10, Kd=3） ---
ax = axes[2]
for Ki in [0, 2, 8, 20]:
    z_hist = simulate_pid(Kp=10.0, Kd=3.0, Ki=Ki, dt=dt, T=T)
    ax.plot(t, z_hist, label=f'Ki={Ki}')
ax.axhline(y=1.0, color='k', ls='--', alpha=0.4, label='目标')
ax.set_title('改变 Ki（Kp=10, Kd=3）')
ax.set_xlabel('时间 (s)'); ax.set_ylabel('高度 z (m)')
ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
ax.set_ylim(-0.1, 1.8)

plt.suptitle('PID 参数对无人机高度阶跃响应的影响', fontsize=14)
plt.tight_layout()
import os; os.makedirs('assets', exist_ok=True)
plt.savefig('assets/control4.png', dpi=150, bbox_inches='tight')
plt.show()