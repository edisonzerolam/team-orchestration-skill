# 交叉验证模块 — 「孤证不立」的多源信息三角测量

## 设计背景

### 动机

Team Orchestration v2.1 的现有流程中，多个 subagent 并行收集信息后，经贝叶斯置信度聚合进入 Layer 1（自验证）→ Layer 2（审核）通道。**但缺乏一个关键环节**：对多 agent 收集的信息进行**系统性跨源交叉验证**。

「孤证不立」——单一来源的证据不足以确立事实。在多智能体协作中，这一原则对应一个基本问题：**当一个声明被多个 agent 确认时，这些 agent 是否真的引用了独立来源？** 还是他们共享了同一个上游数据、同一份文档、甚至是同一篇被错误引用的文章？

### 调研结论（互联网 + 学术研究）

| 方法论 | 来源 | 核心启示 |
|--------|------|---------|
| **三角互证法 (Triangulation)** | 社会学/教育研究方法论 / Webb et al. 1966 | 多种独立方法/来源交叉确认同一结论，可靠性与独立方法数量正相关 |
| **贝叶斯三角互证模型** | Cambridge Phil. of Science, 2024 | Jeffrey 条件化证明：多独立方法的收敛比单一方法更具解释力 |
| **Du Bois 投票模型** | LSE Research Online | 将三角互证建模为投票问题：三角互证策略优于"只信单一方法"的纯粹策略 |
| **Cross-Source Conflation** | Alvarez et al., 2026 (arXiv:2606.18037) | 声明在某处被支持但归因到错误来源——池化证据验证无法检测 |
| **ProvenanceGuard** | Alvarez et al., 2026 | Per-source 路由验证：每个原子声明路由到其声明来源独立检查 |
| **WHISTLE** | IJRPR, 2026 | 5-agent 验证：跨 agent 一致性(50%) + 验证强度(40%) + 推理一致性(10%) |
| **Co-Sight** | Zhang et al., 2025 | 冲突感知验证：只在分歧热点分配计算资源；结构化事实持续同步跨 agent 证据 |
| **CCA-F 信息溯源规则** | Anthropic, 2026 | Triangulation 需要**不同文档**（理想上不同来源层级），非同一文档不同 chunk |
| **Hydra 三因子验证** | arXiv:2505.17464 | 源可信度 + 跨源证实 + 实体路径对齐的三因子交叉 |
| **MAFC 多 agent 事实核查** | PMC / ScienceDirect, 2026 | 多 agent 各有独立信息源，用 BSC 信道模型量化不可靠性，加权阈值聚合 |

---

## 核心概念：孤证不立 → 可执行规则

将「孤证不立」转化为多 agent 编排中的 4 条可执行规则：

| # | 规则 | 含义 | 违反后果 |
|---|------|------|---------|
| R1 | **来源独立性** | 跨源验证要求**不同文档 + 不同编辑流程**，同一文档不同 chunk ≠ 独立来源 | false independence 误判 |
| R2 | **归因准确性** | 声明内容正确 ≠ 声明来源正确——内容可用池化验证，归因必须 per-source 独立检查 | attribute swapping |
| R3 | **置信度与来源数挂钩** | 单来源声明默认 uncertainty: medium；≥2 独立来源 → low uncertainty | 单一来源盲信 |
| R4 | **场景适配验证深度** | 高影响场景（投资/合规/医疗）强制三角测量；低影响场景可跳过或轻量验证 | 资源浪费或验证不足 |

---

## 失败模式矩阵（Covered by Design）

来自调研的 6 类关键失败模式，本设计逐一覆盖：

| 模式 | 机制 | 示例场景 | 检测手段 | 验证阶段 |
|------|------|---------|---------|---------|
| **属性交换** | 声明存在但归因错误 | 毛利率数据正确但来源误标 | Per-source 路由 NLI | triangulated |
| **单一源盲信** | 仅一个 agent 找到的信息以高置信度输出 | 爬虫缓存过时的 VAT 状态 | 来源计数 → 置信度上限 | confidence_scored |
| **虚假独立性** | 两 agent 信息来自同一上游 | 同一 TechCrunch 文章被计为两次独立验证 | document_id 去重 + 编辑链追踪 | independence_checked |
| **共享工具虚假共识** | 所有 agent 用同一搜索引擎产生表面一致 | 竞品分析全部来自同一知乎帖子 | 来源域重叠度检测 | independence_checked |
| **时间漂移盲区** | 信息过时但无时效标注 | 2024 上半年因子胜率用于当前配置 | 时间戳 + 版本约束匹配 | source_identified |
| **NLI 阈值穿透** | 语义接近文档使验证器无法区分 | 2024/2025 指南措辞差异未检出 | 版本感知 + 语义差异度阈值调整 | triangulated |

