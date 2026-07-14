---
name: team-orchestration
version: 2.6.0
description: "多智能体团队编排引擎 — 目标明确、任务拆解、专家匹配、交叉验证、自愈(含专家研讨)、自进化、监控/回滚。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags:
  - orchestration
  - team
  - multi-agent
  - self-evolution
---

# Team Orchestration v2 — 多智能体团队编排

可用专家池：31 个专家团 + 271 独立 agent = 302（WorkBuddy 专家团 + 移植团 + 虚拟团 + 独立专家）。
完整索引：`references/workbuddy-experts/_index.md`

---

## Quick-Start（30 秒上手）

**能做什么：** 把一个模糊的问题变成可执行的子任务计划，自动匹配专家并行执行，交叉验证后交付。

**怎么触发（自然语言即可）：**
- "帮我分析一下 XXX 股票" → 自动组建投资分析团队
- "审查这个代码仓库的安全性" → 自动组建工程保障团队
- "写一份深度 AI 行业研究报告" → 自动组建研究团队
- "组建团队分析 XXX" → 显式指定

**你会得到：**
1. 目标重述（你确认后才继续执行）
2. 任务拆解蓝图（子任务 + 依赖关系）
3. 专家匹配 → 并行执行 → 交叉验证
4. 审核报告（🟢PASS / 🟡CONDITIONAL / 🔴FAIL + 错误码）

**不需要你操心：** 11 步工作流全自动运行；专家匹配、交叉验证、自愈由系统自动完成。

---

## 核心工作流（11 步）

