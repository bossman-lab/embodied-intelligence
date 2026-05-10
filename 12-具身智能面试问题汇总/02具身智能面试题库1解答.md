### 1. 看你用了扩散模型，现在大家都说End-to-End，你为什么要把 VLM和 Diffusion解耦？如果我直接用一个大的多模态模型输出坐标点，你觉得在手术这种精度场景下，最大的瓶颈会出现在哪

虽然端到端（End-to-End）是大势所趋，但在手术这种极高精度的动态场景下，直接用大模型输出坐标点存在致命的**“感知-执行”延迟问题**。

- **解耦的逻辑**：VLM 负责低频的高层语义理解与规划（大脑），而 Diffusion 负责高频、连续的底层动作生成（小脑）。在离散的视觉更新之间，高频策略（例如实现从个位数 Hz 跃升至数十 Hz 的推理加速）对于连续的帧内轨迹插值是必不可少的，从而真正解决现实世界动态操作中的“感知-执行”延迟问题。

- **端到端的瓶颈**：最大的瓶颈在于**控制频率与真实世界动态变化的错位**，以及 VLM 离散 Token 带来的**空间分辨率灾难**。如果设环境真实动态变化的频率为 $f_{env}$，VLM 的推理频率为 $f_{vlm}$。当 $f_{vlm} \ll f_{env}$ 时，下发的动作序列 $a_t$ 会面临严重的相位滞后：

  $$a_t = \pi_{vlm}(o_{t-\Delta t})$$

  其中 $\Delta t$ 是 VLM 的推理延迟。在手术中，这会导致当机械臂执行动作 $a_t$ 时，真实的组织状态已经从 $o_{t-\Delta t}$ 演变到了 $o_t$，产生不可逆的医疗事故。解耦后，我们能以 $f_{diff} \gg f_{env}$ 的高频执行 $a_t \sim p_\theta(a_t | o_t, z_{vlm})$。

### 2. 扩散模型生成的是Action Chunk，但在手术中，组织形变是实时的。如果你的 Chunk 还没跑完，组织已经发生了非线性位移，你的系统怎么做闭环修正？

Diffusion 生成 Action Chunk 会带来“开环执行”的盲区。面对手术中组织的实时非线性形变，必须依赖严格的闭环修正：

- **滚动时域控制 (Receding Horizon Control, RHC)**：模型生成包含 $T$ 步轨迹的 Chunk：$\hat{A}_t = [a_t, a_{t+1}, \dots, a_{t+T-1}]$。但我们只执行前 $k$ 步（$k \ll T$），并在 $t+k$ 时刻重新获取观测 $o_{t+k}$ 生成新的 Chunk。

- **高频多模态打断**：在执行极短时间内，引入超高频的力矩反馈（Force/Torque Sensor）。定义当前实测力矩向量为 $F_{ext}$，安全阈值为 $\tau_{safe}$。控制器逻辑为：

  $$a_{exec} = \begin{cases} \hat{A}_t[i], & \text{if } \| F_{ext} \| \le \tau_{safe} \\ a_{suspend}, & \text{if } \| F_{ext} \| > \tau_{safe} \end{cases}$$

  一旦 $\| F_{ext} \|$ 突变越界（表明组织发生预料外形变），底层控制器立即熔断当前 Chunk。

### 3. 用扩散模型处理多峰分布举一个手术中的例子？面对两种都合理的避障路径，模型是怎么避免决策摇摆

- **手术例子**：假设机械臂在剥离组织时前方遇到一根血管，既可以从左侧绕过（轨迹 $\mu_{left}$），也可以从右侧绕过（轨迹 $\mu_{right}$）。真实的动作分布是一个双峰分布：

  $$p(a|o) = w_1 \mathcal{N}(\mu_{left}, \Sigma) + w_2 \mathcal{N}(\mu_{right}, \Sigma)$$

  如果用传统的 MSE Loss：$\mathcal{L} = \| a - \hat{a} \|_2^2$，模型预测的动作 $\hat{a}$ 会收敛于数学期望 $\mathbb{E}[a|o] \approx \frac{\mu_{left} + \mu_{right}}{2}$，导致机械臂直接撞向中间的血管。Diffusion 的去噪过程通过学习得分函数 $\nabla_a \log p(a|o)$，能精确拟合真实分布，通过朗之万动力学采样坍缩到“绝对左”或“绝对右”。

