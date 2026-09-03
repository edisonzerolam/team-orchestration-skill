# Pre-Approved Operations（预批准操作清单）
> **版本**：v3.9.1-dsh（2026-09-03）
> **来源**：吸收 grok-bot 沙箱纪律 + 审批四层模型
> **目标**：消除审批疲劳——只读操作免人工确认，破坏性操作强制审批

## 沙箱分级

| 等级 | 标识 | 说明 | 是否需要审批 |
|------|------|------|-------------|
| **READONLY** | `S1` | 只读操作：read、grep、list、search | 无需审批 |
| **READWRITE** | `S2` | 写操作：write、edit、create | 无需审批（工作区内） |
| **NETWORK** | `S3` | 网络操作：HTTP、API、fetch | 无需审批（白名单域名） |
| **DESTRUCTIVE** | `S4` | 破坏性操作：delete、rm、truncate | **强制审批** |

## READONLY 白名单（免审批）

```
Read, Bash (只读参数: cat, grep, find, ls, wc, head, tail),
Agent (只读子代理), AskUserQuestion, ReadSessionContext
```

## READWRITE 白名单（免审批，仅限工作区）

```
Write, Edit, TodoWrite, Skill, CronCreate, CronUpdate
```

## NETWORK 白名单（免审批，仅限白名单域名）

```
WebFetch (公开页面), gh (GitHub API), npm/pip install (公共源)
```

## DESTRUCTIVE 操作（强制审批）

| 操作 | 审批条件 | 降级策略 |
|------|---------|---------|
| `rm -rf` 删除目录 | 必须人工确认 | 先 mv 到 trash/ |
| `git reset --hard` | 必须人工确认 | 先 git stash |
| `DROP TABLE` / `DELETE FROM` | 必须人工确认 | 先备份 |
| 发布/推送（git push, npm publish） | 必须人工确认 | 先 dry-run |
| 对外消息（baoyu-post-to-*） | 必须人工确认 | 先生成草稿 |
| 凭据/密钥操作 | 必须人工确认 | 先检查是否有替代方案 |

## 降级策略（无 helper 时）

> grok-bot 沙箱纪律："显式失败优于静默降级"——无 helper 即硬失败，绝不静默放行。

1. **READONLY 操作**：无 helper 时尝试替代工具（如 Bash cat → Read）。
2. **READWRITE 操作**：无 helper 时降级为 READONLY（只读模式），报告无法写入。
3. **NETWORK 操作**：无 helper 时记录失败，不重试。
4. **DESTRUCTIVE 操作**：无 helper 时**硬失败**，`ask_user_question` 确认，不可自动降级。

## 审批疲劳消除原则

- **90% 的操作**（READONLY + READWRITE 工作区内）应免人工确认。
- **仅 10% 的操作**（DESTRUCTIVE + 对外 + 凭据）需要人工确认。
- 审批确认必须是**显式的**（`ask_user_question`），不接受隐式同意。