---

## 架构定位：Layer 1.5（新增层）

```
现有流程（v2.1）：
  [执行阶段] → 调度专家 → 收集产出 → 贝叶斯置信度聚合
                                        ↓
  NEW: [Layer 1.5 交叉验证] ← 此处插入
        声明提取 → 来源追溯 → 独立性检查 → 三角测量 → 冲突检测 → 置信度校准
                                        ↓
  [自验证 + 审核] → Layer 1 (专家自验证) → Layer 2 (@reviewer 审核)
```

### 与原架构的关系

| 层级 | 名称 | 范围 | 核心职责 | 输入 | 输出 |
|------|------|------|---------|------|------|
| **Layer 1** | 专家自验证 | 单 expert | 输出规范 + 置信度标注 + 红线检查 | 专家原始产出 | 带标注的产出 |
| **Layer 1.5** | 交叉验证（NEW） | 跨 expert 关系 | 声明提取→溯源→三角测量→冲突→评分 | 所有 Layer 1 产出 | CrossValidationResult |
| **Layer 2** | @reviewer 审核 | 整体 | 质量门控 | Layer 1 产出 + Layer 1.5 报告 | PASS / CONDITIONAL / FAIL |

**关键设计原则**：
- Layer 1.5 不修改 Layer 1 / Layer 2 的内部逻辑
- Layer 2 的输入增加 `CrossValidationResult` 作为参考
- Layer 1.5 失败或超时可跳过，不影响 1→2 的主流程

---

## 验证状态机

```
                    ┌──────────┐
                    │   raw    │   声明从专家产出中提取，未关联来源
                    └────┬─────┘
                         │ extract_provenance()
                    ┌────▼────────┐
                    │  source_    │   来源追溯完成：source_id, document_id,
                    │ identified  │   chunk_id, tier, timestamp
                    └────┬────────┘
                         │ check_independence()
                    ┌────▼─────────────┐
                    │ independence_    │   来源独立性验证：同源检测 + 编辑链追踪
                    │   checked        │   → 标记 dep_group / is_independent
                    └────┬─────────────┘
                         │ triangulate()
                    ┌────▼───────────┐
                    │  triangulated  │   ≥2 独立来源交叉验证：NLI 一致性检查
                    └────┬───────────┘
                         │ score_confidence()
                    ┌────▼────────────┐
                    │  confidence_    │   综合评分：一致性 + 验证强度 + 源层级加权
                    │    scored       │   → 输出校准后的 cross_confidence
                    └────┬────────────┘
                         │ resolve_conflicts()
                    ┌────▼─────────────┐
                    │  conflict_       │   冲突处理：resolved / unresolved / escalated
                    │   resolved       │   L3+ 未解决 → escalate
                    └────┬─────────────┘
                         │ layer2_review()
                    ┌────▼────────┐
                    │  reviewed   │   @reviewer 终审通过
                    └────┬────────┘
                         │ deliver()
                    ┌────▼──────────┐
                    │  delivered    │   交付用户 + 进入反馈循环
                    └───────────────┘
```

### 转场规则

| 转场 | 触发条件 | 失败处理 |
|------|---------|---------|
| `raw → source_identified` | 声明提取 + 来源关联完成 | 无法溯源 → 标记 `source_unavailable`，conf 上限 0.3 |
| `source_identified → independence_checked` | 同源检测完成 | chunk 同源 → 标记 dep_group，降权 |
| `independence_checked → triangulated` | ≥2 独立来源 | 仅 1 源 → 标记 `insufficient_sources`，conf 上限 0.5 |
| `triangulated → confidence_scored` | 三角测量完成 | 一致性 < 0.3 → 触发冲突解决 |
| `confidence_scored → conflict_resolved` | 冲突已处理 | L4 不可解 → escalate 到用户 |
| `conflict_resolved → reviewed` | 提交 Layer 2 | Layer 2 FAIL → 退回重做 |
| `reviewed → delivered` | PASS | — |

---

## 核心数据结构

### C1. `ClaimRecord` — 原子声明

交叉验证的最小单元——每个事实断言划分为一条声明。

