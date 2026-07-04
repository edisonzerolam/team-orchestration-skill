---
name: team-orchestration
version: 2.1.0
description: "多智能体团队编排引擎 v2 — 第一性原理拆解 + 28 个 WorkBuddy 专家团 + 动态匹配 + 三环自进化 + 自验证/审核门。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags:
  - orchestration
  - team
  - multi-agent
  - self-evolution
---

# Team Orchestration v2 — 多智能体团队编排

可用专家池：28 个 WorkBuddy 移植专家团（188 个子 Agent）+ 6 个原生 subagent。
完整索引见 `references/workbuddy-experts/_index.md`。

---

## 核心工作流（v2.1 — 思维方法论集成）

```
接到任务
  → [双系统分治] → 复杂度判断 → System 1（直调）/ System 2（团队路径）
      ↓
  → [第一性原理拆解] → python3 scripts/task-decomposer.py --task "..."
      ↓ 输出: π类型 + 知识域 + 复杂度
  → [预验尸检查] → 假设已失败 → 回溯风险 + 预设 fallback
      ↓ 输出: 风险清单 + 回退链路
  → [动态专家匹配] → python3 scripts/expert-matcher.py --domains ...
      ↓ 输出: 匹配专家列表 (含匹配度评分 + 置信度)
  → [选择执行路径]
      ├─ 快速路径: System 1 — 直接匹配合适的专家/模板
      ├─ 团队路径: System 2 — 组建团队 + 按 SOP 执行
      └─ 直调路径: System 1 — task(subagent_type=...) 单专家直调
      ↓
  → [执行阶段] 调度专家 → 收集产出 → 贝叶斯置信度聚合
      ↓
  → [自验证 + 审核] ← 强制节点
      ├─ Layer 1: 每个专家自验证 (输出规范检查 + 置信度标注)
      └─ Layer 2: @reviewer 交叉审核
           🟢 通过 → 交付
           🟡 附带标注 → 交付
           🔴 退回 → 最多 3 轮重审
      ↓
  → [结果交付 + 反馈循环 + 自进化触发]
      ├─ 负反馈: 失败分析 → 更新 expert-scores.json
      ├─ 正反馈: 高价值方向 → 加深探索
      ├─ Loop 1: 执行中反思 → 追加 self-evolution-log.md
      └─ Loop 2: 事后回顾 → 更新 expert-scores.json
```

---

## 一、第一性原理拆解 + 预验尸检查

使用 `references/first-principles.md` 的五维框架拆解任务本质，而非从模板匹配开始。

**步骤：**
1. 识别任务本质类型（信息检索/分析判断/创作生成/决策执行/混合）
2. 确定所需知识域（12 个 WorkBuddy 分类）
3. 评估复杂度（L1-L4）
4. **预验尸检查**（v2.1 新增）：假设执行已完成且失败，回溯回答「失败的最可能原因是什么？」
   - 输出风险清单（L1-L4 严重度）
   - 为每个高风险场景预设 fallback 链路
   - 风险等级 L3+ 的必须走团队路径（System 2）

**脚本：** `python3 scripts/task-decomposer.py --task "用户任务" --json`

---

## 二、动态专家匹配（含置信度校准）

根据拆解结果从专家池中匹配最合适的专家/团队。

**匹配维度：**
- 领域匹配度（35%）— 基于 `plugin.json` 的 `categoryId` 和 `displayDescription`
- 能力匹配度（30%）— 基于 Agent MD 的核心能力章节
- 历史表现分（20%）— 基于 `expert-scores.json`
- 负载惩罚（15%）— 当前会话已分配的专家数

**置信度校准（v2.1 新增）：**
- 每个匹配结果附带置信度分数（0-1）
- 置信度 < 0.6 → 标记「匹配不确定性高」，建议手动确认
- 历史表现证据强（>5次成功记录）→ 上调置信度
- 匹配成功后，根据实际执行结果通过负反馈更新置信度

**脚本：** `python3 scripts/expert-matcher.py --domains ... --json`

---

