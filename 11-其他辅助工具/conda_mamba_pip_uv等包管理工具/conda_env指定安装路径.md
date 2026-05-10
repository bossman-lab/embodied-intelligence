

### 方法一：配置 `envs_dirs`（最推荐）

可以告诉 Conda：“请把 `/root/gpufree-data/envs` 也当作存放环境的地方”。这样就可以直接用名字来创建和激活环境，而文件实际存储在数据盘上。

**操作步骤：**

1.  **添加路径到 Conda 配置**：
    ```bash
    # 将数据盘目录添加到环境搜索路径的“最前面”
    conda config --add envs_dirs /root/gpufree-data/envs
    ```

2.  **验证配置**：
    ```bash
    conda info
    # 检查输出中的 "envs directories"
    # 确保 /root/gpufree-data/envs 排在第一位
    ```

3.  **像往常一样使用名字创建环境**：
    由于数据盘路径排在第一位，Conda 会默认把新环境创建在那里。
    ```bash
    conda create -n openpi-server python=3.11 -y
    ```

4.  **像往常一样用名字激活**：
    ```bash
    conda activate openpi-server
    ```

这样既解决了存储空间问题（实际在数据盘），又保留了简短的命令体验。

---

### 方法二：设置 Shell 别名 (Alias)

如果不想修改 Conda 配置，可以在的 `~/.bashrc` 中加一行别名：

1.  编辑 `.bashrc`：
    ```bash
    echo 'alias act_openpi="conda activate /root/gpufree-data/envs/openpi-server"' >> ~/.bashrc
    source ~/.bashrc
    ```
2.  以后只需要输入 `act_openpi` 即可激活。

**总结**：推荐使用**方法一**，这是一劳永逸的解决方案，以后创建其他大环境也可以自动存到数据盘。