**GitHub 出于安全考虑，自 2021 年 8 月 13 日起，在对 Git 操作进行身份验证时，不再支持使用账户密码**。

1. **可以用 API 吗？**
   - 这里的 "API" 应该指的是 **个人访问令牌（Personal Access Token, PAT）**。答案是**肯定的**，这正是 GitHub 推荐的替代密码的方式。当你通过 HTTPS URL (例如 `https://github.com/user/repo.git`) 克隆、推送或拉取代码时，在提示输入密码的环节，输入你生成的 PAT 即可。
2. **如何设置 API（PAT）为环境变量？**
   - 将 PAT 设置为环境变量主要用于**自动化脚本或在程序中调用 GitHub API**的场景，而不是用于日常的 `git push/pull` 命令。对于日常的命令行操作，更推荐使用 **Git 凭证管理器 (Credential Manager)**。

------



### 方法一：推荐方式 - 使用个人访问令牌 (PAT) 配合 Git 凭证管理器



这是最适合日常在自己电脑上进行 `git` 操作的方法。你只需要生成一个 PAT，然后在第一次需要验证时输入一次，之后 Git 就会记住它。



#### 第 1 步：生成个人访问令牌 (PAT)



1. 登录你的 GitHub 账户。
2. 点击右上角的头像，选择 **Settings**。
3. 在左侧菜单中，滚动到底部，选择 **Developer settings**。
4. 在左侧菜单中，选择 **Personal access tokens** -> **Tokens (classic)**。
5. 点击 **Generate new token**，然后选择 **Generate new token (classic)**。
6. **Note (备注)**：给你的 Token 起一个容易识别的名字，比如 "My Laptop Git"。
7. **Expiration (过期时间)**：为了安全，建议设置一个过期时间，比如 30 天或 90 天。
8. **Select scopes (选择权限)**：这是最重要的一步。对于代码仓库的克隆、拉取、推送等操作，**必须勾选 `repo` 这个大项**。它包含了所有与仓库相关的权限。
9. 点击页面底部的 **Generate token**。
10. **立即复制生成的 Token！** 这个 Token 只会显示一次，页面刷新后就再也看不到了。请把它保存在一个安全的地方。



#### 第 2 步：在命令行中使用



现在，当你执行 `git push` 或 `git pull` 等需要验证的命令时：

- **Username (用户名)**：输入你的 GitHub 用户名。
- **Password (密码)**：**粘贴你刚刚复制的个人访问令牌 (PAT)**。

大多数操作系统（Windows, macOS, Linux）的 Git 都会自动使用凭证管理器（Credential Manager）来缓存你的凭证。输入一次成功后，短期内就不需要再次输入了。

------



### 方法二：为脚本或特殊用途设置环境变量



如果你正在编写一个需要和 GitHub API 交互的脚本（例如，一个自动创建仓库的脚本），将 PAT 设置为环境变量是一个很好的做法。

**注意：** 这种方法不推荐用于日常的 `git` 命令，因为凭证管理器更安全、更方便。



#### 在 Linux / macOS 上设置



你可以将环境变量设置在 `~/.bashrc`, `~/.zshrc` 或 `~/.profile` 文件中，这样每次打开新的终端时它都会自动生效。

1. 打开你的 shell 配置文件，例如 `~/.bashrc`：

   Bash

   ```
   nano ~/.bashrc
   ```

2. 在文件末尾添加以下行，将 `your_personal_access_token` 替换成你自己的 PAT：

   Bash

   ```
   export GITHUB_TOKEN="your_personal_access_token"
   ```

   **强烈建议**使用 `ghp_` 或 `ghs_` 开头的完整 Token。

3. 保存并关闭文件。然后执行以下命令使配置立即生效：

   Bash

   ```
   source ~/.bashrc
   ```

4. 验证是否设置成功：

   Bash

   ```
   echo $GITHUB_TOKEN
   ```

   如果能看到你的 Token，说明设置成功。



#### 在 Windows 上设置



1. 在搜索栏中搜索 "环境变量"，然后选择 "编辑系统环境变量"。
2. 在弹出的 "系统属性" 窗口中，点击 "环境变量..." 按钮。
3. 在 "用户变量" 或 "系统变量" 区域（推荐 "用户变量"），点击 "新建..."。
4. **变量名**：`GITHUB_TOKEN`
5. **变量值**：粘贴你的个人访问令牌 (PAT)。
6. 连续点击 "确定" 关闭所有窗口。
7. **重新打开**一个新的命令提示符 (CMD) 或 PowerShell 窗口，新的环境变量才会生效。
8. 验证是否设置成功：
   - 在 CMD 中：`echo %GITHUB_TOKEN%`
   - 在 PowerShell 中：`echo $env:GITHUB_TOKEN`

------



### 总结



- **日常使用 `git` 命令**：选择**方法一**。生成一个 PAT，在 Git 提示输入密码时粘贴它即可。Git 的凭证管理器会自动为你记住。
- **编写脚本或程序调用 API**：选择**方法二**。将 PAT 设置为环境变量，然后在代码中读取这个环境变量来使用。
- **另一种选择：SSH**：除了 HTTPS + PAT，你还可以使用 SSH 协议。这种方式需要你生成 SSH 密钥对，并将公钥添加到你的 GitHub 账户中。设置好之后，你将不再需要输入任何用户名或密码/Token。这也是非常流行和安全的一种方式。