## 三、执行路径选择

**双系统路由规则（v2.1 新增）：**

| 复杂度 | System | 路径 | 触发条件 |
|--------|--------|------|---------|
| L1-简单 | System 1 | 直调路径 | 单维度、已知事实、低风险 |
| L2-中等 | System 1→2 | 快速路径 | 多维度但模板匹配度高 |
| L3-复杂 | System 2 | 团队路径 | 跨领域、需多轮推理 |
| L4-深度 | System 2 | 完整团队 | 需完整团队 SOP 执行 |

- 每次路径选择前先做复杂度判断
- System 1 执行中遇错 → 自动升级到 System 2
- 路径选择结果作为元数据记录到任务日志

### 快速路径（原 13 个模板，保留不动）

| 模板 | 触发词 | 简要流程 |
|------|--------|---------|
| software-team | 写代码、开发功能 | 产品→开发→测试 |
| investment-masters | 分析股票、投资分析 | 分析师并行→风控→决策 |
| research-team | 深度研究、写报告 | 初调→大纲→研究→审稿→发布 |
| a-share-analysis | A 股分析、股票研究 | 宏观+个股+资金 3 路并行 |
| fund-research | 基金分析、选基金 | 筛选→策略→风控 |
| strategy-audit | 审查策略、审计代码 | 代码审查+合规+风控 |
| expert-panel | 专家评审、小组讨论 | 独立分析→交叉审阅→辩论→裁决 |
| ai-content-creator | 内容创作 | 策划→生成→适配 |
| ai-data-copilot | 数据分析 | SQL→建模→可视化→报告 |
| chatlaw | 法律咨询 | 采集→法条→判例→建议→报告 |
| engineering-assurance | 工程保障 | 架构→审查→SRE→测试→文档 |
| content-distribution | 内容分发 | 策略→分析→排期 |
| enterprise-legal | 企业法务 | 合同→雇佣→隐私→监管→IP |

详见 `references/team-templates/`。

### 团队路径（WorkBuddy 专家团）

匹配到高评分的 WorkBuddy 专家团时，按该团队的 SOP 组建团队并执行：

1. 读取 `references/workbuddy-experts/{team}/` 的 `plugin.json` + 主理人 MD
2. 按主理人 MD 中的 SOP 阶段（Phase 1 → Phase 2 → ...）依次调度成员
3. 每个成员通过 `task(subagent_type="{agent-id}")` 执行
4. 成员产出通过 task 回传机制返回到主理人上下文
5. 主理人按 SOP 传递上下文、仲裁分歧、汇编最终结果

**主理人铁律（与 WorkBuddy 一致）：**
| R1 | 必须走正式团队协作流程 |
| R2 | 禁止自己代写成员专业产出 |
| R3 | 禁止跳过前序阶段 |
| R4 | 禁止成员间直连通信 |
| R5 | 禁止跳过检查关卡 |
| R6 | 禁止代替专家发言或辩论 |

### 直调路径

根据专家匹配结果，单专家可直接调用：
```
task(
  subagent_type="{agent-id}",
  prompt="完整任务描述 + 数据 + 产出要求"
)
```

---

## 四、自验证 + 审核节点（强制）

### Layer 1: 专家自验证（含置信度标注）

每个 subagent 执行完毕后，检查输出是否满足以下条件：
- 数据准确性：不虚构数据来源
- 格式合规：符合输出规范中定义的格式
- 完成度检查：验收标准是否达成
- 红线检查：没有违反该专家 MD 中定义的红线
- **置信度标注**（v2.1 新增）：每个核心结论必须标注置信度（高/中/低）
  - 低置信度结论 → 标记「不确定」并说明需要什么额外信息
  - 不标注的结论 → 默认视为中等置信度，审核时重点核查

自验证结果记录在专家目录下的 `self-evolution-log.md`。

### Layer 2: 审核

所有 subagent 产出汇总后，必须经过 `@reviewer` 审核：

```
🟢 PASS → 直接交付用户
🟡 CONDITIONAL → 附带标注问题后交付
🔴 FAIL → 退回修改（最多 3 轮）
```

