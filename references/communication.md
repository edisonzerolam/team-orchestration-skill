# Communication（通信协议）
> **重建说明（v3.5）**：本文件 v3.4 曾因 GBK→UTF-8 误转产生乱码（全文 `?` 替字 + `鈥?`/`鈹?` 错位）。现以 marketplace 完好英文旧版（`skills/agent-team-orchestration/references/communication.md`）为基**重建中文对照版**（乱码版与旧版内容一致，无新增概念）。编码 UTF-8，行尾 CRLF。

多智能体如何协调：同步 vs 异步、spawn vs send、产物共享（How agents coordinate: sync vs async, spawning vs messaging, and artifact sharing）。

## 通信渠道（Communication Channels）

### Shared Files（共享文件 · 主通道 · 异步）

默认通信方式。持久、可审计、无时序依赖。

```
/shared/
├── specs/          — Requirements, research, analysis
├── artifacts/      — Build outputs, deliverables
├── reviews/        — Review notes and feedback
├── decisions/      — Architecture and product decisions
```

**用于：** 交付物、规格、评审、决策——任何其他 agent 之后需要找到的东西。

### Task Comments（任务评论 · 异步）

挂在具体任务上，按时间记录进度。

**用于：** 状态更新、阻塞说明、handoff 消息、评审反馈。

### sessions_send（同步 · 紧急）

直发消息给运行中的 agent 会话，会打断其当前工作。

**用于：**
- 紧急优先级变更（"放下一切，处理严重 bug"）
- 阻塞进度的快速提问（"X 功能在范围内吗？"）
- 等不了任务评论流转的协调

**不要用于：**
- 例行更新（用任务评论）
- 交付产物（用共享文件）
- 需要稍后引用的信息（消息是易失的）

## Spawn vs Send

### 满足以下条件时 Spawn 新子代理：
- 任务自包含、输入输出明确
- 需要隔离（工作不应影响其他运行中的会话）
- 任务需要不同模型或能力集
- 在做并行化（多个独立任务同时进行）

### 满足以下条件时 Send 到已有会话：
- agent 已在处理相关上下文
- 只需要快速回答，而非完整任务执行
- 工作是进行中内容的少量追加

**默认 Spawn。** 更干净。Send 是例外。

## Spawn Prompt 模板

每次 spawn 都包含：

```markdown
## Task: [Title]
**Task ID:** [ID]
**Role:** [What this agent is]
**Priority:** [High/Medium/Low]

### Context
[What the agent needs to know]

### Deliverables
[Exactly what to produce]

### Output Path
[Exact directory/file path for artifacts]

### Handoff
When complete:
1. Write artifacts to [output path]
2. Comment on task with handoff summary
3. Include: what was done, how to verify, known issues
```

**关键字段：**
- **Output Path** — 缺失会丢失工作，必须指定。
- **Handoff instructions** — 明确告诉 agent 如何发出完成信号。

## 产物约定（Artifact Conventions）

### 命名
```
/shared/artifacts/[task-id]-[short-name]/
/shared/specs/[date]-[topic].md
/shared/decisions/[date]-[title].md
/shared/reviews/[task-id]-review.md
```

### 规则
- 所有交付物放 `/shared/` — 绝不写入 agent 个人工作区
- 多文件输出每个任务一个目录
- 目录含 3+ 文件时在顶部放简短 README/摘要
- 原地覆盖旧版本 — 不要创建 v2、v3 副本

## 避免通信失败（Avoiding Communication Failures）

- **静默 agent：** 若 agent 在预期时间内未评论，视为卡住。检查或重启任务。
- **产物丢失：** 任务完成后总是核验输出路径存在。agent 有时会写错目录。
- **上下文断裂：** spawn 时带上 agent 所需的全部上下文。不要假设它能读到其他 agent 会话或近期对话。共享文件是桥梁。
- **消息时序：** `sessions_send` 仅在目标会话活跃时有效。不确定时，改 spawn 新会话。

---

## 脱敏占位规范（Data Redaction · v3.9 · 吸收 grok-bot redaction）

> 来源：grok-bot `shouldRedact.js` → `formatRedacted(fieldName) → [redacted:field_name]`

### 标准占位格式

所有被脱敏的敏感字段使用统一格式：`[redacted:field_name]`

