---
name: team-orchestration
version: 2.3.0
description: "多智能体团队编排引擎 — 目标明确、任务拆解、专家匹配、交叉验证、自进化。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags:
  - orchestration
  - team
  - multi-agent
  - self-evolution
---

# Team Orchestration v2 — 多智能体团队编排

可用专家池：28 个 WorkBuddy 专家团（188 agents）+ 6 个 subagent。
完整索引：`references/workbuddy-experts/_index.md`

---

## 核心工作流（10 步）

```
接到任务
  → [目标明确] 模糊度检测→澄清追问→语义坍缩防护→目标重述
  → [强化拆解] 子任务清单→依赖图(DAG)→关键路径→角色分配
  → [预验尸] 发散5模式逐项检查(Sequencing/Omissions/Additions/Granularity/Misinterpretation)
  → [双系统分治] 复杂度判断 → System 1（直调/快速）/ System 2（团队）
  → [专家匹配] python3 scripts/expert-matcher.py --domains ...
  → [执行] 调度专家 → 收集产出 → 贝叶斯置信度聚合
  → [交叉验证 Layer 1.5] 声明提取→来源追溯→三角测量→冲突检测→置信度校准
  → [自验证+审核] Layer 1(专家自验证) → Layer 2(@reviewer)
  → [交付] 🟢PASS / 🟡CONDITIONAL / 🔴FAIL(≤3轮重审)
  → [反馈+自进化] 负反馈/正反馈/用户纠正 → Loop1,2,3
```

---

## 各阶段说明

### 一、目标明确 + 强化任务拆解

设计文档：`references/task-decomposition-v2.3.md`

| 阶段 | 步骤 | 输出 |
|------|------|------|
| A 目标明确 | A1 模糊度检测(5W2H覆盖/语义坍缩/模糊词) → A2 澄清追问(≤2轮) → A3 语义坍缩防护 → A4 目标重述(5W2H结构化) | goal_restatement |
| B 强化拆解 | 子任务清单(6种类型) → DAG依赖图(blocking/conditional/feedback) → 关键路径 → 角色分配(AI/Human/AI+Human) → 五维元标签 | subtasks[] + dependency_graph |
| C 预验尸 | 发散5模式逐项验证(Sequencing/Omissions/Additions/Granularity/Misinterpretation) | risk_assessment + fallback |

- 目标重述须经用户确认方可进入拆解
- 2轮追问未解决 → 标记「不可拆解」返回用户
- 最优粒度 ≈ √(推理步数)。L3+风险 → 强制团队路径
- **脚本：** `python3 scripts/task-decomposer.py --task "..." --json`

---

### 二、动态专家匹配（含置信度校准）

设计文档：`references/expert-matching.md`

| 维度 | 权重 | 依据 |
|------|------|------|
| 领域匹配 | 35% | plugin.json categoryId + displayDescription |
| 能力匹配 | 30% | Agent MD 核心能力章节 |
| 历史表现 | 20% | expert-scores.json |
| 负载惩罚 | 15% | 当前会话已分配数 |

- 置信度 < 0.6 → 标记「匹配不确定性高」，建议手动确认
- **脚本：** `python3 scripts/expert-matcher.py --domains ... --json`

---

### 三、执行路径选择

| 复杂度 | 路径 | 触发条件 |
|--------|------|---------|
| L1 简单 | System 1 直调 | 单维度、已知事实、低风险 |
| L2 中等 | System 1→2 快速 | 多维度但模板匹配度高 |
| L3 复杂 | System 2 团队 | 跨领域、需多轮推理 |
| L4 深度 | System 2 完整团队 | 深度分析、需完整 SOP |

15 个快速路径模板列表 + 流程图 → `references/team-templates/index.md`
System 1 执行遇错 → 自动升级 System 2
主理人铁律：禁止代写/禁止跳过阶段/禁止成员直连 → `references/communication.md`

---

### 四、交叉验证 Layer 1.5