- **避免决策摇摆**：引入**动作指数移动平均 (Action EMA)**。设 $t$ 时刻实际执行的动作为 $a_t^{(final)}$，它是当前生成的动作与历史动作的加权：

  $$a_t^{(final)} = \alpha a_t^{(new)} + (1 - \alpha) a_{t-1}^{(final)}$$

  其中 $\alpha \in (0, 1)$ 是平滑系数。通过给历史决策赋予权重，打破了由于采样随机性导致的左右对称摇摆。

### 4. 手术动辄几小时，Transformer 的 KV Cache 会随时间爆炸，虽然换了 Mamba。但 Mamba 的线性压缩本质上是Lossy，怎么保证它在记录了前一个小时的操作后，还能精准记得现在对应的逻辑，而不是产生幻觉？

Mamba 的状态压缩由于固定了隐状态 $h_t \in \mathbb{R}^n$ 的维度，本质上是马尔可夫的有损压缩。防止几小时前逻辑混乱的方法：

- **状态重置 (State Reset)**：手术有严格阶段划分。切换阶段时，主动将底层的物理隐状态 $h_t$ 乘以一个衰减门控 $g_t \to 0$，即 $h_t \leftarrow g_t \odot h_{t-1}$，清空无用的高频历史噪音。

- **层次化语义锚点**：不要让 Mamba 记住所有的底层动作序列 $a_{0:t}$。将过去的“大逻辑”通过 VLM 抽象为离散的 Milestone 集合 $S = \{s_1, s_2, \dots, s_k\}$（如“已完成组织剥离”）。这些语义信息作为高维条件向量 $c_{semantic}$ 定期注入：

  $$h_t = \bar{A} h_{t-1} + \bar{B} x_t + W c_{semantic}$$

  （$W$ 为投影矩阵），以此维持精准的长期逻辑。

### 5. 刚才提到了Transformer和Mamba，然后你能讲一下这两个结构的一个区别吗？

- **Transformer**：核心是自注意力机制（Self-Attention），计算公式为：

  $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

  其中 $Q, K, V \in \mathbb{R}^{N \times d_k}$（$N$ 为序列长度，$d_k$ 为特征维度）。它需要全局纵览所有 Token，捕获显式的全局空间与时间依赖。

- **Mamba**：基于选择性状态空间模型（Selective SSM）， 它是连续时间动力学系统的离散化。本质上是带有数据依赖门控机制的线性 RNN。隐状态 $h_t$ 随时间步顺序递推：

  $$h'(t) = A h(t) + B x(t)$$

  它不需要在当前时刻回头计算历史的所有 Token。

### 6. 解释一下为什么Transformer是 N 的平方，然后Mamba是线性的。

- **Transformer ($O(N^2)$)**：在计算注意力分数矩阵 $S = QK^T$ 时，$Q$ 的维度是 $N \times d_k$，$K^T$ 的维度是 $d_k \times N$。矩阵乘法的计算复杂度为 $\mathcal{O}(N^2 \cdot d_k)$。因为每一个 Token 都必须与序列中的所有其他 $N-1$ 个 Token 计算点积，内存和计算量随序列长度 $N$ 呈二次方爆炸。
- **Mamba ($O(N)$)**：Mamba 通过固定维度的隐状态 $h_t \in \mathbb{R}^n$ 处理序列。离散化后的状态更新为 $h_t = \bar{A} h_{t-1} + \bar{B} x_t$。对于序列中的每一个新 Token $x_t$，只需进行向量与矩阵的乘法，单步更新复杂度恒定为 $\mathcal{O}(n^2)$ 或更低（对角化处理后）。总长度为 $N$ 的序列，总复杂度为 $\mathcal{O}(N \cdot n)$，呈线性增长。

### 7. 有没有做过定量的实验，就是Mamba会相比的性能上会有变化吗？就在精度上。

在具身智能的真实实验中：

