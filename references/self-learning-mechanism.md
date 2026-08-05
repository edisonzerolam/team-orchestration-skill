# 自学习机制（Self-Learning Mechanism）

> 在原有三环自进化协议之上，增加审判庭级的四层自学习架构。
> 原有 Loop 1/2/3 保持，叠加新的审判学习层。

---

## 1. 整体架构

```
原有三环                         新增审判庭自学习层
─────────                       ─────────────────────
Loop 1: 执行中反思               Layer S1: 审判记录归档
Loop 2: 事后回顾                 Layer S2: 专家调度优化
Loop 3: 主动联网增强              Layer S3: 反馈驱动改进
                                  Layer S4: 跨议题知识积累
```

**关系**：原三环以"智能体执行"为中心，四层以"审判庭议题处理"为中心，两者互补。

---

## 2. Layer S1: 审判记录归档

### 2.1 归档内容

每次审判庭流程完成后，归档到 `deliverables/trial/archive/`：

```
trial_archive/{yyyy-mm}/{docket_id}/
├── 00-案卷信息.json           # 元数据：议题、时间、所用资产
├── 01-争点清单.md             # Phase A 产出
├── 02-举证/                   # Phase B 所有子代理产物
│   ├── P1-正方.md
│   ├── P2-反方.md
│   └── P3-中立.md
├── 03-质证/                   # Phase C 质证记录
│   ├── P1-B-质证.md
│   └── ...
├── 04-终审意见书.md           # Phase D 产出
├── 05-资产使用记录.json        # 用了哪些资产、效果如何
└── 06-反馈记录.json            # 用户反馈（如有时）
```

### 2.2 案卷信息 JSON 结构

```json
{
  "docket_id": "TC-2026-0727-001",
  "issue": "我国二审终审制与举证辩论制度评估",
  "issue_type": "11-SecurityCompliance",
  "created_at": "2026-07-27T11:00:00+08:00",
  "complexity": "L3",
  "sub_agent_count": 3,
  "cross_exam_rounds": 1,
  "assets_used": {
    "expert_teams": ["chatlaw-team"],
    "mcp_tools": [],
    "skills": [],
    "connectors": []
  },
  "assets_suggested_but_unused": [],
  "key_disagreements_resolved": 6,
  "key_disagreements_remaining": 0,
  "user_feedback": null,
  "improvement_suggestions": []
}
```

---

## 3. Layer S2: 专家调度优化

### 3.1 评分数据结构

```json
{
  "expert_team_scores": {
    "a-share-analysis": {
      "total_trials": 12,
      "avg_relevance": 0.87,
      "avg_evidence_quality": 0.82,
      "avg_judgment_agreement": 0.78,
      "by_issue_type": {
        "08-FinanceInvestment": {
          "trials": 8,
          "avg_score": 0.91
        },
        "02-Engineering": {
          "trials": 4,
          "avg_score": 0.62
        }
      },
      "last_used": "2026-07-27"
    }
  },
  "mcp_tool_scores": {
    "tdx-connector": {
      "total_trials": 10,
      "avg_contribution": 0.85,
      "by_issue_type": {
        "08-FinanceInvestment": {
          "trials": 10,
          "avg_contribution": 0.85
        }
      }
    }
  },
  "skill_scores": { ... },
  "connector_scores": { ... }
}
```

### 3.2 调度优化算法

```python
def calculate_adjusted_weight(base_weight: float, historical_scores: dict) -> float:
    """
    基准权重 × 历史表现调优
    """
    if not historical_scores:
        return base_weight  # 无历史数据，用默认权重
    
    performance_factor = historical_scores.get("avg_relevance", 0.5)
    confidence = min(historical_scores.get("total_trials", 0) / 10, 1.0)  # 10次以上置信度高
    
    # 加权：基准权重 + 表现偏差 × 置信度
    adjusted = base_weight + (performance_factor - 0.5) * 0.3 * confidence
    
    return max(0.1, min(1.0, adjusted))  # 钳位在 0.1-1.0
```

### 3.3 调度策略自调整

| 观察项 | 触发条件 | 调整动作 |
|-------|---------|---------|
| 某专家团连续 3 次匹配但未被最终选用 | `match_count >= 3 AND selected_count == 0` | 降低该团在该议题类型的权重 20% |
| 某 MCP 工具在 5 次以上审判中被提示但从未被使用 | `suggested >= 5 AND used == 0` | 从该议题类型的"活跃提示"降级为"备用" |
| 某技能与某议题类型配对使用后用户明确好评 | `user_feedback == "positive"` | 建立强配对，下次该议题类型自动推荐该技能 |
| 某专家团在某一子议题上连续产出"存疑"标注 | `doubtful_ratio > 0.5 over last 3 trials` | 自动为该类型议题追加一个补充专家团 |

