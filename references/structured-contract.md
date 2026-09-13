# 结构化契约（Structured Contract）· 反向吸收自 dsh-agent-teams 插件

> **版本**：v3.13（2026-09-13 · 团队 team-orchestration-mutual-absorb）。
> **来源**：本机 agent-teams 插件 v0.1.17（`@nanmicoder/dsh-agent-teams`，目录 `~/.dsh/profiles/<profile>/node_modules/@nanmicoder/dsh-agent-teams/`）的
> `lib/types.js`、`lib/types/types.d.ts`、`lib/quality-gates.js`、`lib/state.js`。字段名与常量**逐条按源码核对**，未作推测。
> **定位**：本文是**结构化契约的单一事实源**——`references/task-lifecycle.md` 与 `references/phase-gates.md` 描述的是**流程与检查点**，
> 与本文件重叠处以本文件为准（`task-lifecycle.md` / `phase-gates.md` 本轮不改，见 `merge-history.md` 2026-09-13 条目）。
> **边界**：本文件**不改五阶段对抗协议主流程**，也不改二审终审制本体语义；它是把插件侧的**数据模型与门禁**映射到本技能既有流程的增强层。

---

## A1 任务类型（kind）↔ 五阶段映射

**插件侧事实**（`lib/types.js:12–20`、`lib/types/types.d.ts:15–16`）：

```js
TASK_KINDS = ['requirements','implementation','verification','review','repair','integration','work']
```
缺省/未知 kind 一律按 `work` 处理（`lib/types/types.d.ts:14`）。质量类 kind 由 `isQualityKind()` 判定（`lib/quality-gates.js:32`）。

**映射到五阶段**（阶段语义不变，仅补 kind 标签；一个阶段可按需拆成多个任务）：

| kind | 五阶段落点 | 用途（本技能口径） |
|---|---|---|
| `requirements` | A 立案 | 争点陈述 / 达标阈值冻结。**完成需 `verdict=pass`** |
| `implementation` | B 举证、D 回灌修订 | 产生产物的写类任务（举证报告、修订稿）。完成需 `changedPaths` |
| `verification` | C 质证（独立复核部分） | 跑验证命令、复核证据。完成需逐条 `commandsRun` |
| `review` | C 质证、D 一审、E 二审终审 | 裁断类任务。**完成需 `verdict=pass`**；`reviewStage` 区分一审/终审（见 §A3） |
| `repair` | D 一审回灌修订、§7.3 复审前修补 | 按 findings 修复。**终审（`reviewStage='final'`）不得生成 repair**（§A3/§A8） |
| `integration` | A 立案收尾 / E 归档 | 汇总归档、案卷落盘 |
| `work` | 任意 | 缺省类，无质量门约束 |

> 溯源：`lib/types.js:12–20`；[SKILL.md §3 五阶段]。

---

## A2 任务契约字段集（contract）

**插件侧事实**——`TeamTask` 的结构化契约字段（`lib/types/types.d.ts:86–102`）：

```ts
objective?: string;          // 目标（= 本技能的「争点陈述」）
inScope?: string[];          // 允许产物范围
outOfScope?: string[];       // 明确不做
acceptance?: string[];       // 逐条验收标准（= 本技能 C2「达标阈值」的逐条化）
verify?: string[];           // 验证命令清单
deliverables?: string[];     // 交付物路径
nonGoals?: string[];         // 非目标
changedPaths?: string[];     // 实际改动路径（写类任务完成必填，workspace 相对）
coverageOf?: string[];       // 本任务覆盖的用户约束/goal 条目
acceptanceResults?: AcceptanceResult[];  // 逐条验收证据 {criterion,status:'passed'|'failed',evidence?}
commandsRun?: CommandResult[];           // 逐条命令证据 {command,status,exitCode?,evidence?}
```

**本技能用法**（写进 `tasks.json` 的任务对象，与既有 `{id,subject,status,assignee,dependencies,output}` **并存**）：

- A 立案：1 核心争点 → 1 个 `requirements` 任务；2–5 子争点 → 各 1 个 `implementation` 任务，逐条写 `acceptance`。
- `inScope` / `outOfScope` 用于**并行写冲突检测**（补齐此前只靠提示词「不越界」的空洞）。
- B 举证 / D 回灌修订：写类任务完成时**必填** `changedPaths` 与 `commandsRun`。
- 自报完成不再被采信：以 `acceptanceResults` 逐条证据为准（呼应 §7「磁盘即真相」）。