- **局部精度损失**：在需要极高频空间微调的短序列动作上，Mamba 的绝对成功率可能会略低于 Transformer（通常在 1%-3% 左右）。数学上，这是一个**信息瓶颈 (Information Bottleneck)** 问题。设输入序列包含的信息熵为 $H(X)$，而固定维度隐状态的容量为 $C(h_t)$。当 $H(X) > C(h_t)$ 时，高频空间特征不可避免地被截断丢失。
- **长序列优势**：在长时间跨度（$N \to \infty$）控制上，Transformer 的 softmax 分布会因为 $\sum_{j=1}^N \exp(q_i \cdot k_j)$ 分母过大而产生注意力稀释（Attention Dilution），导致性能崩塌；而 Mamba 则能保持极高的推理帧率和平滑度。

### 8. 你刚才讲到你这里其实还有一个高层的一个规划模型，这个模型是用什么做的呢？

通常是一个多模态大语言模型（VLM），例如基于 Qwen-VL、LLaVA 或 Gemini 架构微调的模型。

用函数表示为：

$$z_t = f_{vlm}(I_{img}, s_{proprio}, P_{text} ; \theta_{vlm})$$

其中 $I_{img}$ 为当前手术视野图像，$s_{proprio}$ 为机械臂本体状态，$P_{text}$ 为文本指令，$\theta_{vlm}$ 为模型权重。输出的 $z_t$ 是下一步的离散子任务指令（如 `[GRASP, NEEDLE]`）。

### 9. 输入多少张历史图片呢，如果就是只做就是做那个高层的那个规划模型，它只用三到五张，它能记住之前的所有的那些操作吗，为什么

因为高层任务在宏观语义层面严格符合**马尔可夫决策过程 (MDP)**。

在 MDP 中，未来状态仅依赖于当前状态和动作，即：

$$P(S_{t+1} | S_t, A_t, \dots, S_0, A_0) = P(S_{t+1} | S_t, A_t)$$

高层模型不需要知道 10 分钟前的微观轨迹。它只需要通过 3-5 张图（当前帧 + 少量历史帧）计算当前环境的一阶导数（即动态趋势）：

$$\dot{O}_t \approx \frac{O_t - O_{t-k}}{k \cdot \Delta t}$$

“当前的视觉状态”加上这代表趋势的“少量历史帧”，结合文本指令给出的最终目标，已足以提供求解 MDP 的完整语义上下文。

### 10. 整个这个高层模型的训练是怎么做的

训练分为三个阶段：

1. **大规模预训练**：建立基础图文表征。

2. **SFT（监督微调）**：使用大量医生手术视频，提取关键帧和动作打标签。最小化负对数似然损失：

   $$\mathcal{L}_{SFT} = - \sum_{t=1}^T \log p_{\theta}(a_t^* | O_{\le t}, P_{text})$$

   其中 $a_t^*$ 为医生真实操作指令。

3. **对齐训练（RLHF/DPO）**：由专业医生给出偏好反馈。以 DPO (Direct Preference Optimization) 为例，针对安全和危险操作优化策略 $\pi_\theta$：

   $$\mathcal{L}_{DPO} = -\mathbb{E}_{(x, y_w, y_l)} \left[ \log \sigma \left( \beta \log \frac{\pi_\theta(y_w|x)}{\pi_{ref}(y_w|x)} - \beta \log \frac{\pi_\theta(y_l|x)}{\pi_{ref}(y_l|x)} \right) \right]$$

   $y_w$ 为安全的偏好操作，$y_l$ 为危险的违规操作。

### 11. 在Mamba的Selective Scan里，是怎么定义‘什么该忘、什么该记’的？如果系统不小心把一个转瞬即逝的微小的点给遗忘了，怎么办

- **什么该忘，什么该记**：Mamba 的时间步长参数 $\Delta_t$ 是输入 $x_t$ 的线性投影函数：

  $$\Delta_t = \text{softplus}(\text{Linear}(x_t))$$

  当网络学习到 $x_t$ 是无用背景时，$\Delta_t \to 0$。由离散化公式 $\bar{A} = \exp(\Delta_t A)$ 可知，此时 $\bar{A} \to I$ 且 $\bar{B} \to 0$，导致隐状态更新变为 $h_t \approx I h_{t-1} + 0 \cdot x_t = h_{t-1}$，这就是“遗忘当前，记住历史”。反之，$\Delta_t$ 变大则将当前新特征写入。

- **丢失微小点怎么办**：这是架构硬伤。工程上引入**混合架构**：在 Mamba 外部并行一个高频异常检测分支 $f_{anomaly}(x_t)$。其特征直接走残差连接 (Residual Connection) 融合到输出端：

  $$y_t = C h_t + \text{ReLU}(f_{anomaly}(x_t))$$

  保证一闪而过的关键点（如出血点）直接 Bypass 绕过 Mamba 的状态压缩。

