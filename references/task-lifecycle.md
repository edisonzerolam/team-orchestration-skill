# Task Lifecycle（任务生命周期）
> **重建说明（v3.5）**：本文件 v3.4 曾因 GBK→UTF-8 误转产生乱码（全文 `?` 替字 + `鈫?`/`鈥?` 错位）。现以 marketplace 完好英文旧版（`skills/agent-team-orchestration/references/task-lifecycle.md`）为基**重建中文对照版**，并把乱码版中新增的状态/概念（**Pre-task Discussion / Consensus Check**）回移植进重建版。内容为中文说明 + 英文保留字段，编码 UTF-8，行尾 CRLF。

任务状态、状态迁移、评论约定与决策留痕（Task states, transitions, comment conventions, and decision logging）。

## 状态（States）

```
Inbox → Pre-task Discussion → Assigned → In Progress → Review → Consensus Check → Done | Failed
```

| State | 含义 | Owner（负责方） |
|-------|------|----------------|
| **Inbox** | 新任务，未分配 | Orchestrator |
| **Pre-task Discussion** | 执行前专家讨论任务理解与策略（复杂度达标或声明 `// full-discussion` 时启用） | Orchestrator（facilitator） |
| **Assigned** | 已选定执行者，尚未开始 | Orchestrator |
| **In Progress** | 执行者工作中 | Assigned agent |
| **Review** | 工作完成，等待核验 | Reviewer |
| **Consensus Check** | 交付前全体专家核验最终结论 | Orchestrator + All experts |
| **Done** | 已核验并交付 | Orchestrator |
| **Failed** | 记录原因后放弃 | Orchestrator |

## 迁移规则（Transition Rules）

**Orchestrator 触发：**
- Inbox → Pre-task Discussion（为对齐 spawn 专家，复杂度阈值达标或声明 `// full-discussion` 时启用）
- Pre-task Discussion → Assigned（达成共识，以确认的执行计划 spawn builder）
- Assigned → In Progress（spawn 执行者或下发任务）
- Review → Consensus Check（reviewer 通过，触发专家共识核验）
- Consensus Check → Done（共识达成，交付用户）
- Consensus Check → In Progress（存在未解决的异议，退回 builder）
- Any state → Failed（记录原因）

**Agents 触发：**
- In Progress → Review（提交产物并附 handoff 评论）

**Reviewers 触发：**
- Review → In Progress（退回并附反馈，执行者必须处理）
- Review → Done（通过，由 orchestrator 确认）

**Never skip Review.** 琐碎任务可由 orchestrator 直接放行，但必须留痕说明。

## 评论约定（Comment Conventions）

每次状态变更都要有评论。格式：

```
[Agent] [Action]: [Details]
```

### 必填评论：

**Pre-task discussion（Orchestrator 开场）：**
```
[Orchestrator] Pre-task Discussion: Task complexity={HIGH/MEDIUM/LOW}. Spawning {N} experts for alignment.
- Topic: {task}
- Key question: {main question for experts}
- Time budget: 5min per expert opinion, 10min debate round
```

**专家意见提交：**
```
[Expert-{id}] Opinion: {domain} perspective on {task}
- View on approach: ...
- Key risks: ...
- Suggested angle: ...
```

**共识达成：**
```
[Orchestrator] Consensus: Agreed on {execution plan}. Proceeding to Assigned.
```

**Consensus Check（Orchestrator 发起）：**
```
[Orchestrator] Consensus Check: Final report ready at {path}. Experts please confirm: ✔ Agree / ⚠ Concern / 🚫 Object.
```

**专家共识回应：**
```
[Expert-{id}] Consensus: {✔/⚠/🚫} — {reason if concerned/objecting}
```

**开始工作：**
```
[Builder] Starting: Picking up auth module. Questions: Should rate limiting be per-user or per-IP?
```

**遇到阻塞：**
```
[Builder] Blocked: Need API credentials for the payment gateway. Who has access?
```

**提交评审：**
```
[Builder] Handoff: Auth module complete at /shared/artifacts/auth/.
- Added JWT validation middleware
- Tests at /shared/artifacts/auth/tests/
- Run `npm test -- --grep auth` to verify
- Known issue: refresh token rotation not implemented (out of scope per spec)
- Next: Reviewer checks error handling paths
```

**评审反馈：**
```
[Reviewer] Feedback: Two issues found.
1. Missing input validation on email field — SQL injection risk
2. Error messages expose internal paths in production mode
Returning to builder. Fix both, then resubmit.
```

**完成：**
```
[Reviewer] Approved: All issues addressed. Auth module ready to ship.
```

**失败：**
```
[Orchestrator] Failed: Deprioritized — superseded by new auth provider integration. Preserving spec at /shared/specs/auth-v1.md for reference.
```

## 决策留痕（Decision Logging）

任务执行期间产生的架构/产品决策写入共享 decisions 目录。

```markdown
# Decision: [Title]
**Date:** YYYY-MM-DD
**Author:** [Agent]
**Status:** Proposed | Accepted | Rejected
**Task:** [Task ID if applicable]

## Context
Why this decision came up.

## Options Considered
1. Option A — tradeoffs
2. Option B — tradeoffs

## Decision
What was chosen and why.

## Consequences
What changes as a result.
```

**何时留痕：**
- 在两个有效架构方案之间做选择
- 实现期间修改规格
- 将某需求判定为不可行
- 任何未来 agent 会问"当时为何这样做"的选择

## 多步任务工作流（Multi-Step Task Workflows）

复杂任务拆分为子任务，跟踪父子关系：

```
Task #12: Build user dashboard
  ├── #12a: Write spec (Assigned: Spec writer)
  ├── #12b: Review spec (Assigned: Builder — feasibility check)
  ├── #12c: Build frontend (Assigned: Builder)
  ├── #12d: Build API endpoints (Assigned: Builder)
  └── #12e: Integration test (Assigned: Reviewer)
```

orchestrator 跟踪父任务，仅当全部子任务完成才标记 Done。
