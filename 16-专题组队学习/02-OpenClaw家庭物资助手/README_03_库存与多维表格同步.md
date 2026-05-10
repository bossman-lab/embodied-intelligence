# 库存与多维表格同步

这一章把家庭物资助手的库存状态同步到飞书多维表格。读者不需要先理解完整机械臂流程，只需要知道库存快照如何生成、如何写入飞书表格，以及失败时先检查哪些配置。

## 本章完成后

读者应该能够：

1. 理解家庭物资库存快照的数据结构
2. 创建一张用于同步的飞书多维表格
3. 配置 `appToken` 和 `tableId`
4. 手动触发一次同步并检查结果

## 表格字段

建议多维表格包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `SKU` | 物资唯一标识 |
| `物品` | 展示名称 |
| `剩余数量` | 当前库存数量 |
| `阈值` | 低库存阈值 |
| `建议补货` | 建议补货数量 |
| `单位` | 件、瓶、块等 |
| `位置` | 家庭内存放位置 |
| `状态` | 正常或低库存 |
| `购买链接` | 采购入口 |
| `下单链接` | OpenClaw 生成的下单入口 |
| `更新时间` | 最近更新时间 |

## 配置位置

多维表格同步需要两个值：

```env
OPENCLAW_FEISHU_BITABLE_APP_TOKEN=
OPENCLAW_FEISHU_BITABLE_TABLE_ID=
```

如果不想写环境变量，也可以放到 `~/.openclaw/openclaw.json` 的 `channels.feishu.inventoryBitable` 中。

## 同步入口

本专题已经在同级目录提供 `tuntunclaw` 代码。库存同步入口对应：

- [integrations.py](./tuntunclaw/integrations.py)
- [workflow_hooks.py](./tuntunclaw/workflow_hooks.py)
- [main.py](./tuntunclaw/main.py)

## 常见问题

- `feishu bitable sync not configured`：通常是 `appToken/tableId` 没有配置，或配置文件没有被程序读到
- `Access denied`：通常是飞书应用没有开通多维表格权限
- Python 读不到 `openclaw.json`：检查文件是否带 UTF-8 BOM，Windows 下建议写成无 BOM UTF-8