```
接到任务
  → [目标明确] 模糊度检测→澄清追问→语义坍缩防护→目标重述
  → [强化拆解] 子任务清单→依赖图(DAG)→关键路径→角色分配
  → [预验尸] 发散5模式逐项检查(Sequencing/Omissions/Additions/Granularity/Misinterpretation)
  → [双系统分治] 复杂度判断 → System 1（直调/快速）/ System 2（团队）
  → [专家匹配] python3 scripts/expert_matcher.py --domains ...
   → [执行] 按依赖顺序调度 ★ — orchestrator 拓扑排序保证:
         Phase 1: 调研先行 (information_retrieval, async_research)
         Phase 2: 分析依赖调研 (analysis_judgment)
         Phase 3: 创作依赖分析 (creation_generation)
         Phase 4: 决策依赖所有前置 (decision_execution)
         同一 phase 可并行, 跨 phase 阻塞等待
   → [回滚自动化] ← v2.6 快照引擎+愈合前快照+失败自动回滚 (see 九、Agent 回滚自动化)
   → [交叉验证 Layer 1.5] 声明提取→来源追溯→三角测量→冲突检测→置信度校准
   → [自愈机制] ← v2.4 贯穿所有阶段 → v2.5 含专家研讨 → v2.6 监控指标暴露(Prometheus /metrics)
       故障检测(6检测器) → 诊断(10故障类型) → 恢复(7策略+熔断器+专家小组研讨) → 验证(5验证器)
       L0预设规则→L1单专家→L2多专家研讨→L3人类 escalate 四层防御
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
- **脚本：** `python3 scripts/task_decomposer.py --task "..." --json`

---

### 二、动态专家匹配（含置信度校准）

设计文档：`references/expert-matching.md`

| 维度 | 权重 | 依据 |
|------|------|------|
| 领域匹配 | 35% | plugin.json categoryId + displayDescription |
| 能力匹配 | 30% | Agent MD 核心能力章节 |
| 历史表现 | 20% | expert-scores.json |
| 负载惩罚 | 15% | 当前会话已分配数 |

#### v2.6 增强

| 特性 | 说明 |
|------|------|
| 动态权重矩阵 | `references/weight-matrix.json` — 按任务类型动态调整四维权重，非固定比例 |
| ε-greedy 冷启动探索 | 新 Agent 以概率 ε 探索分配（ε 随经验衰减），避免冷启动偏置 |
| 三阶层次化加载 | 领域级 → 能力级 → 实体级三级过滤，大幅降低匹配延迟 |

- 置信度 < 0.6 → 标记「匹配不确定性高」，建议手动确认
- **脚本：** `python3 scripts/expert_matcher.py --domains ... --json`

---

### 三、执行路径选择

| 复杂度 | 路径 | 触发条件 |
|--------|------|---------|
| L1 简单 | System 1 直调 | 单维度、已知事实、低风险 |
| L2 中等 | System 1→2 快速 | 多维度但模板匹配度高 |
| L3 复杂 | System 2 团队 | 跨领域、需多轮推理 |
| L4 深度 | System 2 完整团队 | 深度分析、需完整 SOP |

19 个快速路径模板列表 + 流程图 → `references/team-templates/index.md`
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

### 五、自愈机制（Self-Healing）— v2.5 含专家研讨

跨阶段的自愈监控管道，贯穿所有执行阶段，在故障发生时自动检测→诊断→恢复→验证。

#### 恢复策略（7+1 类）

| 策略 | 说明 | 适用故障 |
|------|------|---------|
| retry | 指数退避重试(最多3次) | FT-01/02/03 |
| degrade | 降级验证深度 | FT-06 |
| rollback | 回滚到上一个稳定状态 | FT-04/07 |
| switch | 切换到备用 Agent | FT-05/08 |
| circuit_break | 熔断器 OPEN | FT-07(连续) |
| skip | 跳过当前故障 | 低严重度 |
| **escalate_via_panel** | **★ L0→L1→L2→L3 专家研讨管道** | **FT-04/07/09/10** |
| escalate(旧) | 直接升给人类(兜底) | 研讨不可用时 |

#### 专家小组研讨（v2.5 new）

设计文档：`references/problem-solving-panel.md`

当 escalate 策略被触发时，自动启动四层防御解题管道：

| 层级 | 名称 | 解决率 | 成本/次 | 处理时间 |
|------|------|--------|---------|---------|
| **L0** | 预设规则匹配 | ~60% | $0 | ~0ms |
| **L1** | 单专家深度调研+方案 | ~25% | $0.57 | ~30s |
| **L2** | 多专家研讨(3人)+辩论+投票 | ~10% | $1.76 | ~120s |
| **L3** | 人类 escalate | ~5% | $1.94 | — |

**关键设计**：
- 触发条件：仅 FT-04/FT-07/FT-09/FT-10 触发
- 冷却期：同故障 5min 内直接返回缓存结论
- 预算保护：单场 ≤120K tokens，每日 ≤500K tokens
- 研讨不收敛 → 自动取当前最优 + 标记 `not_converged`
- Sceptic 角色强制包含，投票权重 ×1.5（防错误共识）
- 脚本：`python3 scripts/problem_solver.py --team <team_id> --agent <agent_id> --fault-type FT-04`

#### 熔断器状态机

CLOSED→OPEN(连续3次失败)→HALF_OPEN(冷却60s)→CLOSED(连续恢复2次)

#### 与三环自进化联动

每次自愈自动触发 Loop 1(日志)/Loop 2(评分)/Loop 3(元学习)

**脚本：**
- `python3 scripts/self_heal.py --team <team_id> --agent <agent_id> [--context-json "{}"]`
- `python3 scripts/self_heal.py cb-status --team <team_id> --agent <agent_id>`
- `python3 scripts/self_heal.py solver --team <team_id> --agent <agent_id>`
- `python3 scripts/health-monitor.py check <team_id> [--auto-heal]`

---

### 六、自验证 + 审核节点

**Layer 1:** 每个 subagent 检查：数据准确性 / 格式合规 / 完成度 / 红线 / 置信度标注
- 低置信度→标注「不确定」；不标注→默认中等置信度

**Layer 2: @reviewer 审核** → `references/phase-gates.md`
- 🟢PASS → 交付 / 🟡CONDITIONAL → 附带标注后交付 / 🔴FAIL → 退回(≤3轮)

---

### 七、反馈循环 + 三环自进化

设计文档：`references/self-evolution-protocol.md`（v2.3 增强版）

完整调研报告：`references/loop-engineering-research.md`

| 回路 | 触发 | 动作 | v2.3 增强 |
|------|------|------|-----------|
| 负反馈 | 匹配失败/输出不合格 | 分析根因→Polyak 平均更新权重 | +增益监控 Aβ 检测 |
| 正反馈 | 用户明确认可 | 加深方向探索(保留多样性) | +上限封顶防过调 |
| 用户纠正 | 用户提出修改 | 记录偏误→会话内不重复 | +反馈质量六维自检 |

| 循环 | 层级 | 时间尺度 | 增强内容 |
|------|------|---------|---------|
| Loop 1 | L1 执行层 | 秒级 | +LoopGain 增益监控 + 上下文预算 + 周期重置防退化 |
| Loop 2 | L2 策略层 | 分钟级 | +Polyak 平均更新 + 多轮退化检测 + 收敛速度记录 |
| Loop 3 | L3 元学习层 | 小时/天级 | +OODA 持久世界模型 + 双通道进化 + 验证器过滤 |

**脚本：**
- `python3 scripts/self-evolution/post-task-evolve.py`
- `python3 scripts/self-evolution/proactive-search.py --experts all`

---

### 八、运行时监控（v2.6）

跨执行阶段的实时可观测性层，暴露 Prometheus 指标 + JSON API 端点 + 可视化仪表板。

#### Prometheus /metrics 端点

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `team_task_duration_seconds` | Histogram | team_id, phase, status | 任务执行耗时分布 |
| `team_circuit_breaker_state` | Gauge | team_id, agent_id | 熔断器状态(0=CLOSED, 1=HALF_OPEN, 2=OPEN) |
| `team_self_heal_attempts_total` | Counter | team_id, strategy, result | 自愈尝试次数及结果 |
| `team_expert_match_confidence` | Gauge | team_id, agent_id | 当前匹配置信度 |
| `team_rollback_events_total` | Counter | team_id, trigger | 回滚事件计数 |

#### 熔断器实时可视化

`python3 scripts/health-dashboard.py [--port 9090]` — 本地 Web 仪表板，展示各 Agent 熔断器状态、任务队列深度、失败率趋势。

#### JSON API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/teams` | 当前活跃团队列表及状态 |
| `GET /api/circuit-breakers` | 所有熔断器状态快照 |
| `GET /api/failures` | 失败模式聚合报表 |

