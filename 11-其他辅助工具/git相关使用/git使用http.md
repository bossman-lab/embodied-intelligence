

### 方法一：强制将所有 git 请求转换为 HTTPS（推荐，最快）

如果不想手动修改配置文件，可以直接运行这条全局配置命令。它会告诉 Git：每当遇到 `git@github.com:` 的地址时，自动替换为 `https://github.com/`。

在的终端运行：

Bash

```
git config --global url."https://github.com/".insteadOf git@github.com:
```

运行完上述命令后，再次重试的更新命令：

Bash

```
git submodule update --init --recursive
```

> **注意**：如果该子模组是**私有仓库**（Private Repo），Git 会提示输入 GitHub 的用户名和密码（现在的密码通常是指 **Personal Access Token**）。如果是公开仓库，则会直接下载。

------

### 方法二：手动修改 `.gitmodules` 文件

如果希望永久性地修改这个项目的配置，可以编辑项目根目录下的 `.gitmodules` 文件。

1. 编辑文件：

   使用 vim 或 nano 打开 .gitmodules：

   Bash

   ```
   vim .gitmodules
   ```

2. 修改 URL：

   找到 [submodule "policy"] 这一节，将 url 从 SSH 格式改为 HTTPS 格式。

   **修改前：**

   Ini, TOML

   ```
   url = git@github.com:shuosha/policy_training.git
   ```

   **修改后：**

   Ini, TOML

   ```
   url = https://github.com/shuosha/policy_training.git
   ```

3. 同步并更新（关键步骤）：

   修改文件后，必须运行 sync 才能让 Git 识别新的 URL，然后再更新：

   Bash

   ```
   git submodule sync
   git submodule update --init --recursive
   ```

------

### 方法三：仅修改本地 git 配置（不影响文件）

如果不想改动代码里的 `.gitmodules` 文件（以免提交上去影响别人），可以只修改 `.git/config` 文件。

1. 打开 `.git/config` 文件：

   Bash

   ```
   vim .git/config
   ```

2. 找到 `[submodule "policy"]` 部分，修改 `url` 为 `https://github.com/shuosha/policy_training.git`。

3. 保存退出，直接运行更新命令。

### 总结建议

既然在 `root@gpufree-container` 环境下，我建议直接使用 **方法一**。它不需要通过编辑器修改文件，且能立即生效解决所有子模组的类似问题。

下一步：

可以直接复制并运行这条命令，然后重试更新：

Bash

```
git config --global url."https://github.com/".insteadOf git@github.com: && git submodule update --init --recursive
```