| 字段 | 格式 | 示例 |
|------|------|------|
| 手机号 | `[redacted:phone]` | 13800138000 → `[redacted:phone]` |
| 姓名 | `[redacted:name]` | 张三 → `[redacted:name]` |
| 地址 | `[redacted:address]` | 北京市xxx → `[redacted:address]` |
| 证件号 | `[redacted:id_card]` | 110101xxxx → `[redacted:id_card]` |
| 密钥/Token | `[redacted:secret]` | sk-xxxx → `[redacted:secret]` |
| 内部渠道 | `[redacted:channel]` | 客户A → `[redacted:channel]` |

### 规则

- 占位符必须包含字段名，以便人工 review 识别遗漏。
- 禁止使用 `[脱敏]`、`[隐藏]`、`[***]` 等无信息量占位——无法区分是哪个字段。
- 对外交付物（deliverables/）在发布前必须扫描是否仍有未脱敏的敏感字段。
- 子代理产出的报告中如涉及客户数据，必须主动脱敏后再上传。

---

## 错误双视图协议（Error Dual-View · v3.9 · 吸收 grok-bot 工具系统）

> 来源：grok-bot 工具系统 `risks_for_model` vs `risks_for_user` 分离

### 原则

模型拿**可执行提示**，人拿**诊断细节**。二者分离，避免模型收到无法解析的技术错误陷入重试风暴。

### 格式

```
## 错误摘要（供模型处理）
- 错误类型: [tool_not_found / permission_denied / rate_limited / timeout / format_error]
- 可重试: [yes/no]
- 建议动作: [retry / ask_user / fallback / abort]
- 重试退避: delay_ms = base * 2^attempt (base=5000, max_attempts=3)

## 错误详情（供人工诊断）
- 原始错误: <raw_error_message>
- 错误来源: <tool_name>
- 上下文: <what_was_being_done>
```

### 错误类型 → 动作映射

| 错误类型 | 可重试 | 建议动作 | 说明 |
|---------|--------|---------|------|
| `rate_limited` | yes | retry (退避) | 等待后重试 |
| `timeout` | yes | retry (退避) | 短暂超时重试 |
| `transient_error` | yes | retry (退避) | 临时错误 |
| `permission_denied` | no | ask_user | 需人工授权 |
| `tool_not_found` | no | fallback | 尝试替代工具 |
| `format_error` | no | retry (修正) | 修正输入格式 |
| `fatal` | no | abort | 终止任务 |

---

## 退避策略（Exponential Backoff · v3.9 · 吸收 grok-bot 韧性细节）

> 来源：grok-bot `backoff-scheduler.js` — 指数退避 `delay = base × 2^n`

### 标准退避参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `base_delay_ms` | 5000 | 首次重试等待时间 |
| `max_attempts` | 3 | 最大重试次数 |
| `jitter` | 0 | 默认无抖动（可选 [0,1]） |
| `max_delay_ms` | 40000 | 最大等待时间上限 |

### 公式

```
delay_ms = min(base_delay_ms × 2^attempt, max_delay_ms)
```

- attempt=0: 5000ms | attempt=1: 10000ms | attempt=2: 20000ms | attempt=3: 40000ms (capped)

### 适用场景

- 网络请求超时（HTTP 503/504）、API rate limit（HTTP 429）
- 数据库连接池短暂不可用、子代理 spawn 失败（短暂资源争用）

### 不适用场景

- 权限被拒（不会随时间改变）、参数格式错误（重试无意义）、模型输出截断（需换策略）

---

## 大输出 Spill 落盘约定（Large Output Spill · v3.9 · 吸收 grok-bot MCP 健壮性）

> 当单次工具输出 >50KB 时，写入 `deliverables/spill/` 文件，消息中仅保留引用路径。

### 规则

- **阈值**：单次输出 >50KB 时触发 spill。
- **路径**：`deliverables/spill/[task_id]-[timestamp]-[tool_name].md`
- **引用格式**：
  ```
  [输出过大，已 spill 至 deliverables/spill/[filename]（X KB）]
  摘要: <前 500 字符>
  ```
- **清理**：spill 文件在任务完成 7 天后自动过期（由 checkpoint 清理器处理）。

### 适用工具

- `Bash` 长输出（编译日志、测试报告、代码审计）
- `Read` 大文件（>50KB 的 JSON/MD）
- `Agent` 长报告（>50KB 的子代理返回）