---

## 4. Layer S3: 反馈驱动改进

### 4.1 反馈录入点

```python
FeedbackSource:
    EXPLICIT: "用户对终审意见书打 👍/👎"
    IMPLICIT: "用户跳过质证直接问结论 → 流程过长"
    CORRECTION: "用户纠正了某项事实错误 → 源头追溯"
    REUSE: "用户复用某次终审结论 → 价值确认"
```

### 4.2 反馈驱动的协议改进

```python
def process_feedback(feedback: Feedback, trial_archive: dict):
    """
    根据反馈类型触发相应改进
    """
    if feedback.type == "CORRECTION":
        # 修正来源追溯：是子代理编造？还是 MCP 返回错误？
        root_cause = trace_error_source(feedback.correction_detail, trial_archive)
        if root_cause == "FABRICATION":
            # → 加强该子代理 prompt 中的"严禁虚构"约束
            update_protocol_prompt("subagent_constraint", "evidence_phase")
        elif root_cause == "MCP_ERROR":
            # → 添加 MCP 数据验证步骤
            update_protocol_prompt("mcp_validation", "cross_exam_phase")
    
    elif feedback.type == "EXPLICIT" and feedback.sentiment == "NEGATIVE":
        # 分析哪一阶段最可能引起负面评价
        weak_phase = analyze_weak_phase(trial_archive)
        # → 在该阶段追加"主理人复核"步骤
        add_review_gate(weak_phase)
    
    elif feedback.type == "REUSE":
        # 确认该类型议题的审判流程质量达标
        mark_issue_type_as_validated(trial_archive["issue_type"])
```

### 4.3 协议迭代版本管理

```
protocol_patches.md 格式：
| 版本 | 日期 | 变更来源 | 变更内容 |
|------|------|---------|---------|
| v2.5 | 2026-07-27 | 初始发布 | 审判庭协议升级为核心机制 |
| v2.5.1 | 2026-08-xx | 反馈 S3-001 | 举证实例子代理 prompt 追加"来源验证步骤" |
```

---

## 5. Layer S4: 跨议题知识积累

### 5.1 知识积累类型

| 类型 | 内容 | 存储位置 |
|------|------|---------|
| **裁决摘要** | 每次终审意见的精简摘要 | `trial_archive/{yyyy}/裁决摘要.md` |
| **常据库** | 多次审判中反复出现的事实依据 | `references/knowledge/trial-common-facts.md` |
| **争议图** | 常见分歧点的各方主张与最终裁决 | `references/knowledge/dispute-map.md` |
| **模式库** | 审判流程中有效的 prompt 模式 | `references/knowledge/prompt-patterns.md` |

### 5.2 跨议题推荐

```python
def recommend_for_new_issue(new_issue: str) -> dict:
    """
    基于历史审判记录，对新议题给出推荐：
    - 建议使用哪些专家团（基于历史匹配度）
    - 建议使用哪些 MCP 工具（基于历史贡献）
    - 建议参考哪些历史裁决（基于议题相似度）
    """
    similar_trials = find_similar_trials(new_issue, top_k=3)
    recommended_teams = aggregate_team_scores(similar_trials)
    recommended_tools = aggregate_tool_usage(similar_trials)
    
    return {
        "similar_trials": similar_trials,
        "recommended_teams": recommended_teams,
        "recommended_tools": recommended_tools,
        "reusable_evidence": extract_common_facts(similar_trials)
    }
```

---

## 6. 与原有三环自进化的集成

| 原有组件 | 新增对接 | 时机 |
|---------|---------|------|
| `self-evolution-protocol.md` | 读取审判记录归档中的资产使用数据 | Phase D 完成后 |
| `scripts/self-evolution/post-task-evolve.py` | 新增 `--trial-docket` 参数，输入审判记录 | 任务完成后手动触发 |
| `scripts/self-evolution/proactive-search.py` | 按议题类型触发，而非全量专家 | 定时/按需 |
| `references/workbuddy-experts/<团队>/self-evolution-log.md` | 记录该团队在审判庭中的表现 | 每次使用后追加 |
| `expert-scores.json` | 由 Layer S2 更新（补充审判庭维度） | 每次终审后 |

---

## 7. 快速启动指南

第一次启用自学习：

```
# 1. 创建归档目录
mkdir -p deliverables/trial/archive/

# 2. 初始化解锁评分表
python3 scripts/trial-court-orchestrator.py --init-learning

# 3. 查看当前学习状态
python3 scripts/trial-court-orchestrator.py --learning-status

# 4. 查看改进建议
python3 scripts/trial-court-orchestrator.py --improvements
```