```python
@dataclass
class ClaimRecord:
    claim_id: str                    # UUID
    task_id: str                     # 关联任务
    expert_id: str                   # 产出 agent
    text: str                        # 声明原文（原子级断言）
    claim_type: str                  # fact | judgment | prediction | numeric | causal
    status: str                      # raw → source_identified → ... → delivered
    created_at: datetime

    # 溯源信息
    provenance: list[SourceProvenance]

    # 置信度
    expert_confidence: float | None      # 专家自标注
    cross_confidence: float | None       # 交叉验证校准后
    confidence_breakdown: dict | None    # {consistency, verification, reasoning}

    # 冲突
    conflicts: list[str]                 # ConflictRecord IDs
    resolution_status: str               # consistent | conflict_resolved | contradiction_unresolved

    # Source Tier
    max_source_tier: int                 # 最高来源层级 (1-5)
    effective_tier: int                  # 加权有效层级
```

### C2. `SourceProvenance` — 来源溯源

```python
@dataclass
class SourceProvenance:
    source_id: str                     # UUID
    document_id: str                   # 文档/数据 ID
    chunk_id: str                      # 文档内具体位置
    url: str | None                    # 原始 URL
    access_time: datetime              # 访问时间
    tier: int                          # 来源层级 1(KG) ~ 5(社媒)
    is_independent: bool               # 是否独立来源
    independence_group: str | None     # 非独立时标记同源组
    reliability_score: float           # 历史可靠度 (0-1)
```

### C3. `CrossValidationResult` — 交叉验证结果

```python
@dataclass
class CrossValidationResult:
    validation_id: str
    task_id: str
    validation_depth: str              # skip | light | standard | deep
    executed_at: datetime
    duration_ms: int

    # 声明级
    claims_validated: list[str]
    claims_passed: list[str]
    claims_failed: list[str]
    claims_insufficient: list[str]

    # 聚合
    overall_confidence: float
    conflict_count: int
    resolved_conflicts: int
    unresolved_conflicts: int

    # 综合
    findings: list[ValidationFinding]
    recommendations: list[str]
```

### C4. `ConflictRecord` — 跨源冲突

```python
@dataclass
class ConflictRecord:
    conflict_id: str
    claim_ids: list[str]              # 冲突声明对
    conflict_type: str                # contradiction | misattribution | source_dependency | inconsistency
    severity: int                     # L1(信息缺失) ~ L4(核心矛盾)
    description: str

    # 仲裁
    resolution: str | None            # resolved | unresolved | escalated
    resolution_method: str | None     # source_hierarchy | majority_vote | expert_arbitration | user
    resolved_by: str | None
    resolved_at: datetime | None
    resolution_notes: str | None
```

---

## 验证深度路径（四档自适应）

### 四级深度

| 路径 | 验证内容 | 延迟增量 | 适用场景 | 触发条件 |
|------|---------|---------|---------|---------|
| **skip** | 不执行交叉验证 | +0ms | L1 简单任务，单专家直调 | 复杂度=L1 且 风险无 L2+ |
| **light** | 来源追溯 + 独立性检查 | +200~500ms | L2 中等任务 | 复杂度=L2 或 风险 ≤ L2 |
| **standard** | 全量三角测量 + 一致性评分 | +1~3s | L3 复杂任务 | 复杂度=L3 或 风险 = L3 |
| **deep** | 全量 + NLI per-source + 版本约束 | +5~15s | L4 关键任务（投资/合规/医疗） | 复杂度=L4 或 风险有 L4 |

### 自适应算法

```python
def determine_validation_depth(task: TaskAnalysis) -> str:
    # 基础 = 复杂度
    depth_map = {1: "skip", 2: "light", 3: "standard", 4: "deep"}
    depth = depth_map[task.complexity]

    # 预验尸风险修正
    max_risk = max(r.severity for r in task.risk_list)
    if max_risk >= 4 and depth == "light":
        return "standard"        # 风险升级
    if max_risk <= 1 and depth == "standard":
        return "light"           # 风险不足降级

    # 声明数量修正
    if estimate_claim_count(task) > 50 and depth == "deep":
        return "standard"        # 声明过多降档

    # 专家数量修正
    if len(task.matched_experts) == 1:
        return "light"           # 单专家无法跨源验证

    return depth
```

### 增量验证（Co-Sight 风格）

只对分歧热点做完整 NLI，高一致性声明直接通过：

```python
def validate_claims(claims: list[ClaimRecord]) -> CrossValidationResult:
    # 1. 快速一致性矩阵（embedding cosine similarity）
    # 2. similarity > 0.85 → 标记 consistent，跳过 NLI
    # 3. similarity < 0.6 → 分歧热点 → 分配 NLI
    # 预期：standard 路径减少 70%+ 验证成本
```

### 超时熔断

