# 审判庭核心架构（Trial Court Architecture v2）
> **DEPRECATED（v2.5 历史协议，已废弃）**：现行协议以 SKILL.md v3.1（三阶段 + A3 JSON）为准，本文档仅存档供历史参考。

> team-orchestration v2.5 核心架构建档。
> 将类审判庭协议升级为**技能默认运行机制**，每一议题必经审判庭四阶段流程，
> 并深度集成 WorkBuddy 全资产体系（技能/插件/MCP/专家团/连接器/未来扩展）。

---

## 0. 设计原则

| 原则 | 说明 |
|------|------|
| **审判庭优先** | 所有议题默认走审判庭流程（非可选），取代原来"讨论环节两种协议择一" |
| **资产即工具** | WorkBuddy 中已注册的 Skill / 插件 / MCP 工具 / 连接器 → 审判庭中的"工具箱"，按议题类型自动匹配 |
| **留痕可复现** | 每一轮举证、质证、裁决产物落盘 `deliverables/trial/`，全程可追溯 |
| **自学习闭环** | 每次审判产生结构化记录 → 积累到学习库 → 优化下一次匹配与调度 |
| **最小侵入** | 不破坏原有 10 步工作流的完整性，在其上叠加审判庭流程层（原步骤映射为审判庭的子阶段） |

---

## 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Trial Court Core Layer                                │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐              │
│  │  Phase A  │    │  Phase B  │    │  Phase C  │    │  Phase D  │              │
│  │  立案 &    │    │  举证     │    │  质证     │    │  终审裁决  │              │
│  │  争点拆解  │──► │  (并行)   │──► │  (并行)   │──► │  (独任)   │              │
│  └───────────┘    └───────────┘    └───────────┘    └───────────┘              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     Asset Bridge Layer                                    │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │   │
│  │  │ Skill   │ │ Plugin   │ │ MCP-Tool │ │Connector │ │ Expert   │        │   │
│  │  │ Resolver│ │ Resolver │ │ Resolver │ │ Resolver │ │ Resolver │        │   │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                     Self-Learning Layer                                    │   │
│  │  ┌───────────────┐ ┌──────────────────┐ ┌──────────────────────┐         │   │
│  │  │ 审判记录归档    │ │ 专家组调度优化     │ │ 反馈驱动的协议迭代    │         │   │
│  │  │ (trial_archive)│ │ (expert_tuning)  │ │ (feedback_loop)     │         │   │
│  │  └───────────────┘ └──────────────────┘ └──────────────────────┘         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 模块划分与职责

### 2.1 审判庭核心层（Trial Court Core）

| 模块 | 职责 | 主要接口 | 对应原工作流 |
|------|------|---------|------------|
| **Phase A: 立案 & 争点提取** (Docket) | 议题登记、模糊度检测、争点拆解、分配举证角色 | `docket(issue) → {docket_id, points[], roles[]}` | 原步骤一(目标明确)+步骤二(拆解) |
| **Phase B: 举证** (Evidence) | 并行拉起 N 个子代理独立举证、产物落盘 | `evidence_phase(docket_id, points[], roles[], assets[]) → P{i}(A)[]` | 原步骤三(预验尸)+步骤四(多代理判定)+步骤五(匹配)+步骤六(执行) |
| **Phase C: 质证** (Cross-Examination) | 打包分发产物、控制质证轮次、修正立场 | `cross_exam(docket_id, P_A[], max_rounds) → P{i}(B)[]` | 原步骤七(交叉验证) |
| **Phase D: 终审裁决** (Judgment) | 逐条采信/排除、产出终审意见书、落盘 | `judgment(docket_id, P_B[]) → verdict` | 原步骤八(自验证)+步骤九(交付) |

### 2.2 资产桥接层（Asset Bridge）

| 模块 | 职责 | 数据来源 |
|------|------|---------|
| **Skill Resolver** | 扫描 `~/.workbuddy/skills/` 已安装技能，按议题类型匹配合适技能 | 文件系统 |
| **Plugin Resolver** | 扫描 `~/.workbuddy/plugins/` 已安装插件（含专家团），提取能力描述 | 文件系统 |
| **MCP-Tool Resolver** | 读取 `connector-states.v3.json` 已连接 MCP 工具，列出可用工具集 | MCP 状态文件 |
| **Connector Resolver** | 读取连接器配置，识别已授权的外部服务（邮箱、行情、地图等） | 连接器配置 |
| **Expert Resolver** | 已通过 `workbuddy-experts/` 实现，增强匹配维度（加入历史绩效） | workbuddy-experts |
| **Future Resolver** | 预留扩展点，新资产类型只需实现 `resolver(issue_type) → assets[]` 接口 | 扩展点 |

