# 前端展示与发布清单

这一章说明家庭物资助手前端应该展示什么，以及把 `tuntunclaw` 放进公开仓库前需要检查哪些文件。

## 前端展示目标

前端不需要做成完整商品后台。它的目标是让读者看到一条清楚的演示闭环：

1. 当前物资库存
2. 低库存状态
3. 飞书提醒或表格同步状态
4. 一键下单入口
5. 最近一次任务执行结果

## 前端展示区块

- 任务输入区：用于输入自然语言任务
- 执行状态区：展示 OpenClaw 任务阶段
- 库存卡片区：展示物品、数量、阈值和状态
- 飞书同步区：展示同步是否配置、是否成功
- 日志区：展示最近一次执行和错误信息

## 发布前检查

公开 `tuntunclaw` 子目录前，先检查以下内容：

- 不提交 `.env`
- 不提交 `sam_b.pt`
- 不提交 `temp/`、`trash/`、`__pycache__/`
- 不提交 `mask_*.png` 调试图
- 不提交场景编辑器：`scene_layout_editor.py` 和 `SCENE_LAYOUT_EDITOR_README.md`
- 不提交本地飞书 token、OpenAI key、机器人真实内网地址

## 可公开保留的文件

- `.env.example`
- `README.md`
- `requirements-py311.txt`
- `frontend/`
- `inventory.py`
- `integrations.py`
- `workflow_hooks.py`
- `main.py`
- `openclaw_like/`

## 验证方式

提交前运行：

```bash
git status --short
git ls-files | grep -E "sam_b.pt|\\.env$|scene_layout_editor|__pycache__|temp/|trash/"
```

第二条命令不应该输出任何内容。