> 溯源：`lib/types/types.d.ts:34–46、86–102`；[SKILL.md §4.3 C2、§7 磁盘即真相]。

---

## A3 任务状态机、轮次与阶段

### A3.0 与 A3 举证契约的兼容（**扩展，不替换**）

> 本节对应吸收规格 B-02。**A3 仍是子代理回传的唯一举证契约**（`{"role":…,"artifacts":{…},"confidence":…,"uncertainties":[…]}`，见 SKILL.md §4 要素 2）；
> 本文件定义的结构化字段承载的是**进度/裁决层**，落点在案卷 `00-立案/tasks.json`，**不进 A3 JSON**。
> 子代理仍按 A3 回传；由 main 把 A3 摘要**转写**为 `tasks.json` 的字段。两者不是替代关系，也不得互相吞并。
> 冲突时以 SKILL.md §4 四要素 + A3 契约的**举证语义**为准，以本文件的**状态/门禁语义**为准。

### A3.1 状态机（既有，v3.6 已吸收 · 此处仅与 kind/契约对齐）

`pending → claimed → in_progress → completed | failed | cancelled`（终态无出边，禁从 completed 跳回）。
- 溯源：`lib/types.js:11`、`TERMINAL_TASK_STATUSES`（`lib/types/types.d.ts:13`）；SKILL.md §4.2.1。

### A3.2 轮次与阶段字段

| 字段 | 取值 | 语义 | 来源 |
|---|---|---|---|
| `round` | 1-based 整数 | 阶段轮次：质证轮（≤2）、一审回灌轮（固定 1） | `lib/types/types.d.ts:82–83`；SKILL.md §4.3 C2 |
| `reviewStage` | `first_instance` \| `final` | **新增语义位**：`first_instance` = 一审（可回灌）；`final` = 二审终审（**不再回灌**） | 规格 B-01/B-06；映射 [SKILL.md §3 E L86–87] |
| `rehearsalCount` | ≥0 整数 | **回退重审次数**，与 `round` **解耦**（回退只重做 main 侧独立裁决，不追加质证轮次） | 规格 B-06；[SKILL.md §7.2 L256–261] |

- **阶段不可逆**：A→B→C→D→E 推进方向不变（SKILL.md §7.2 末条）。
- **`final` 的硬语义**：不生成 repair、不回灌子代理；`needs_revision` 只能重做 main 侧独立裁决，超限即升级（§A7）。

---

## A4 裁断：verdict / findings / severity / rubricScores

**插件侧事实**：

```js
REVIEW_VERDICTS   = ['pass','needs_revision','reject']      // lib/types.js:21
FINDING_SEVERITIES = ['low','medium','high','blocker']       // lib/types.js:22
ReviewFinding = { id, severity, file?, line?, problem, requiredFix, resolved? }  // lib/types/types.d.ts:24–33
```

**三态 ↔ 中文裁断（别名映射，不改既有用词）**：

| 中文裁断（既有） | 结构化 `verdict` |
|---|---|
| 采信 | `pass` |
| 部分采信 | `needs_revision` |
| 排除 | `reject` |

**五维 rubric 与 severity 的双轨（**禁止只存 severity**）**：

- `rubricScores` = 五维原始分（各 0–1）：`evidence`（依据充分性）/ `sourceIndependence`（来源独立性）/ `coherence`（论证自洽）/ `crossExamConsistency`（与质证一致）/ `counterEvidence`（反证回应）——与 SKILL.md §7.2 五维**同名同义**。
- `severity` = **确定性映射**结果，可审计：`minScore = min(五维)` →
  `≤0.30 → blocker`｜`0.30<min≤0.60 → high`｜`0.60<min≤0.80 → medium`｜`>0.80 → low`。