设计文档：`references/cross-validation.md`

| 规则 | 含义 |
|------|------|
| R1 来源独立性 | 跨源验证要求不同文档+不同编辑流程 |
| R2 归因准确性 | 声明内容正确 ≠ 声明来源正确 |
| R3 置信度挂钩 | 单来源→中等置信度；≥2独立→低不确定性 |
| R4 场景适配 | 高影响强制三角测量；低影响跳过 |

四档自适应深度：skip(L1) / light(L2) / standard(L3) / deep(L4+高风险)
- **脚本：** `python3 scripts/cross-validator.py --task <id> --depth auto`

---

### 五、自验证 + 审核节点

**Layer 1:** 每个 subagent 检查：数据准确性 / 格式合规 / 完成度 / 红线 / 置信度标注
- 低置信度→标注「不确定」；不标注→默认中等置信度

**Layer 2: @reviewer 审核** → `references/phase-gates.md`
- 🟢PASS → 交付 / 🟡CONDITIONAL → 附带标注后交付 / 🔴FAIL → 退回(≤3轮)

---

### 六、反馈循环 + 三环自进化

设计文档：`references/self-evolution-protocol.md`

| 回路 | 触发 | 动作 |
|------|------|------|
| 负反馈 | 匹配失败/输出不合格 | 分析根因→调整权重(连续3次失败才冷却) |
| 正反馈 | 用户明确认可 | 加深方向探索(保留多样性) |
| 用户纠正 | 用户提出修改 | 记录偏误→会话内不重复 |

- Loop 1: 执行中反思 → `self-evolution-log.md`
- Loop 2: 事后回顾 → `python3 scripts/self-evolution/post-task-evolve.py`
- Loop 3: 主动联网增强 → `python3 scripts/self-evolution/proactive-search.py --experts all`

---

## 思维方法论集成

| 方法论 | 工作流位置 |
|--------|-----------|
| **双系统理论** | 核心工作流 → 双系统分治 + 路径选择 |
| **第一性原理** | 阶段 B 强化拆解：从本质分解而非模板 |
| **5W2H分析法** | 阶段 A 目标明确：7维覆盖，缺失即追问 |
| **SMART目标** | 阶段 B + 五：AC + 置信度 |
| **奥卡姆剃刀** | 全流程：最小必要团队/步骤 |
| **预验尸法** | 阶段 C 发散5模式 |
| **反馈循环** | 阶段六三环自进化 |
| **贝叶斯置信度** | 阶段二专家匹配 + 阶段五置信度标注 |
| **三角互证/孤证不立** | 阶段四交叉验证 |

---

## 参考文件索引（L3 — 按需读取）

使用规则：工作流推进到对应阶段时读取该文件；不提前加载。

| 读取时机 | 文件 | 用途 |
|---------|------|------|
| 一、目标明确+拆解时 | `references/task-decomposition-v2.3.md` | 完整 schema + 5W2H 映射 |
| 二、专家匹配时 | `references/expert-matching.md` | 匹配评分算法细节 |
| 三、路径选择时 | `references/team-templates/index.md` | 15 个快速模板定义 |
| 四、交叉验证时 | `references/cross-validation.md` | 状态机+数据结构+评分算法 |
| 六、反馈循环时 | `references/self-evolution-protocol.md` | 三环协议细节 |
| 任意阶段 | `references/workbuddy-experts/_index.md` | 188 agents 完整索引 |
| 需要时 | `references/first-principles.md` | 第一性原理框架 |
| 需要时 | `references/task-lifecycle.md` | 任务状态转场规范 |
| 需要时 | `references/handoff-protocol.md` | 交接协议 |
| 需要时 | `references/phase-gates.md` | 阶段关卡检查清单 |
| 需要时 | `references/patterns.md` | 多步骤工作流模式 |
| 需要时 | `references/communication.md` | Agent 通信模式 |
| 需要时 | `references/knowledge/` | 39 个领域知识文件 |