#### 失败模式聚合报表

**脚本：** `python3 scripts/failure-analyzer.py summary [--since <time>] [--team <id>]`

输出 JSON：按故障类型聚合的计数、趋势、Top-N 高频 Agent 列表。支持 `--format markdown` 输出可读报告。

---

### 九、Agent 回滚自动化（v2.6）

当自愈机制无法恢复时，自动触发 Agent 状态回滚。

#### 快照引擎

`python3 scripts/rollback_manager.py` — 回滚管理入口：

| 命令 | 说明 |
|------|------|
| `rollback_manager.py snapshot <agent_id>` | 手动创建快照 |
| `rollback_manager.py list <agent_id>` | 列出可用快照 |
| `rollback_manager.py restore <agent_id> <snapshot_id>` | 回滚到指定快照 |

#### 愈合前快照策略

- 每次自愈尝试前自动创建快照（`auto_snap`）
- 验证失败（Layer 2 审核 🔴FAIL）后自动触发回滚
- 快照保留策略：最近 24h 全部保留，超过 24h 仅保留每日末次

#### Orchestrator 回滚钩子

- 失败任务 exit code ≠ 0 时自动触发 `rollback_manager.py restore <agent_id> latest`
- 回滚后自动重试（指数退避，最多 3 次）
- 回滚事件计入 Prometheus `team_rollback_events_total`
- **脚本：** `python3 scripts/memory-bridge.py resume-context` — 记忆桥接，回滚后恢复 Agent 上下文状态

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
| 五、自愈机制 | `references/self-healing-architecture.md` | 自愈架构设计（v2.4） |
| 五、自愈机制-专家研讨 | `references/problem-solving-panel.md` | 专家小组研讨管道（v2.5 new） |
| 六、反馈循环时 | `references/self-evolution-protocol.md` | 三环协议细节（v2.3 增强版） |
| 六、反馈循环时 | `references/loop-engineering-research.md` | Loop Engineering 完整调研报告 |
| 任意阶段 | `references/workbuddy-experts/_index.md` | 302 agents 完整索引 |
| 运行时监控时 | `references/health-monitoring.md` | 监控指标说明 |
| 需要时 | `references/first-principles.md` | 第一性原理框架 |
| 需要时 | `references/task-lifecycle.md` | 任务状态转场规范 |
| 需要时 | `references/handoff-protocol.md` | 交接协议 |
| 需要时 | `references/phase-gates.md` | 阶段关卡检查清单 |
| 需要时 | `references/patterns.md` | 多步骤工作流模式 |
| 需要时 | `references/communication.md` | Agent 通信模式 |
| 需要时 | `references/knowledge/` | 39 个领域知识文件 |
