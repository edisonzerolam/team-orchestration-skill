# 类审判庭核心机制（Trial Court）
> **现行补充协议（Trial Court）**：本文档为团队编排的**完整审判庭协议细节**。SKILL.md v3.1 三阶段（立案→并行举证→质证+终审）是四阶段的精简视图；本文档为四阶段的展开执行规范（含案卷归档、自学习 S1/S2、终审六段式）。

> team-orchestration v2.5 默认运行机制。每一议题满足触发条件即走审判庭四阶段，
> 深度集成 WorkBuddy 全资产体系（技能/插件/MCP/专家团/连接器），确保
> **结论有依据、分歧有留痕、裁决可追溯**。
>
> **自动触发条件**（满足任一）：① 派出 >1 个子代理；② main agent 与 ≥1 子代理协作；③ main agent 多角度执行任务。

---

## 1. 核心原则

| 原则 | 说明 |
|------|------|
| **审判庭优先** | 满足触发条件即默认走四阶段（非可选），原 10 步工作流映射为其子阶段 |
| **信息公开** | 每阶段产物对所有参与方可见，**裁决权唯一归 main agent（审判长）** |
| **资产即工具** | 已注册 Skill/插件/MCP/连接器/专家团 → 按议题类型自动匹配，注入子代理 prompt |
| **严禁虚构** | 所有依据必须真实可核验，存疑项如实标注"存疑/待核" |
| **全程留痕** | 每轮产物落盘 `deliverables/trial/{docket_id}/`，供审计与自学习 |
| **自学习闭环** | 每次审判产生结构化记录 → 积累学习库 → 优化下次匹配与调度 |

---

## 2. 架构总览

```
┌────────────────────── Trial Court Core Layer ──────────────────────┐
│ Phase A 立案&争点拆解 ─► Phase B 举证(并行) ─► Phase C 质证(并行) ─► Phase D 终审(独任) │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
  Asset Bridge Layer: Skill / Plugin / MCP-Tool / Connector / Expert / Future Resolver
                               ▼
  Self-Learning Layer: 审判记录归档(trial_archive) / 专家调度优化(expert_tuning)
                       / 反馈驱动迭代(feedback_loop)
```

---

## 3. 角色映射

| 司法类比 | 工程实现 | 由谁充当 | 职责 |
|---------|---------|---------|------|
| 审判长 | **main agent（主理人）** | 当前主 agent | 立案、控轮次、汇总产物、**终局裁决** |
| 举证方 | **子代理（正/反/中立）** | Agent 工具拉起的 general-purpose | 独立举证、质证他方、据反驳修正、提交产物 |
| 书记员 | main agent 兼任 | — | 记录每轮产物、归档审判记录 |
| 法警 | 资产桥接层 | Asset Resolver 自动 | 匹配并将可用资产注入子代理 prompt |
| 陪审团 | 自学习层 | — | 历史裁决记录影响未来匹配 |

---

## 4. 四阶段流程

```
Phase A 立案 & 争点拆解（main 独任）
  议题登记 → 模糊度检测 → 争点提取 → 角色分配 → 资产匹配
  产出 DocketRecord + 争点清单 + ResolvedAssets → 落盘 00-立案/
Phase B 举证（子代理并行）
  同一消息并行拉起 2-6 个子代理，prompt 含角色分工+举证要求+产物模板+可用资产
  产出 P{i}(A) → 落盘 01-举证/
Phase C 质证（子代理并行）
  汇总 B 产物 → 打包分发 → 逐条质证他方 → 修正己方立场 → 再提交
  产出 P{i}(B)；争议未收敛自动追加一轮（最多 3 轮）→ 落盘 02-质证/
Phase D 终审裁决（main 独任）
  逐条采信/排除 → 终审意见书 → 记录资产使用 → 触发自学习归档
  落盘 03-终审/ → 归档 deliverables/trial/archive/{yyyy-mm}/{docket_id}/
```

### 4.1 Phase A 立案要点
1. **议题登记**：生成 `docket_id`（格式 `TC-{YYYYMMDD}-{序号}`）
2. **模糊度检测**：5W2H 检测，模糊则向用户澄清（≤2 轮）
3. **争点提取**：1 条核心争点 + 2-6 条可独立举证的子争点
4. **角色分配**：见 §6.1 子代理数量策略
5. **资产解析**：`resolve_assets_for_issue(issue_type, docket)`，结果注入 Phase B prompt

### 4.2 Phase B 举证要点
- 对每个角色编写 prompt（角色分工/举证要求/可用资源/产物模板），**同一消息内并行**发起 N 个 Agent 调用
- 子代理独立举证，可联网/调 MCP/用技能，经返回值回传 main

### 4.3 Phase C 质证要点
- 收齐 `P{i}(A)` 打包为完整上下文，再次对每个子代理发起调用
- 收齐后判断收敛：分歧点 ≤1 → 进 Phase D；>1 → 追加一轮（≤3 轮）
- 自动触发 Layer 1.5 交叉验证：多来源主张检查来源独立性，单来源标注"中等置信度"，冲突点标注"分歧未收敛"

### 4.4 Phase D 终审要点（不再派发子代理）
- 汇总最新一轮 `P{i}(B)`，对每条子争点逐条裁断：采信 / 部分采信 / 排除
- 终审意见书结构：① 案卷信息 ② 争点回顾 ③ 逐条裁决 ④ 终局结论 ⑤ 存疑/遗留事项 ⑥ 资产使用评价
- 终审结论作为主工作流"交付"环节输入，触发自学习归档（Layer S1+S2）

