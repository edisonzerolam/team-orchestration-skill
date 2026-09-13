# 两阶段生命周期（staged 审批 / halted / escalated）· 反向吸收自 dsh-agent-teams 插件

> **版本**：v3.13（2026-09-13 · 团队 team-orchestration-mutual-absorb）。
> **来源**：本机 agent-teams 插件 v0.1.17（`~/.dsh/profiles/<profile>/node_modules/@nanmicoder/dsh-agent-teams/`）
> 的 `lib/types/types.d.ts:184–208`、`lib/quality-gates.js:779–819`（`qualityPlanningPrompt` / `describeQualityLoop`）。
> **吸收范围**：只吸收**生命周期语义**，**不吸收前端实现**（活动面板 / 形象 / cordis-tsdown 工程层）——见 `agent-teams-absorption.md` §8 修订后的边界句。

---

## 1 为什么需要它

本技能原有的起步动作是「立案后立即派发举证」。插件把这一步改成**两阶段**：立案产出的是一份**待批准的计划**，人类显式批准后才进入执行。
好处是**把最贵的人类纠错点前移到最便宜的时刻**——计划错比结论错便宜一个数量级。

---

## 2 状态字段（插件侧事实）

| 字段 | 取值 | 语义 |
|---|---|---|
| `phase` | `staged` \| `running` | 两阶段执行生命周期。**缺省 = `running`**（对 staged 机制出现之前创建的团队向后兼容） |
| `planReviewState` | `awaiting_review` \| `awaiting_feedback` | 仅 `phase=staged` 时的审查子态。缺省 = `awaiting_review`。`awaiting_feedback` 表示用户已回到对话，**主理人必须先问「要改什么」再改这份 draft**，不得自行开改 |
| `approvedAt` | 时间戳 | **仅在 staged 计划被显式批准后才写入** |
| `halted` / `haltedAt` | 布尔 / 时间戳 | 人类从对话中拉停：**团队保留在盘、成员仍可用、未完成任务被取消**，直到 resume |
| `escalated` | 布尔 | 自动裁决/修补循环撞上配置上限（**注意：不是 halt**，见 `structured-contract.md` §A7） |

`resume` 必须携带**非空 reason**（插件 `resumeTeamState(team, reason)`，`lib/quality-gates.js:560`）；插件文案明确写：
> `halted means the human stopped the team; call agent_teams_resume before creating more work. escalated means the automatic review loop hit its ceiling; that is not halt.`

---

## 3 映射到本技能（DSH 落地形态）

| 插件机制 | 本技能落地 | 落点 |
|---|---|---|
| `phase=staged` | 立案（A 阶段）产出**待批计划**，不 spawn 子代理 | 案卷 `00-立案/team-state.json` 的 `phase` 字段 |
| 人类批准 → `approvedAt` | main 用 `ask_user_question` 呈递计划（争点 / 角色 / 派数 / 预算档 / 预期产物），用户显式确认后写 `approvedAt` 并置 `phase=running` | 同上 |
| `planReviewState=awaiting_feedback` | 用户驳回计划后，**先问清要改什么再改 draft**，禁止 main 自作主张重写后再次呈递 | 同上 |
| `halted` / `haltedAt` | 用户说停 → 写 `halted=true`；未完成任务置 `cancelled`；团队与成员保留 | §2 降级路径 / §3 中断恢复 |
| `escalated` | §7.2 回退超限 或 §7.3 无法满足异质性 → 置位，交人类裁决 | `structured-contract.md` §A7 |
| `resume(reason)` | 用户批准复工 → 写 `resume_from` + **非空 reason**，从断点继续（不重复已澄清的 5W2H） | §3 新会话读案卷续审 |

**案卷状态文件最小结构**（`00-立案/team-state.json`，与既有 `案卷信息.json` 并存，不替换）：

```json
{
  "phase": "staged",
  "planReviewState": "awaiting_review",
  "approvedAt": null,
  "halted": false,
  "haltedAt": null,
  "escalated": false,
  "resumeReason": ""
}
```

---

## 4 与既有条款的关系（不相冲）

| 既有条款 | 关系 |
|---|---|
| §2 规模门 + 降级路径 | 规模门判定**在 staged 计划里写明**（L1 直行 / L3+ 五阶段）；降级也要写进计划让人看见 |
| §3 五阶段对抗协议 | **流程本体不变**：staged 只在 A 立案与 B 举证之间插一道人类批准门 |
| §3 检查点 / 新会话续审 | `resume(reason)` 复用既有 `resume_from` + 检查点机制；reason 是**新增要求**（此前无） |
| §4.5 提问中转协议 | staged 批准是**main 唯一对外提问**的合法场景之一（与 questions 软键合并提问，不额外增加提问轮次） |
| §4.6 主理人同步领活 | `phase=staged` 期间**尚未派发**，不适用领活纪律；`running` 后照旧 |
| §2 「协议内 B/C 阶段 main 保持中立」 | 不受影响：批准门在 B 之前 |

---

## 5 边界（明确不吸收）

- ❌ 前端实现：活动面板、形象、`lib/client/*`、cordis/tsdown/client bundle 工程层；
- ❌ 插件特有 API（`agent_teams_stage_plan` 等工具名）不进入本技能文本——本技能只描述**语义与案卷字段**，DSH 侧以 `ask_user_question` + 案卷文件落地；
- ✅ 只吸收：`phase` / `planReviewState` / `approvedAt` / `halted` / `escalated` / `resume(reason)` 六个语义点。

> 边界句修订登记见 `references/agent-teams-absorption.md` §8（v3.13 修订）。