- **🔴 硬约束**：`minScore ≤ 0.3` ⇒ 该条结论 `fail`，**回退一审重审**（SKILL.md §7.2 既有条款，语义未变）；映射后**必须保留五维原始分**，否则审计链断裂。
- **🔴 硬约束**：`reviewStage='final'` 且 `verdict='pass'` 时，`rubricScores` 必须**五维齐全**且无一维 ≤0.3，否则不得判完成。
- `verdict='pass'` 时**不得**残留 `resolved !== true` 的 `high` / `blocker` finding（插件既有规则 `lib/quality-gates.js:360`，本技能同口径）。
- 终审裁决理由**逐条字段化**：`findings[] = {id, severity, problem, requiredFix, file?, line?, resolved?}`；可选 `traceableTo[]` 指向一审产物/finding id，用于「禁止引入新论点」的弱校验（默认关闭，见 §A8）。

> 溯源：`lib/types.js:21–22`、`lib/types/types.d.ts:24–33`、`lib/quality-gates.js:318–319、341–360`；[SKILL.md §7.1 第 4 章 L245、§7.2 L254]。

---

## A5 执行代次与交接（attempt 机制）

**插件侧事实**（`lib/types/types.d.ts:72–79`）：

| 字段 | 语义 |
|---|---|
| `attempt` | 单调递增的**执行代次**；重派/重试使所有更早的 attempt 失效 |
| `attemptId` | 当前 claimed/in_progress 代次的**能力凭证**；成员更新任务时必须回带 |
| `handoffId` | 交接凭证：已发起撤销但下一代次尚未开始的过渡态标识 |
| `reassigning` | `true` 表示正在静默旧责任人，**调度器在此期间不得派发** |

**本技能落地**（`tasks.json` 任务对象**追加**这三个字段，既有字段不动）：

- main 重派某个举证/质证任务时 `attempt+1`，旧 `attemptId` 立即失效；子代理用旧凭证回传 → **拒绝更新并提示 stale**。
- 与 §4.2 看门狗互补：看门狗负责「不无限等」，attempt 机制负责「过期凭证不写入」。
- 交接期（`reassigning=true`）不派发新工作，避免双写同一案卷任务。

> 溯源：`lib/types/types.d.ts:72–79`；SKILL.md §4.2.1（状态机）、§4.3 C2（重试上限）。

---

## A6 ReviewPolicy：熔断与质证配置

**插件默认值**（`lib/quality-gates.js:17–22`）：

```js
DEFAULT_REVIEW_POLICY = {
  requirementsMinRounds: 1,
  requirementsMaxRounds: 4,
  codeMaxRounds: 3,
  maxRepairAttempts: 2,
}
```
另有 `requiredReviewers?: string[]`（schema 已声明，`lib/quality-gates.js:62–68`；插件侧**无消费点**——这正是本次移植要补的「假门禁」教训）。

**本技能配置表**（写进案卷 `00-立案/案卷信息.json` 的 `reviewPolicy` 段，取代散落 §4.3 的硬编码说明）：

| 键 | 本技能取值 | 对应既有契约 |
|---|---|---|
| `requirementsMinRounds` | 1 | 举证至少 1 轮 |
| `requirementsMaxRounds` | 2 | **C2 质证默认 1 轮、分歧 >2 追加 1 轮、最多 2 轮** |
| `codeMaxRounds` | 1 | **D 一审回灌修订固定 1 轮** |
| `maxRepairAttempts` | 2 | **C2 单子代理因相同原因最多重试 2 次即收敛** |
| `finalReviewMaxRehearsals`（**新增**，默认 1） | 1 | **§7.2 同一子争点最多 1 次回退** |
| `minIndependentSources`（**新增**，默认 2） | 2 | **§4.4② 收敛需 ≥2 个独立来源** |
| `requiredReviewers`（既有声明，本技能**启用**） | 角色名数组 | §4.7 异质性强制 + §4.8 R6（sensenova 三池 = 1 来源） |

> ⚠ 数值与轮次语义**不得改**：上表是把已有硬编码数值**显式化 + 可审计化**，不是放宽或收紧（`merge-history.md` 已登记）。
> 溯源：`lib/quality-gates.js:17–22、35–70`；[SKILL.md §4.3 C2、§4.4②、§7.2]。

---

## A7 `escalated` 与 `halted`：两种完全不同的停止态

| 态 | 触发 | 语义 | 恢复方式 |
|---|---|---|---|
| `escalated: true` | 自动裁决/修补循环撞上配置上限 | **不是 halt**：需要**人类裁决**（升级用户人工仲裁） | 用户给结论后继续 |
| `halted: true` + `haltedAt` | 人类主动拉停 | 团队保留在盘、成员仍可用，未完成任务取消 | `resume(reason)`，**reason 必填非空** |