### 12. 如果是Occlusion导致的失败，能不能实现盲操？还是说系统只能挂起等医生

在真实的医疗机器人中，**绝对不允许纯视觉盲操**。

如果发生严重遮挡，视觉 Encoder 的置信度分数会锐减。设视觉动作预测置信度为 $c_{vis} = \max_a P(a | o_{occluded})$，置信度阈值为 $\gamma$。

当 $c_{vis} < \gamma$ 时，系统必须降级，依赖末端执行器的六维力矩反馈 $F_{ext}$（力控模式）。若在此状态下 $\exists \|F_{ext}\| > \tau_{safe}$，必须立即执行安全挂起策略 $a_{suspend}$（如沿当前器械轴线后撤一小段安全距离并锁死关节），发出警报交由医生接管（Supervised Autonomy）。

### 13. 仿真环境里的组织力学参数（如杨氏模量）和活体猪差异极大，你是怎么做对齐的

- **域随机化 (Domain Randomization)**：在仿真中，将组织的力学参数集合 $\Phi$（如杨氏模量 $E$、泊松比 $\nu$）设为宽泛的均匀分布 $\Phi_{sim} \sim \mathcal{U}(\Phi_{min}, \Phi_{max})$。强迫控制策略 $\pi_\theta$ 在训练时对未知的力学参数保持鲁棒。

- **在线系统辨识 + 残差控制 (Online System ID + Residual Policy)**：在活体操作时，利用实时的动作 $a_t$ 和反馈力 $F_t$，在线推测当前组织的隐式力学表征 $z_{phy} = \phi(a_{t-k:t}, F_{t-k:t})$。然后使用一个残差策略网络 $\pi_{res}$ 补偿 Sim-to-Real 的 Gap：

  $$a_{real} = \pi_{sim}(o_t) + \pi_{res}(o_t, z_{phy}, F_t)$$

### 14. 大家都知道 Mamba 的状态压缩是线性递归，如果你在手术进行到第 2 小时时，突然出现了一个在训练集里从未出现的‘组织大面积塌陷’（OOD 场景），Mamba的Hidden State会不会因为‘历史记忆过重’产生认知惯性，导致它强行把当前的异常状态拟合到过去的正常轨迹里

是的，会产生认知惯性。因为 $h_{t-1}$ 积累了极强的正常先验，而输入端门控 $\Delta_t$ 对 OOD 特征 $x_{ood}$ 无法产生合理的响应，导致模型被动地“顺着历史往下走”。

**应对策略**：引入系统级的**认知不确定性估计 (Uncertainty Estimation)**。可以监控视觉 Encoder 的重建误差：

$$E_{recon} = \| o_t - \text{Decoder}(\text{Encoder}(o_t)) \|_2^2$$

如果 $E_{recon} > \epsilon_{threshold}$，说明当前图像流形不在训练集内（OOD），直接触发硬件级熔断，而非依靠 Mamba 的内部权重去强行拟合。

### 15. 动物上的临床验证它真正的成功率大概是能到多少？

在目前的学术界水平（如 ICRA/IROS 的 SOTA 论文中），定义子任务的成功率 $SR$ 为：

$$SR = \frac{1}{N} \sum_{i=1}^N \mathbb{I} \left( d(S_{end}^{(i)}, S_{goal}) < \epsilon \right)$$

其中 $N$ 是试验总数，$\mathbb{I}$ 是指示函数，$d$ 是距离度量，$\epsilon$ 是任务容差。

对于特定受限单一子任务（固定路径切割、打结），活体猪上的成功率通常在 **70% - 85%** 之间。面对全流程、强动态、伴随出血的复杂手术，完全自主的成功率极低，目前依然是“医生主导、系统辅助”的监督自主形态。

### 16. 手撕：1.一根木棍折成三段能构成三角形的概率？2.给你一个由 '1'（陆地）和 '0'（水）组成的的二维网格，请你计算网格中岛屿的数量。

**1. 一根木棍折成三段能构成三角形的概率**

设木棍总长为 1，折成三段的长度分别为 $x, y, z$。满足以下限制：