### 2.3 自学习层（Self-Learning）

| 模块 | 职责 | 输出 |
|------|------|------|
| **审判记录归档** | 每次审判全流程存档（争点/举证/质证/裁决 + 所用资产） | `trial_archive/{yyyy-mm}/{docket_id}/` |
| **专家调度优化** | 跟踪各专家团在不同议题类型上的表现，动态调整匹配权重 | `expert_scores.json` + 匹配算法参数 |
| **反馈驱动迭代** | 用户对终审意见的反馈、使用中暴露的流程缺陷 → 自动更新协议文件 | `protocol_patches.md` |

---

## 3. 接口定义（API Surface）

### 3.1 审判庭核心接口

```python
# === Phase A: 立案 & 争点提取 ===
def docket_issue(issue: str, context: dict = None) -> DocketRecord
"""
输入：议题描述、可选的上下文（用户背景、历史议题）
输出：DocketRecord {
    docket_id: str,          # 唯一编号 e.g. "TC-2026-0727-001"
    issue_statement: str,    # 议题陈述（经5W2H澄清后）
    core_point: str,         # 核心争点（一句话）
    sub_points: list[str],   # 子争点列表
    roles: list[Role],       # 举证角色分配 [正方/反方/中立/...]
    assets_resolved: list[Asset],  # 该议题匹配的可用资产
    created_at: str
}
"""

# === Phase B: 举证 ===
def evidence_phase(docket: DocketRecord, sub_agents: list[Agent]) -> dict[str, Evidence]
"""
输入：立案记录、子代理列表
输出：{role_id: Evidence}  # 每个角色的举证产物
"""

# === Phase C: 质证 ===
def cross_examination_phase(
    docket: DocketRecord,
    evidence_map: dict[str, Evidence],
    sub_agents: list[Agent],
    max_rounds: int = 2
) -> dict[str, Evidence]
"""
输入：立案记录、举证产物、子代理列表、最大质证轮次
输出：{role_id: Evidence}  # 每方修正后的产物
"""

# === Phase D: 终审裁决 ===
def judgment_phase(
    docket: DocketRecord,
    final_evidence: dict[str, Evidence]
) -> Verdict
"""
输入：立案记录、终局质证产物
输出：Verdict {
    docket_id: str,
    rulings: list[Ruling],  # 逐条裁决
    conclusion: str,        # 终局结论
    dissenting: str,        # 存疑/遗留事项
    asset_usage: list[str]  # 本次用到的资产
}
"""
```

### 3.2 资产桥接接口

```python
def resolve_assets_for_issue(issue_type: str, docket: DocketRecord) -> ResolvedAssets
"""
输入：议题类型分类（08-FinanceInvestment / 11-SecurityCompliance 等）、立案记录
输出：ResolvedAssets {
    skills: list[Skill],      # 已安装且相关的技能
    mcp_tools: list[MCPTool], # 已连接且可用的MCP工具
    connectors: list[Connector],  # 已授权且相关的连接器
    expert_teams: list[ExpertTeam],  # 匹配的专家团
    plugins: list[Plugin],    # 相关插件
    summary: str              # 给主理人的人类可读摘要
}
"""

# 每个 Asset 的统一接口：
class Asset:
    name: str
    type: Literal["skill", "plugin", "mcp_tool", "connector", "expert", "future"]
    relevance_score: float      # 0.0 - 1.0
    capability_tags: list[str]  # ["financial", "legal", "search", ...]
    usage_hint: str            # 给主理人的使用建议
```

### 3.3 自学习接口

```python
def archive_trial(docket: DocketRecord, verdict: Verdict, logs: dict) -> str
"""归档整次审判记录，返回归档路径"""

def optimize_expert_scores(trial_archive_id: str) -> dict
"""根据上次审判结果更新专家评分"""

def generate_improvement_suggestions() -> list[Suggestion]
"""基于历史记录生成流程改进建议"""
```

---

## 4. 与现有 workbuddy-adaptation.md 的集成

