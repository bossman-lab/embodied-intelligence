# OpenClaw 与飞书接入

这一章只讲接入链路，不讲 UI，也不讲后续的库存逻辑。

## 本章完成后

读者应该知道：

1. OpenClaw 读哪些配置
2. 飞书应用凭据放在哪里
3. 为什么多维表格同步要单独写一层配置

## 读取顺序

OpenClaw 的集成层会先读环境变量，再回退到本机的 `~/.openclaw/openclaw.json`。

优先级如下：

1. `OPENCLAW_FEISHU_APP_ID`
2. `OPENCLAW_FEISHU_APP_SECRET`
3. `OPENCLAW_FEISHU_NOTIFY_TARGET`
4. `OPENCLAW_FEISHU_NOTIFY_RECEIVE_ID_TYPE`
5. `OPENCLAW_FEISHU_BITABLE_APP_TOKEN`
6. `OPENCLAW_FEISHU_BITABLE_TABLE_ID`

## 需要准备什么

- 飞书开放平台里的应用凭据
- 一个可写的 OpenClaw 本机配置文件
- 已开通的多维表格权限

## 关键检查点

- 如果 `appId` 和 `appSecret` 为空，通知和同步都会失败
- 如果只配了通知目标，没有配多维表格的 `appToken/tableId`，库存同步仍然不会启动
- 如果配置文件是 Windows 写出的 UTF-8 BOM，Python 读取 JSON 可能失败，建议写成无 BOM UTF-8

## 对应代码

- [integrations.py](./tuntunclaw/integrations.py)
- [workflow_hooks.py](./tuntunclaw/workflow_hooks.py)
- [main.py](./tuntunclaw/main.py)