对于不同产物类型：
- **分析/报告类** → 检查数据准确性、逻辑一致性、引用完整
- **代码/配置类** → 检查语法正确性、功能完整性、安全合规
- **金融/投资类** → 检查数据源标注、免责声明、核心结论与数据一致

---

## 五、反馈循环 + 三环自进化（v2.1）

### 反馈循环机制（新增）

| 回路类型 | 触发条件 | 动作 | 增益控制 |
|---------|---------|------|---------|
| **负反馈** | 专家匹配失败/输出不合格 | 分析根因 → 调整匹配权重或 prompt | 降权不摘除，连续 3 次失败才冷却 |
| **正反馈** | 匹配准确率高/用户明确认可 | 加深该方向探索 → 增加同类专家优先 | 不过度偏食，保留多样性 |
| **用户纠正** | 用户提出修改意见 | 记录偏误模式 → 当前会话不再重复 | 不因一次纠正否定整个方向 |

### Loop 1: 执行中反思（快速，每次执行）

每个 subagent 执行完毕后自动追加到 `self-evolution-log.md`：
- 任务简述、时间戳
- 有效方法、缺失数据
- 改进建议
- 置信度自评

### Loop 2: 事后回顾（中速，每次任务后）

```bash
python3 scripts/self-evolution/post-task-evolve.py
```
- 收集所有参与专家的日志
- 更新 `expert-scores.json`
- 生成跨专家学习建议

### Loop 3: 主动联网增强（慢速，手动触发）

```bash
python3 scripts/self-evolution/proactive-search.py --experts all
```
- 为每个专家生成搜索词
- 搜索互联网获取最新信息
- 生成进化报告由用户审核
- 审核通过后：`python3 scripts/self-evolution/knowledge-merger.py --expert ... --source ...`

---

## 六、参考文件

| 文件 | 用途 |
|------|------|
| `references/first-principles.md` | 第一性原理拆解框架（v2 new） |
| `references/expert-matching.md` | 专家匹配评分算法（v2 new） |
| `references/self-evolution-protocol.md` | 三环自进化协议（v2 new） |
| `references/workbuddy-experts/_index.md` | 28 个专家团完整索引（v2 new） |
| `references/workbuddy-experts/{team}/` | 各专家团详细定义（188 agents） |
| `references/task-lifecycle.md` | 任务状态、转场规范 |
| `references/handoff-protocol.md` | 交接协议详情 |
| `references/phase-gates.md` | 阶段关卡 + 检查清单 |
| `references/patterns.md` | 多步骤工作流模式 |
| `references/communication.md` | Agent 通信模式 |
| `references/knowledge/` | 39 个领域知识文件 |
| `references/team-templates/` | 10 个团队模板 |
| `C:/Users/林昌/.config/opencode/AGENTS.md` | 全局 P0 核心方法论（思维方法论核心集章节） |

---

## 七、思维方法论集成（v2.1 新增）

本 skill 内置了从 70+ 思维原理中提炼的 P0 核心方法论，自动在编排流程中生效：

| 方法论 | skill 中对应位置 | 生效方式 |
|--------|----------------|---------|
| **双系统理论** | 核心工作流第一步 + 三、执行路径选择 | 任务复杂度判断自动分流 |
| **第一性原理** | 一、第一性原理拆解（内置） | 五维框架拆解任务本质 |
| **奥卡姆剃刀** | 各阶段 → 最小必要团队/最少步骤 | 不引入冗余专家或阶段 |
| **预验尸法** | 一、拆解后新增预验尸检查 | 每任务输出风险清单 + fallback |
| **反馈循环** | 五、反馈循环 + 三环自进化 | 负反馈纠错 + 正反馈深化 |
| **贝叶斯置信度** | 二、动态专家匹配（置信度校准）+ 四、自验证（置信度标注） | 匹配/输出均带置信度分数 |

主理人不需要手动触发这些方法论，它们已嵌入工作流的各个节点。每次编排自动执行。