$$x > 0, \quad y > 0, \quad z > 0$$

$$x + y + z = 1$$

构成三角形的充要条件是任意两边之和大于第三边（等价于任意一边小于 0.5）：

$$x < 0.5$$

$$y < 0.5$$

$$z = 1 - x - y < 0.5 \implies x + y > 0.5$$

在 $x-y$ 二维坐标系中，总样本空间为满足 $x > 0, y > 0, x + y < 1$ 的直角三角形，面积为 $S_{total} = \frac{1}{2} \times 1 \times 1 = \frac{1}{2}$。

满足构成三角形条件的可行域是顶点为 $(0.5, 0), (0, 0.5), (0.5, 0.5)$ 的内部小三角形，其面积为 $S_{valid} = \frac{1}{2} \times 0.5 \times 0.5 = \frac{1}{8}$。

因此，概率为几何概率：

$$P = \frac{S_{valid}}{S_{total}} = \frac{1/8}{1/2} = 25\%$$

**2. 岛屿数量 (LeetCode 200)**

核心考察深度优先搜索（DFS）。



```Python
def numIslands(grid):
    if not grid:
        return 0
    
    count = 0
    rows, cols = len(grid), len(grid[0])
    
    def dfs(r, c):
        # 边界检查及是否为水的判断
        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] == '0':
            return
        # 标记已访问（原地修改为'0'以节省空间）
        grid[r][c] = '0'
        # 深度优先搜索四个方向
        dfs(r+1, c)
        dfs(r-1, c)
        dfs(r, c+1)
        dfs(r, c-1)
        
    for i in range(rows):
        for j in range(cols):
            # 找到陆地起点，发起一次 DFS 连通分量遍历
            if grid[i][j] == '1':
                dfs(i, j)
                count += 1
                
    return count
```

### 17. 你能列一下你的那个数学方程吗？

**1. Mamba 依赖的连续状态空间模型 (SSM) 核心方程**

$$h'(t) = A h(t) + B x(t)$$

$$y(t) = C h(t)$$

- $t$：连续时间步。
- $x(t) \in \mathbb{R}$：一维输入信号。
- $h(t) \in \mathbb{R}^n$：连续系统的 $n$ 维隐含状态向量。
- $A \in \mathbb{R}^{n \times n}$：状态转移矩阵。
- $B \in \mathbb{R}^{n \times 1}$：输入投影矩阵。
- $C \in \mathbb{R}^{1 \times n}$：输出投影矩阵。
- $y(t) \in \mathbb{R}$：系统输出信号。

**2. Mamba 的零阶保持器 (ZOH) 离散化过程**

处理离散 Token 需要引入依赖于输入的动态步长参数 $\Delta_t \in \mathbb{R}$ 进行离散化。

离散化后的状态递推公式为：

$$h_t = \bar{A} h_{t-1} + \bar{B} x_t$$

$$y_t = C h_t$$

离散化参数的严格推导：

$$\bar{A} = \exp(\Delta_t A)$$

$$\bar{B} = (\Delta_t A)^{-1}(\exp(\Delta_t A) - I) \cdot \Delta_t B$$

- $x_t$：第 $t$ 步的离散输入 Token。
- $h_t$：第 $t$ 步的离散隐含状态。
- $\bar{A}$：离散化后的状态转移矩阵（决定保留多少历史）。
- $\bar{B}$：离散化后的输入投影矩阵（决定吸纳多少新输入）。
- $I$：单位矩阵。

**3. Diffusion 模型逆向去噪采样方程**

$$p_\theta(x_{t-1} | x_t) = \mathcal{N}(x_{t-1}; \mu_\theta(x_t, t), \Sigma_\theta(x_t, t))$$

- $\theta$：神经网络（如 U-Net 或 Transformer）的可学习参数。
- $x_t$：在扩散过程第 $t$ 步的带噪数据（在具身控制中通常是带噪的动作轨迹）。
- $x_{t-1}$：去噪一步后的数据状态。
- $\mathcal{N}$：高斯分布。
- $\mu_\theta(x_t, t)$：由网络预测的均值（指导去噪方向，通常通过预测噪声 $\epsilon_\theta$ 或直接预测无噪动作 $x_0$ 算得）。
- $\Sigma_\theta(x_t, t)$：方差矩阵（控制生成过程的随机性与多样性）。