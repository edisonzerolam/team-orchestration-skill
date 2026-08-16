# dsh-agent-teams 优秀设计吸收（AgentTeams Absorption · v3.6）

> **来源**：https://github.com/NanmiCoder/dsh-agent-teams （DSH AgentTeams 插件，343★）。
> **本文件**：把外部优秀设计吸收进 team-orchestration 技能的**可落地规则**。与既有契约（A3 / 五阶段对抗 / 二审终审制 /
> 加权投票 / 预算门禁）**融合而非替换**。变化量级：新增依赖感知任务模型 + durable 邮箱 + 成员 persona + 工具级越权防护 +
> 磁盘即真相 + 归档化删除 + fail-loud 纪律。
> **吸收策略**：本技能是**提示词级编排方法论 + 纯 stdlib Python 决策脚本**，不引入前端 UI / cordis plugin 工程层；
> 仅吸收与编排协议正交的**数据模型、状态机、成员边界、持久化纪律**。

---

## 1. 依赖感知任务图（Dependency-aware task graph）· 吸收自 B1/B2/P1/P2

### 1.1 五阶段任务状态机

把 A-E 阶段当作显式任务记录（对应 TeamTask），状态迁移白名单化：

```
立案(pending) → claimed → in_progress → completed → 举证(→completed) → 质证(→completed)
   → 一审(→completed) → 二审终审(→completed) → 归档(completed)
                              ↘ failed | cancelled（终态，无出边）
```

- **迁移白名单**：`pending→claimed→in_progress→completed|failed|cancelled`；终态（completed/failed/cancelled）**无出边**，
  禁止从 completed 跳回 in_progress（防"静默重开"）。
- **依赖门控**：每阶段声明 `dependsOn[]`（立案⊲∅；举证⊲立案；质证⊲全部举证；一审⊲质证；二审⊲一审）。
  阶段**仅在依赖全部到达 completed/终态门**后才能启动；`status` 暴露 `blocked-by` 供审计。
- **所属/越权**：主理人可推进任意阶段；成员（worker）只能推进**自己被指派的**任务——架构层限制而非仅提示。

### 1.2 使用方式（融入五阶段）

- **A 立案**：main 拆 1 核心争点 + 2-5 子争点后，登记为**带依赖与状态的任务清单**（案卷内 `任务状态` 结构）。
- **B 举证**：每子争点一个举证任务（assignee=对应子代理），依赖=立案 completed；子争点间显式声明依赖（如"数据层依赖宏观结论"）。
- **C 质证**：一个"质证"阶段任务，依赖=全部举证 completed——未收齐全部举证产物**不得**启动质证（结构性保证，替代"检查收尾"人工核对）。
- **D 一审 / E 二审终审**：仅接受 `completed` 证据；`failed`/blocked 的举证输出→重新派工/重审（见 §7.3 复审路径），不得静默跳过。

### 1.3 落盘建议

案卷 `00-立案/` 内建 `tasks.json`：

```json
{
  "tasks": [
    { "id": "t1", "subject": "立案·澄清5W2H", "status": "completed", "dependencies": [] },
    { "id": "t2", "subject": "举证·投资视角", "status": "pending", "assignee": "investment-analyst", "dependencies": ["t1"], "output": "" },
    { "id": "t3", "subject": "举证·风险视角", "status": "pending", "assignee": "risk-manager", "dependencies": ["t1"], "output": "" },
    { "id": "t4", "subject": "质证", "status": "pending", "dependencies": ["t2", "t3"] },
    { "id": "t5", "subject": "一审·裁决", "status": "pending", "dependencies": ["t4"] },
    { "id": "t6", "subject": "二审终审", "status": "pending", "dependencies": ["t5"] }
  ]
}
```

---

## 2. Durable 邮箱直邮 + 唤醒即行动（Durable mailbox messaging）· 吸收自 B3/B6/P6

### 2.1 邮箱模型

每参与者一个 JSONL 邮箱（追加式）：主理人 `captain.jsonl`，每成员 `<member>.jsonl`。消息结构
`{id, from, to, content, ts}`。DSH 映射：`subagent`/`send_message`（depth-1）即唤醒。

### 2.2 原则

1. **唤醒即行动**：成员收到消息才行动，无常驻轮询；离线时消息留邮箱待下次投递（与 §4.2 看门狗互补——不 sleep/轮询，以完成通知/回收产物为准）。
2. **防冒名**：回传 message 的 `from` 强制为调用者自身身份；拒绝伪造署名——强化反盲从（§4.4）真伪根源。
3. **无队长中转**：成员↔成员可直接投递（见 §7 P9 语义细化：**禁绕过裁决，不禁横向通信**）。
4. **磁盘即真相，事件仅审计**：任务/成员/邮箱状态以落盘为准；会话事件日志仅作审计与确定性重放（二审终审可复盘）。若成员完成任务却忘走更新仪式，主理人以 `status`/文件为准汇总（不采信自报，呼应回归 F1）。
5. **viewer-scoped 状态面**：主理人看全量（含各邮箱），质证成员在回灌前**只见己方**——天然隐藏他方论点，防对抗泄漏。

---

## 3. 成员 persona 自包含系统提示 + 工具级越权防护 · 吸收自 B4/P3/P4

### 3.1 persona 块（融入 §4 四要素，作为拓展块）

每个子代理 prompt 在四要素外追加**自包含 persona 段**，替代"部署默认 persona"：

