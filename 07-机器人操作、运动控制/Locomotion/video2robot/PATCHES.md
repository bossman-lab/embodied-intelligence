# Patch 应用说明

本文档用于在同基线上复现当前改动。

## 基线 commit（请务必一致）

- 主仓库（video2robot）：`030f3410dac3cb15a2570376dca6a0f46c2d158c`
- `third_party/PromptHMR`：`4f8915c5b9603344c56e95fadb9a01a23ba2272d`
- `third_party/GMR`：`069b4fd48f440e813b2b4d69255c70f53e5f83fb`

## patch 文件

- `patches/main.patch`
- `patches/prompthmr.patch`
- `patches/gmr.patch`

## 应用步骤

```bash
git submodule update --init --recursive

git apply patches/main.patch
git -C third_party/PromptHMR apply ../../patches/prompthmr.patch
git -C third_party/GMR apply ../../patches/gmr.patch
```

## 验证

```bash
git status --short
git -C third_party/PromptHMR status --short
git -C third_party/GMR status --short
```

## 若应用失败

- 先确认基线 commit 是否一致
- 使用 `git apply --reject` 生成 `.rej` 后手动处理冲突