---

## 5. Prompt 结构模板

### 5.1 举证 Prompt（Phase B）
```markdown
## 角色：{角色名}
你是本次审判庭的「{角色名}」，专业领域：{领域}
### 议题
{核心争点}
### 你的立场分工
{具体举证方向}
### 举证要求
1. 结论先行，然后展示依据
2. 每条依据必须标明来源（法条/文献/数据源/URL）
3. 严禁虚构，存疑标注"存疑/待查"
4. 这是第一轮举证，稍后你会收到其他方产物并需要质证
### 可用资源
{由 Asset Resolver 动态生成，见 workbuddy-asset-bridge.md §5}
### 产物格式
## 产物 P{i}（阶段 B）— 角色：{角色名}
### 一、核心主张
### 二、举证依据（表格：| # | 依据/事实 | 来源 | 可信度 |）
### 五、给审判长的裁决建议
```

### 5.2 质证 Prompt（Phase C）
```markdown
## 阶段 C: 交叉质证 — {角色名}
你已经完成了第一轮举证。现在审判长把其他方的产物全部交给你。
### 质证要求
1. 对他方产物逐条质证：哪些依据可信？哪些有偏颇？哪些遗漏了有利于你方的事实？
2. 修正己方立场：撤回站不住的主张 / 加强可坚守的主张 / 补充新的反驳依据
### 其他方产物全文
{此处插入其他方全部举证产物}
### 产出格式
## 产物 P{i}（阶段 C）— 角色：{角色名}
### 一、对他方质证意见
### 二、己方立场修正
### 三、修正后的终局建议
```

---

## 6. 调度策略

### 6.1 子代理数量策略

| 议题复杂度 | 建议子代理数 | 角色分配模式 |
|-----------|------------|------------|
| L1（简单查询） | 2-3 | 常规视角（归纳/分析/验证）或 正方/反方 |
| L2（中等分析） | 3-4 | 正方/反方/中立/专家（默认 3 方） |
| L3（复杂决策） | 4-6 | 主理人 + 3-5 个专业领域视角 |
| L4（深度研判） | 5-8 | 主理人 + 多学科专家团（可跨团队组合） |

### 6.2 资产匹配策略
1. **议题类型提取**：从 `DocketRecord.sub_points` 提取领域标签
2. **技能匹配**：检查 `~/.workbuddy/skills/<name>/SKILL.md` description
3. **MCP 匹配**：检查已连接 MCP 工具描述是否覆盖议题所需能力
4. **专家匹配**：`expert-matcher.py` 的 category_id 匹配
5. **综合评分**：按 type 加权（专家 0.4 / MCP 0.3 / 技能 0.2 / 连接器 0.1）

### 6.3 质证轮次控制
- 默认 1 轮；`max_rounds > 1` 且分歧未收敛（>2 个关键点）→ 自动追加；最大 3 轮；终审保留所有轮次记录

---

## 7. 质量门禁

- **终审意见书必须包含资产使用评价**（没用任何资产也要说明原因）
- **严禁在终审中引入新论点**（未在举证/质证中出现的主张不可采信）
- **每轮质证产物必须标注"相比上一轮的变与不变"**
- **终审结论的可信度 = 最低可信度依据的可信度**（最薄弱的证据决定整体质量）

---

## 8. 接口与自学习

```python
# 审判庭核心接口
def docket_issue(issue, context=None) -> DocketRecord       # Phase A
def evidence_phase(docket, sub_agents) -> dict[str, Evidence]   # Phase B
def cross_examination_phase(docket, evidence_map, sub_agents, max_rounds=2) -> dict  # Phase C
def judgment_phase(docket, final_evidence) -> Verdict        # Phase D

# 资产桥接
def resolve_assets_for_issue(issue_type, docket) -> ResolvedAssets
class Asset:  # name / type / relevance_score / capability_tags / usage_hint

# 自学习接口
def archive_trial(docket, verdict, logs) -> str             # 归档整次审判记录
def optimize_expert_scores(trial_archive_id) -> dict        # 更新专家评分
def generate_improvement_suggestions() -> list[Suggestion]  # 流程改进建议
```

**扩展点**：新资产类型实现 `AssetResolver.resolve(issue_type, docket) -> list[Asset]`；
新自学习插件实现 `LearningPlugin.on_trial_complete()` / `on_feedback()`。

---

## 9. 与原 10 步工作流映射

| 原工作流 | 审判庭映射 | 执行者 |
|---------|-----------|-------|
| ① 目标明确 / ② 强化拆解 / ③ 预验尸 | Phase A 模糊度检测+争点拆解+角色分配+风险预判 | main |
| ④ 多代理判定 / ⑤ 专家匹配 | Phase A 触发判定 + 资产解析 | main / Asset Resolver |
| ⑥ 执行 | Phase B 举证 | 子代理 |
| ⑦ 交叉验证 | Phase C 质证 + Layer 1.5 | 子代理 + main |
| ⑧ 自验证+审核 / ⑨ 交付 | Phase D 终审裁决（Layer 1+2）→ 交付用户 | main |
| ⑩ 反馈+自进化 | Phase D 触发自学习归档 | 自学习层 |