**本技能落地**：
- §7.2 回退次数超 `finalReviewMaxRehearsals` → 置 `escalated=true` 并走 §7.3。
- §7.3 独立复审**无法满足异质性约束** → 置 `escalated=true`，**禁止降级为同源复审**（与 §4.7/§4.8 红线一致）。
- `halted` 的完整生命周期（staged 审批 / awaiting_feedback / resume）见 `references/web-staged-lifecycle.md`。

> 溯源：`lib/types/types.d.ts:198–208`、`lib/quality-gates.js:437–438、467–468、779、802–806`；[SKILL.md §7.2 L257、§7.3 L265]。

---

## A8 交付门清单（`canDeclareDelivery` 等价物）

**插件侧事实**：`canDeclareDelivery(team)` 是**独立于其他门**的交付判定（`lib/quality-gates.js:516–558`），已知 blocker 文案包括
`"{id} completed without verdict=pass"`、`"{id} failed without a follow-up repair"`、`completed implementation has no passing review`、`"{id} has unaudited path {path}"`。

**本技能交付门清单**（交付前逐条勾选，任一不过 → 不得交付）：

- [ ] 每个 `review` / `requirements` 任务为 `completed` 且 `verdict=pass`；
- [ ] `failed` 的任务**必有**后续 repair / 重派任务（不得静默跳过）；
- [ ] 存在 `implementation` 完成时，**必有一个 `verdict=pass` 的 review**；
- [ ] 终审（`reviewStage='final'`）已存在且 `verdict=pass`，`rubricScores` 五维齐全、无一维 ≤0.3；
- [ ] `changedPaths` 全部落在 `inScope` 内且未被 `outOfScope` 命中（未审计路径 = blocker）；
- [ ] 独立来源去重后 ≥ `minIndependentSources`；
- [ ] 无未解决 `high`/`blocker` finding；
- [ ] 口子收敛：`escalated=false`（若 `true`，须附人类裁决结论）。

**可选的弱校验**：`findings[].traceableTo`（指向上游 finding id / 一审产物路径）用于「禁止引入新论点」的可审计化；**默认关闭**，避免误伤（对应移植规格 M15）。

> 溯源：`lib/quality-gates.js:516–558`；[SKILL.md §7 L233/L237、§7.1 L246、§7.3 L265]。

---

## A9 三层质量门（创建 / 完成 / 交付）

| 层 | 插件承载 | 本技能落点 | 清单 |
|---|---|---|---|
| **创建门** | `validateCreateTask`（`lib/quality-gates.js:197–309`） | A 立案登记任务时 | 质量类 kind 必须有契约（`objective`+`acceptance`）；依赖必须存在且不构成环；`inScope`/`outOfScope` 不得互相矛盾；`review` 任务须指明 `reviewedTaskId` |
| **完成门** | `evaluateQualityCompletion`（同上 `341–399`） | 任务标记 completed 时 | 见 §A4 硬约束；写类任务须有 `changedPaths` + `commandsRun`；验收标准须逐条有 `acceptanceResults` |
| **交付门** | `canDeclareDelivery`（同上 `516–558`） | E 二审终审产出前 | 见 §A8 清单 |

> 三层必须分离：**创建门挡的是畸形任务，完成门挡的是畸形结论，交付门挡的是残缺交付**。任何一层不得代替另一层。

---

## A10 术语中英对照（插件 ↔ 本技能）

