# 前端说明

这里是 OpenClaw 的静态网页前端。

## 文件

- `index.html`
- `styles.css`
- `app.js`

## 使用方式

你可以直接在浏览器里打开 `index.html`，也可以通过仓库根目录的 `main.py`
启动一个本地 FastAPI 服务后访问网页。

默认状态是 mock 模式。以后要接真实后端时，可以通过顶部的 `API` 按钮设置后端基址。
前端预期会调用：

- `POST /api/command`
- `GET /api/session/:id`
- `GET /api/session/:id/events`

## 说明

- 页面采用深色背景和高亮文字。
- 命令输入支持 `Enter` 提交，`Shift+Enter` 换行。
- 已预置常用测试命令，方便快速试用。