| 现有组件 | 审判庭架构中的角色 | 变更 |
|---------|------------------|------|
| `references/workbuddy-adaptation.md` | 资产桥接层的专家团对接基础 | 新增资产桥接章节，原内容作为 Expert Resolver 的底层实现 |
| `scripts/expert-matcher.py` | 专家匹配，输入审判庭的议题类型 | 扩展输出为 `ResolvedAssets`（不仅含专家还含其他资产） |
| `scripts/dispatch-planner.py` | 生成 Mode B 派工方案 | Phase B 举证阶段调用它生成子代理方案 |
| `references/self-evolution-protocol.md` | 自学习层的三环基础 | 扩展为四层：原三环 + 审判庭级自学习 |
| `references/cross-validation.md` | Phase C 质证的核心方法论 | 质证阶段自动触发 Layer 1.5 交叉验证 |
| `references/phase-gates.md` | Phase D 终审的审核节点 | 终审意见书包含 Layer 1 + Layer 2 检查 |

---

## 5. 与原有 10 步工作流的映射

```
原 10 步工作流                         审判庭 4 阶段
─────────────────                     ──────────────
① 模糊度检测→澄清→目标重述            ─┐
② 子任务拆解→DAG→角色分配              ├→ Phase A 立案 & 争点拆解
③ 预验尸(5模式)                       ─┘
④ 多代理/多角度判定                     ─┐
⑤ 专家匹配                              ├→ Phase B 举证（满足审判庭触发条件自动走）
⑥ 执行→收集产出→聚合                   ─┘
⑦ 交叉验证 Layer 1.5                   ─→ Phase C 质证（含三角互证）
⑧ 自验证+审核 Layer 1 + Layer 2        ─┐
⑨ 交付 🟢/🟡/🔴                          ├→ Phase D 终审裁决
⑩ 反馈+自进化                           ─┘ (自学习层承接)
```

---

## 6. 调度策略

### 6.1 子代理数量策略

| 议题复杂度 | 建议子代理数 | 角色分配模式 |
|-----------|------------|------------|
| L1（简单查询） | 2-3 | 常规视角（归纳/分析/验证） |
| L2（中等分析） | 3-4 | 正方/反方/中立/专家 |
| L3（复杂决策） | 4-6 | 主理人 + 3-5 个专业领域视角 |
| L4（深度研判） | 5-8 | 主理人 + 多学科专家团（可跨团队组合） |

### 6.2 资产匹配策略

1. **议题类型提取**：从 `DocketRecord` 的 `sub_points` 中提取领域标签
2. **技能匹配**：检查 `~/.workbuddy/skills/<name>/SKILL.md` 的 description 是否匹配
3. **MCP 匹配**：检查已连接 MCP 的工具描述是否覆盖议题所需能力
4. **专家匹配**：用 `expert-matcher.py` 的 category_id 匹配（现有逻辑）
5. **综合评分**：按 `type` 加权（专家 0.4 / MCP 0.3 / 技能 0.2 / 连接器 0.1）

### 6.3 质证轮次控制

- **默认 1 轮**（标准三阶段：举证→质证→终审）
- 当 `max_rounds > 1` 且阶段 B 产物中分歧未收敛（分歧>2个关键点）→ 自动追加一轮
- 最大不超过 3 轮（避免无限循环）
- 终审保留所有轮次记录

---

## 7. 目录结构变化

```
references/
├── trial-court-architecture.md    <-- 本文件（新增）
├── trial-court-protocol.md        <-- 增强（核心协议）
├── workbuddy-asset-bridge.md      <-- 新增（资产桥接）
├── self-learning-mechanism.md     <-- 新增（自学习机制）
├── workbuddy-adaptation.md        <-- 增强（加入资产桥接章节）

scripts/
├── trial-court-orchestrator.py    <-- 新增（核心调度器）
├── asset-resolver.py              <-- 新增（资产解析器）
└── ... (原有脚本不变)

tests/
├── test_trial_court.py            <-- 新增（审判庭测试）
└── ... (原有测试不变)
```

---

## 8. 扩展性设计（Future-Proof）

```python
# 注册新的资产解析器（只需实现这个接口）：
class AssetResolver(ABC):
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def resolve(self, issue_type: str, docket: DocketRecord) -> list[Asset]: ...
    
    @abstractmethod
    def priority(self) -> int: ...  # 解析顺序，小优先

# 注册新的自学习插件：
class LearningPlugin(ABC):
    @abstractmethod
    def on_trial_complete(self, docket: DocketRecord, verdict: Verdict): ...
    
    @abstractmethod
    def on_feedback(self, docket_id: str, feedback: str): ...
```