| 插件术语 | 本技能现状用词 | 对齐后统一用语 | 本文件落点 |
|---|---|---|---|
| `kind` | 阶段 A/B/C/D/E | 任务 type（`kind`）+ 阶段标签并存 | §A1 |
| `objective` | 争点 / 子争点 | `objective`（= 争点陈述） | §A2 |
| `acceptance[]` | 达标阈值（C2） | `acceptance[]` | §A2 |
| `inScope[]` / `outOfScope[]` | 无 | 原样引入 | §A2 |
| `verify[]` | 无（有检查点/脚本命令） | 原样引入 | §A2 |
| `deliverables[]` | 案卷产物路径 | 原样引入 | §A2 |
| `nonGoals` | 边界 / 不越界 | 原样引入 | §A2 |
| `changedPaths[]` | 无 | 原样引入 | §A2 |
| `acceptanceResults[]` / `commandsRun[]` | 无 | 原样引入 | §A2 |
| `verdict` | 采信 / 部分采信 / 排除 | 保留中文裁断 + 落 `verdict` 三态 | §A4 |
| `findings[]` | 裁决理由（散句） | 原样引入 | §A4 |
| `severity` | 五维 rubric 0–1 分 | 双轨：`rubricScores` + `severity` | §A4 |
| `round` | 质证轮数 / 回灌轮 | `round`（阶段轮次） | §A3 |
| `reviewStage` | 一审 / 二审终审 | `first_instance \| final` | §A3 |
| `attempt` / `attemptId` | 无 | 原样引入 | §A5 |
| `handoffId` / `reassigning` | 无 | 原样引入 | §A5 |
| `reviewPolicy` | C2 硬编码数值 | `reviewPolicy{}` | §A6 |
| `escalated` | 升级用户人工仲裁 | `escalated` | §A7 |
| `halted` / `resume(reason)` | 无 | 原样引入 | `web-staged-lifecycle.md` |
| `phase=staged \| running` | 无 | 原样引入 | `web-staged-lifecycle.md` |
| `canDeclareDelivery` | 禁止跳阶段 + §7.3 裁断 | 交付门清单 | §A8 |
| `handoffSummary` | C1 结构化交接摘要 | 可选**软键**（缺失仅 warning，不触发 C2 重试） | §A2 / §A3 |

---

## A11 落盘位置与最小示例

- **案卷结构**：`00-立案/tasks.json`（任务图 + 契约字段）、`00-立案/案卷信息.json`（`reviewPolicy` 段）、
  `02-质证/` `04-回灌修订/` `05-二审终审/`（产物）；元状态（`tasks.json` / `resume_from` / `cross_exam` / `status`）**仅 main 写**（SKILL.md §4.1 末注）。

```json
{
  "tasks": [
    { "id": "t1", "subject": "立案·争点拆分", "kind": "requirements", "status": "completed",
      "objective": "拆 1 核心 + 3 子争点", "acceptance": ["争点互斥", "每子争点可独立举证"],
      "dependencies": [], "attempt": 1, "attemptId": "a-1001", "verdict": "pass", "round": 1 },
    { "id": "t2", "subject": "举证·投资视角", "kind": "implementation", "status": "completed",
      "assignee": "investment-analyst", "dependencies": ["t1"], "attempt": 1, "attemptId": "a-1002",
      "inScope": ["02-质证/investment-*"], "outOfScope": ["法律意见"],
      "deliverables": ["01-举证/P1-investment.md"],
      "changedPaths": ["deliverables/trial/2026-09-13/TC-20260913-1/01-举证/P1-investment.md"],
      "commandsRun": [{ "command": "python tests/check_references.py", "status": "passed", "exitCode": 0 }],
      "acceptanceResults": [{ "criterion": "含 3 条独立证据", "status": "passed", "evidence": "P1-investment.md L12–28" }] },
    { "id": "t5", "subject": "一审·裁决", "kind": "review", "status": "completed",
      "dependencies": ["t4"], "attempt": 1, "reviewStage": "first_instance", "round": 1,
      "reviewedTaskId": "t2", "verdict": "needs_revision",
      "findings": [{ "id": "F-01", "severity": "high", "problem": "来源单一时仍判收敛", "requiredFix": "补第二独立来源" }],
      "rubricScores": { "evidence": 0.7, "sourceIndependence": 0.4, "coherence": 0.8,
                        "crossExamConsistency": 0.6, "counterEvidence": 0.5 } },
    { "id": "t6", "subject": "二审终审", "kind": "review", "status": "pending",
      "dependencies": ["t5"], "reviewStage": "final", "rehearsalCount": 0,
      "echoGate": { "expected": 3, "collected": 3, "confirmedAt": 1789250000000, "reason": "echo_collected" },
      "deliverables": ["05-二审终审/final-verdict.md"], "acceptance": ["五章齐备", "五维 rubric 全维达标"] }
  ]
}
```

> `echoGate`（终审前置门禁的结构化落点）与 `handoffSummary` 的可选软键语义见 SKILL.md §3 E 步骤 0 与 §4.3 C3。
