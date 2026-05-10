import os
import re
import platform
import subprocess
from pathlib import Path

def setup_mujoco_path():
    """
    自动处理中文路径问题：
    如果当前路径包含中文，则在用户家目录创建英文软链接并切换 cwd。
    """
    project_root = Path.cwd().resolve()
    # 强制使用英文名，建议与你的教程主题相关
    link_path = Path.home() / "lerobot-mujoco-tutorial"

    # 检测中文正则
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', str(project_root)))

    if not has_chinese:
        # 如果没有中文且当前不是链接路径，直接返回
        if "lerobot-mujoco-tutorial" not in str(project_root):
            return project_root

    # 如果已经是在链接路径下运行，无需重复操作
    if project_root == link_path:
        return project_root

    if not link_path.exists():
        sys_name = platform.system()
        if sys_name == "Windows":
            cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(project_root)]
            subprocess.run(cmd, capture_output=True)
        elif sys_name in ("Linux", "Darwin"):
            link_path.symlink_to(project_root, target_is_directory=True)
    
    # 切换进程的工作目录
    os.chdir(link_path)
    return link_path

# --- 关键点：在模块导入时自动运行 ---
current_path = setup_mujoco_path()
print(f"[Env Info] 运行环境已就绪，当前工作目录: {current_path}")