```python
TIMEOUT_MS = {"skip": 0, "light": 1000, "standard": 5000, "deep": 20000}

def run_bounded(depth: str, claims: list) -> CrossValidationResult:
    deadline = now() + TIMEOUT_MS[depth]
    result = CrossValidationResult(validation_depth=depth)
    for batch in batched(claims, 10):
        if now() > deadline:
            result.add_finding(f"超时：{len(remaining)} 声明未验证")
            break
        result += validate_batch(batch)
    return result
```

---

## 置信度评分算法

综合 WHISTLE 公式 + Hydra 三因子：

```
cross_confidence = w1 × consistency + w2 × verification + w3 × reasoning

其中：
  consistency  = 跨 agent 统一声明的一致性比例 (0-1)
  verification = 通过独立来源验证的声明比例 (0-1)
  reasoning    = 推理链中无断裂的比例 (0-1)
  w1=0.5, w2=0.4, w3=0.1

修正因子：
  × source_tier_factor (不同来源层级的加权)
  × independence_ratio (独立来源/总来源)
  × temporal_validity (时效性：最新时间 vs 当前时间)
```

### 置信度 → 风险等级映射

| cross_confidence | 等级 | 交付表现 | 说明 |
|-----------------|------|---------|------|
| ≥ 0.85 | 高可信 | ✅ 正常交付 | 多独立来源 + 一致 |
| 0.60 ~ 0.84 | 中等可信 | 🟡 标注「来源有限」 | 来源较少但一致 |
| 0.30 ~ 0.59 | 低可信 | 🔴 标注「需人工确认」 | 冲突或来源不足 |
| < 0.30 | 不可信 | 🚫 拦截，不退审 | 核心矛盾 |

---

## 与现有工作流的集成

### Layer 2 审核标准更新

在现有审核标准中增加一条：

```
审核标准 +1:
  若 CrossValidationResult.unresolved_conflicts > 0
    且 severity >= L3 → 自动标记 CONDITIONAL
  若 overall_confidence < 0.3 → 标记 FAIL
```

### 反馈循环

| 回路 | 触发条件 | 动作 |
|------|---------|------|
| 负反馈 | 交叉验证后用户指出遗漏的孤证 | 更新 validation 权重参数 |
| 正反馈 | 用户确认跨源验证有效拦截了错误 | 加深该 depth 的验证强度 |
| 校准 | 用户纠正置信度评分 | 调整 w1/w2/w3 权重 |

---

## 场景风险优先级

| 排序 | 团队模板 | 风险等级 | 交叉验证深度建议 |
|------|---------|---------|----------------|
| 1 | **投资分析** (investment-masters / a-share-analysis) | 极高 | deep（强制） |
| 2 | **风控合规** (risk-manager / financial-compliance) | 极高 | deep（强制） |
| 3 | **法务咨询** (chatlaw / enterprise-legal) | 高 | standard~deep |
| 4 | **代码审计** (engineering-assurance) | 高 | standard |
| 5 | **宏观/行业研究** (macro-analyst / industry-researcher) | 中~高 | standard |
| 6 | **量化策略** (quant-researcher) | 中~高 | standard |
| 7 | **综合报告** (synthesis-writer) | 中 | standard |
| 8 | **基金分析** (fund-analyst) | 中 | light~standard |
| 9 | **内容创作** (ai-content-creator) | 低~中 | light |
| 10 | **内容分发** (content-distribution) | 低 | skip~light |

---

## 实施建议

### 新增文件

| 文件 | 用途 |
|------|------|
| `scripts/cross-validator.py` | 验证编排核心（CLI + Python API） |
| `references/cross-validation.md` | 本文档 |
| `tests/test_cross_validator.py` | 验证单元测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `SKILL.md` | 核心工作流中插入 Layer 1.5 阶段 |
| `references/phase-gates.md` | 新增交叉验证关卡 |
| `references/self-evolution-protocol.md` | 交叉验证结果纳入事后回顾 |

### 与现有贝叶斯置信度聚合的关系

当前：执行阶段末尾的贝叶斯置信度聚合解决的是**单专家置信度校准**问题。
Layer 1.5 交叉验证解决的是**跨专家来源独立性验证**问题。
两者互补，输出合并后进入 Layer 1。

---

## 设计约束与权衡

| 约束 | 设计决策 |
|------|---------|
| 不阻塞主流程 | Layer 1.5 可超时熔断，跳过不影响 |
| 不增加用户配置负担 | 验证深度自动适配，用户无需手动选择 |
| 不重复验证 | 增量验证只验分歧热点 |
| 尊重专家独立性 | 不修改 Layer 1 逻辑，只新增 1.5 |
| 可审计 | 每个验证步骤有日志和状态记录 |