```
你是「{角色名}」，团队成员，身份/署名: {name}。
团队上下文: 团队={team}，队长={captain}，案卷状态位于 {stateDir}（只读诊断，勿直接改；用 A3/工具回传）。
工作规则:
  1. 收到指派→声明认领；开始即标 in_progress。
  2. 用可用工具认真完成,不必cut corners。
  3. 完成时给 status=completed + 结构化 output（A3 结论）。
  4. 完成/遇阻均向队长短报。
  5. 问队友或队长→直接投递（to=<对方>）。
  6. 你是 worker: 不建团/不加员/不删除/不裁决——那是队长/主理人的职责。
  7. 反盲从：每条结论自带 1 条最强反论并回应（缺失则置信度上限 0.6）。
```

### 3.2 工具级 deny（升级"禁止成员越权"为可执行层）

将「建团 / 加员 / 删团 / 创建任务 / 终审裁决」类能力置于成员 **deny 列表**（DSH `subagent`/`send_message`
无 `toolFilter` 参数，故为**主理人提示词纪律的显式化**：在 fork/subagent prompt 中声明"你不可调用 X/Y/Z"并
在验收时校验其 `actions` 未含越权项）。与"主理人铁律·禁止成员直连/越权"一致，并强化可执行性。

### 3.3 角色视角裁剪（B4）

给立案官/举证/质证/一审/二审每角色一块 scope：允许的产物、禁止的动作。如"二审终审不得引入新论点"直接写入
二审角色 persona 的禁止项——把"不越界"变成**设计属性**而非事后检查。

---

## 4. 零交互模型路由快照（inherit-by-default, override-only）· 吸收自 B5/P5

- **默认**：每个成员快照主理人当前 step 实际生效的 provider/model/reasoning，冷恢复沿用（跨会话一致）。
- **仅显式异构**：用户明确"该角色用模型 X/provider Y"时才派发专属 provider+model；否则一律继承。
  DSH 映射：`subagent`/`subagent_fork` 默认继承 main 模型；`workflow` `agent({provider,model})` 做异构覆盖。
- **与 §4.1 视觉路由一致**：main 默认 text-only；需视觉时走 `workflow` 视觉模型或外部 OCR 转文本（不硬调不存在的类型）。

---

## 5. 锁定串行 + 原子写 + 容错读（持久化纪律）· 吸收自 B7/P14

| 纪律 | 具体做法 |
|------|---------|
| **串行化** | 所有落盘操作（质证回灌 / 回灌修订 / 归档）**同一案卷内串行**，避免并发读-改-写交错。DSH 下即"主理人逐一处理、不并行写同一案卷文件"。 |
| **原子写** | 写文件先写临时文件再 rename 覆盖；避免写一半崩溃留下损坏案卷。 |
| **容错读** | 读产物遇畸形行/损坏段→**降级为低可信警告**（不崩溃），标记后继续；印证 §7.3 低可信度复审路径。 |
| **状态校验守卫** | 读 `案卷信息.json`/`tasks.json` 前做**结构校验**（字段齐全、状态机合法）；失败即判不可续并产可操作错误，防静默错判二审终审。 |

---

## 6. 归档化删除 + 全案卷可恢复 · 吸收自 B12/P8

- **终局归档**：E 二审终审产出《终审意见书》后，将**全案卷**（含 tasks.json 依赖图 + 各阶段事件 + 邮箱 + 分歧数/回灌轮数/
  收敛路径 + believability 权重）移到 `deliverables/trial/YYYY-MM-DD/<docket_id>/`（或 `archive/<caseId>/`），
  **archive-not-delete**，供复盘与自学习 S1/S2 挖掘。
- **复盘可重建**：归档目录应保留完整依赖图与收敛路径，使"从历史会话恢复完整团队/案卷、重建依赖"成为可能。

---

## 7. 与现行契约的语义细化（冲突点处理）

| 现行 | 吸收后 |
|------|--------|
| 主理人铁律「禁止成员直连」 | **细化为**：禁止**绕过主理人裁决**；允许成员间**横向通信/交换产物**（DSH `send_message` depth-1）。裁决与团队变更权唯一归主理人。 |
| B 举证"同一消息并行" | 并行不受影响，但**每子争点登记为独立任务并声明依赖**，质证仅在全部举证 completed 后启动。 |
| A3 作为唯一举证契约 | A3 仍是**举证契约**；新增 **任务状态记录 + 邮箱**承载进度/运维层。 |
| 二审终审"不回灌" | 不变（二审终审不回灌）；新增：仅接受 completed 证据，blocked/failed→复审/重派。 |

---

## 8. 触发与边界（When to apply）

本吸收**不改五阶段对抗协议主流程**，是增强层：
- **默认生效**：依赖任务模型、persona 块、磁盘即真相、归档化删除、fail-loud 纪律——直接融入既有流程。
- **可选增强**：durable 邮箱整体落地需较高工程投入（本技能为提示词级，故以**落盘案卷 + 状态文件**体现，不依赖插件）。
- **不吸收**：Web UI 活动面板 / 小鲸鱼形象（编排方法论不需要前端）；插件工程层（cordis/tsdown/client bundle）；
  与 DSH 结构强绑定的实现细节。

---

## 附：来源

- [GitHub README](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/README.md) · [README_ZH](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/README_ZH.md)
- [docs/usage.md（工作原理 / 工具一览 / 配置 / 限制）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/docs/usage.md)
- [docs/developing-dsh-plugins.md（工程经验，正交参考）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/docs/developing-dsh-plugins.md)
- [src/types.ts（TeamState/TeamTask/TeamMember/TeamMessage）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/src/types.ts) ·
  [src/members.ts（persona / 模型快照 / durable 邮箱 / toolFilter）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/src/members.ts) ·
  [src/state.ts（锁定/原子写/校验守卫）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/src/state.ts) ·
  [src/tools.ts（工具契约）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/src/tools.ts) ·
  [src/index.ts（策略注入）](https://github.com/NanmiCoder/dsh-agent-teams/blob/main/src/index.ts)
