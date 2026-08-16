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
