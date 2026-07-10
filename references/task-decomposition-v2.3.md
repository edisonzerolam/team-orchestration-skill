# 任务拆解框架 v2.3 — 结构化分析设计文档

> 系统架构分析师 | 基于 Team Orchestration Skill 现有五维分类框架的增强设计

---

## A. Gap 分析：从「分类」到「拆解」的缺失环节

### A.1 分类 ≠ 拆解

当前 v2.x 框架本质是一个**分类器**：给定一个任务，输出 π 类型 + 知识域 + 复杂度的元标签。这三个标签描述了任务的"相貌"，但没有描述任务的"骨骼"——它无法回答"具体先做什么、再做什么、每步的交付物是什么"。一个 π 类型为"分析判断"、知识域为"量化金融"、复杂度 L3 的任务，可以是一篇研报、一个回测框架、一个归因分析或一个风险模型，它们的执行步骤完全不同。分类标签**泛化过度**，丢失了任务的结构信息。

### A.2 缺失子任务清单的后果

没有显式的子任务清单，下游 Agent（或 human-in-the-loop）就缺乏执行锚点。实践中表现为：
- **发散模式中的 Omissions**：Agent 倾向于跳步，尤其会跳过"非典型"但关键的步骤（如数据质量检查、边界条件验证）
- **Sequencing 混乱**：没有依赖约束时，Agent 可能先做 B 再做 A，导致返工
- **Agent 幻觉放大**：缺乏结构化约束时，自由生成空间太大，更易坍缩到似是而非的路径

### A.3 缺少验收标准导致「做完了」定义模糊

每个子任务没有验收标准（Acceptance Criteria），意味着：
- **无法确认完成**：Agent 认为做完了但 Human 不认，来回拉扯
- **质量不可观测**：输出形式、精度、引用要求未约定，Agent 按默认模式输出，不匹配任务需求
- **回归不可审计**：失败后无法定位到具体子任务，只能整锅重来

### A.4 人机分工模糊

当前输出不区分"哪些步需要人决策、哪些步可自动执行"。这导致：
- 需要人介入的地方 Agent 擅自往前推，产生不可逆错误
- 可以自动执行的地方 Agent 停下来等人确认，浪费轮次
- 尤其在高风险的 L3/L4 任务中，没有明确的人机切换点会直接导致信任崩塌

### A.5 依赖关系缺失阻塞并行化

没有依赖图，就无法识别：
- 哪些子任务可并行（减少执行时间）
- 关键路径在哪里（决定总工期）
- 哪个子任务失败会导致整体失败（风险隔离点）

缺少这些信息，P3 分解后的派发只能是串行顺序执行，浪费多 Agent 并行的潜力。

---

## B. 目标明确模块设计

### B.1 模糊度检测方法（5 种）

| # | 检测方法 | 检测内容 | 触发条件示例 |
|---|---------|---------|------------|
| ① | **5W2H 覆盖率扫描** | 检查用户输入覆盖了多少个 W/H 维度 | 覆盖 ≤4/7 个维度 → 模糊 |
| ② | **语义坍缩探查** | 对同一输入生成 2-3 种不同解释，计算解释间的语义距离 | 解释间 Jaccard 距离 <0.3 → 严重欠规约 |
| ③ | **边界模糊词匹配** | 匹配「适当」「优化」「更好」「改进」「处理」等开放词 | 出现 ≥2 个 → LLM 自由度过大 |
| ④ | **验收标准可测性检查** | 用户是否给出了可量化的成功标准 | 无量化指标 → 模糊 |
| ⑤ | **发散模式预扫描** | 用发散 5 模式逐项检查用户输入是否易被误解 | 误解释风 ≥3/5 → 需要澄清 |

**检测执行流程**：先跑一次 ①②③ 做快速筛查，快筛未通过则启用 ④⑤ 做深度检测。深度检测结果决定是否需要追问。

### B.2 澄清追问策略

**轮次上限**：最多 2 轮追问。单轮能消歧的不用第二轮。

**策略选择矩阵**：

| 检测结果 | 追问策略 | 策略说明 |
|---------|---------|---------|
| 轻度模糊（覆盖 5-6/7 维度） | 单轮段落式 | 合并缺失维度在一轮中补全 |
| 中度模糊（覆盖 3-4/7 维度） | 单轮结构化 | 对每个缺失维度输出选择题或填空模板 |
| 重度模糊（覆盖 ≤2/7 维度） | 多轮渐进式 | 第一轮缩小 scope，第二轮补细节 |
| 语义坍缩（高解释分歧） | 反问式 | "我理解您要 A，但也可以理解为 B 或 C，您是指哪一个？" |

**追问输出格式要求**：
```
[模糊检测结果]
- 已覆盖维度: What, Why
- 缺失维度: Who, When, Where, How, How Much
- 语义坍缩风险: 高（至少3种冲突解释）

[追问]
1. 目标产出是什么（What）：报告/代码/配置/其他？
2. 谁使用/谁审批（Who）：自用/团队/客户？
3. 完成期限（When）：有无硬性截止日期？
4. 交付范围（Where）：覆盖哪些模块/系统？
5. 实施方法（How）：有无首选技术路线？
6. 质量标准和量化指标（How Much）：精度要求、引用格式等？
```

### B.3 目标重述格式

澄清完成后，必须输出以下结构化的目标重述，**经用户确认后**再进入拆解阶段：

```json
{
  "goal_restatement": {
    "what": "构建一个A股多因子选股回测框架",
    "why": "验证季度调仓策略的夏普比率和最大回撤，辅助投资决策",
    "who": {
      "creator": "AI Agent（量化研究员）",
      "reviewer": "用户（策略分析师）",
      "end_user": "用户本人"
    },
    "when": {
      "deadline": "2026-07-13",
      "priority": "高"
    },
    "where": {
      "scope": "A股全市场（剔除ST/退市）",
      "exclusions": "港股通、期货衍生品不在本次范围",
      "environment": "本地 Python 3.11 + 聚宽数据源"
    },
    "how": {
      "methodology": "IC/IR 因子测试 + 分层回测 + 组合优化",
      "constraints": "不允许使用未来函数，只能用每月末截面数据"
    },
    "how_much": {
      "precision": "夏普误差 <0.05, IC 至少三组",
      "output_format": "Jupyter Notebook + Markdown 报告",
      "reference_style": "附数据来源 URL（聚宽/巨潮）"
    }
  },
  "interpretation_set": [
    {
      "label": "解释A（主选）",
      "confidence": 0.85,
      "description": "用户需要完整的回测框架+报告"
    },
    {
      "label": "解释B（备选）",
      "confidence": 0.10,
      "description": "用户只需要因子IC计算结果，不需要回测"
    }
  ]
}
```

### B.4 语义坍缩防护策略

**核心原理**：欠规约（under-specification）让 LLM 自由度过大，模型天然倾向于选择一条**看起来最合理的单一路径**而不自知这是众多可能之一。防护分三层：

**第一层 — 显式替代解释（检测层）**
- 每轮澄清后，强制生成 2-3 个不冲突的替代解读（如上文 `interpretation_set`）
- 如果解读间语义距离 <0.3，标记为"欠规约"，需要补充追问
- 这一层优先用 System 2 慢思维做，不做直觉模式匹配

**第二层 — 分歧仲裁（消歧层）**
- 将替代解读呈现给用户："我理解到 A/B 两种含义，您指哪一个？"
- 用户选择后，标记被排除的解读，供后续参考（防止回归到被排除路径）
- 分歧仲裁信息写入 `interpretation_resolved` 字段

**第三层 — 执行中验证（回溯层）**
- 在拆解阶段（D 依赖图构建时）回查：当前路径是否与已排除的解读一致？
  - 如果一致 → 说明坍缩已发生 → 停止执行并报警
  - 如果不一致 → 继续
- 这一步防止"澄清时用户纠正了，但模型自动滑回原路径"

**示例场景**：用户说"帮我分析一下茅台"
- 检测层输出：解释A=技术面分析，解释B=基本面财务分析，解释C=新闻舆情分析（语义距离 0.54>0.3 → 中度欠规约）
- 消歧层追问："茅台有 A/B/C 三种分析角度，您需要哪个？"
- 用户回答"A"，解释B和C被排除并记录
- 回溯层在拆解时检查：当前依赖图是否混入了基本面分析？若有 → 坍缩报警

---

## C. 强化版任务拆解 Schema（v2.3）

```json
{
  "$schema": "https://json-schema.org/draft/07/schema#",
  "title": "TaskDecompositionV2.3",
  "type": "object",
  "required": [
    "schema_version",
    "meta",
    "goal_restatement",
    "clarification_rounds",
    "subtasks",
    "dependency_graph",
    "risk_assessment"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["v2.3"]
    },
    "meta": {
      "type": "object",
      "description": "五维分类（保留原始框架的兼容性）",
      "required": ["pi_type", "knowledge_domain", "complexity"],
      "properties": {
        "pi_type": {
          "type": "string",
          "enum": ["information_retrieval", "analysis_judgment", "creation_generation", "decision_execution", "hybrid"]
        },
        "knowledge_domain": {
          "type": "string",
          "description": "12分类知识域（按原框架）"
        },
        "capability_requirements": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["research", "reasoning", "coding", "writing", "coordination"]
          },
          "minItems": 1,
          "maxItems": 5
        },
        "complexity": {
          "type": "string",
          "enum": ["L1", "L2", "L3", "L4"]
        },
        "quality_requirements": {
          "type": "object",
          "properties": {
            "precision": { "type": "string", "description": "精度要求，如 IC 误差 <0.05" },
            "citation": { "type": "string", "description": "引用规范，如 数据来源URL" },
            "output_format": { "type": "string", "description": "交付物格式，如 Markdown 报告" }
          }
        }
      }
    },
    "goal_restatement": {
      "type": "object",
      "description": "澄清后的结构化目标重述",
      "required": ["what", "why", "who", "when", "where", "how", "how_much"],
      "properties": {
        "what": { "type": "string" },
        "why": { "type": "string" },
        "who": {
          "type": "object",
          "properties": {
            "creator": { "type": "string" },
            "reviewer": { "type": "string" },
            "end_user": { "type": "string" }
          }
        },
        "when": {
          "type": "object",
          "properties": {
            "deadline": { "type": "string", "format": "date" },
            "priority": { "type": "string", "enum": ["高", "中", "低"] }
          }
        },
        "where": {
          "type": "object",
          "properties": {
            "scope": { "type": "string" },
            "exclusions": { "type": "string" },
            "environment": { "type": "string" }
          }
        },
        "how": {
          "type": "object",
          "properties": {
            "methodology": { "type": "string" },
            "constraints": { "type": "string" }
          }
        },
        "how_much": {
          "type": "object",
          "properties": {
            "precision": { "type": "string" },
            "output_format": { "type": "string" },
            "reference_style": { "type": "string" }
          }
        }
      }
    },
    "clarification_rounds": {
      "type": "array",
      "description": "澄清轮次记录（用于审计回溯）",
      "items": {
        "type": "object",
        "required": ["round", "detection_results", "user_input", "resolved"],
        "properties": {
          "round": { "type": "integer" },
          "detection_results": {
            "type": "object",
            "properties": {
              "coverage_score": { "type": "number", "minimum": 0, "maximum": 7, "description": "5W2H覆盖维度数" },
              "semantic_collapse_risk": { "type": "string", "enum": ["高", "中", "低"] },
              "vagueness_keywords": { "type": "array", "items": { "type": "string" } },
              "interpretation_set": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "label": { "type": "string" },
                    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
                    "description": { "type": "string" }
                  }
                },
                "minItems": 1,
                "maxItems": 5
              }
            }
          },
          "user_input": { "type": "string" },
          "resolved": { "type": "boolean" }
        }
      }
    },
    "subtasks": {
      "type": "array",
      "description": "子任务清单（DGI 最优粒度 ≈ √(推理步数)）",
      "items": {
        "type": "object",
        "required": [
          "id", "name", "type", "dependency_ids", "acceptance_criteria",
          "output_format", "assigned_role", "method_hint", "effort_estimate"
        ],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^ST-\\d{3}$"
          },
          "name": {
            "type": "string",
            "description": "子任务名称（动宾结构，如"获取因子数据"）"
          },
          "type": {
            "type": "string",
            "enum": ["information_retrieval", "analysis_judgment", "creation_generation", "decision_execution", "verification", "coordination"],
            "description": "子任务类型（继承自π类型但在子任务粒度细化）"
          },
          "dependency_ids": {
            "type": "array",
            "items": { "type": "string" },
            "description": "前置依赖的子任务ID列表，空数组表示无依赖"
          },
          "acceptance_criteria": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 1,
            "description": "验收标准列表（每个标准必须可验证、可观测）"
          },
          "output_format": {
            "type": "object",
            "properties": {
              "type": { "type": "string", "enum": ["code", "data", "text", "image", "config", "mixed"] },
              "schema": { "type": "string", "description": "输出schema引用或内联描述" },
              "max_length": { "type": "integer", "description": "输出最大长度约束" }
            }
          },
          "assigned_role": {
            "type": "object",
            "properties": {
              "executor": { "type": "string", "enum": ["AI", "Human", "AI+Human"], "description": "执行主体" },
              "reviewer": { "type": "string", "enum": ["AI", "Human", "AI+Human"], "description": "审核主体" },
              "escalation": { "type": "boolean", "description": "是否允许AI在不确定时上报human" }
            }
          },
          "method_hint": {
            "type": "string",
            "description": "可选的方法/工具建议"
          },
          "effort_estimate": {
            "type": "object",
            "properties": {
              "level": { "type": "string", "enum": ["XS", "S", "M", "L", "XL"] },
              "max_tokens": { "type": "integer" },
              "max_rounds": { "type": "integer" }
            }
          },
          "risk": {
            "type": "string",
            "enum": ["L1", "L2", "L3", "L4"],
            "description": "L1✅ 安全 / L2⚠️ 需关注 / L3🔴 高风险 / L4🚫 极高风险"
          }
        }
      }
    },
    "dependency_graph": {
      "type": "object",
      "description": "依赖关系图（DAG）",
      "required": ["nodes", "edges", "critical_path"],
      "properties": {
        "nodes": {
          "type": "array",
          "items": { "type": "string", "description": "子任务ID" }
        },
        "edges": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["from", "to"],
            "properties": {
              "from": { "type": "string" },
              "to": { "type": "string" },
              "type": {
                "type": "string",
                "enum": ["blocking", "conditional", "feedback"],
                "description": "blocking：前序完成后序才能开始；conditional：前序输出决定后序是否执行；feedback：后序输出可触发前序修正"
              }
            }
          }
        },
        "critical_path": {
          "type": "array",
          "items": { "type": "string" },
          "description": "关键路径上的子任务ID序列（决定总工期）"
        }
      }
    },
    "risk_assessment": {
      "type": "object",
      "description": "预验尸检查结果嵌入",
      "required": ["overall_risk", "failure_scenarios", "fallback_plans"],
      "properties": {
        "overall_risk": {
          "type": "string",
          "enum": ["L1✅", "L2⚠️", "L3🔴", "L4🚫"]
        },
        "failure_scenarios": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "scenario": { "type": "string" },
              "affected_subtasks": { "type": "array", "items": { "type": "string" } },
              "causes": { "type": "array", "items": { "type": "string" } },
              "likelihood": { "type": "string", "enum": ["高", "中", "低"] }
            }
          },
          "minItems": 3
        },
        "fallback_plans": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "for_scenario": { "type": "string" },
              "action": { "type": "string" },
              "trigger_condition": { "type": "string" }
            }
          }
        },
        "divergence_patterns_checked": {
          "type": "object",
          "description": "发散5模式检查结果",
          "properties": {
            "sequencing_risk": { "type": "string", "enum": ["pass", "warn", "fail"] },
            "omissions_risk": { "type": "string", "enum": ["pass", "warn", "fail"] },
            "additions_risk": { "type": "string", "enum": ["pass", "warn", "fail"] },
            "granularity_risk": { "type": "string", "enum": ["pass", "warn", "fail"] },
            "misinterpretation_risk": { "type": "string", "enum": ["pass", "warn", "fail"] }
          }
        }
      }
    },
    "execution_plan": {
      "type": "object",
      "description": "执行模式选择",
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["serial", "parallel_clusters", "human_loop", "hybrid"]
        },
        "parallel_clusters": {
          "type": "array",
          "items": {
            "type": "array",
            "items": { "type": "string", "description": "可并行的子任务ID" }
          },
          "description": "parallel_clusters模式下，每组内的子任务可并行执行"
        },
        "human_checkpoints": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "at_subtask": { "type": "string" },
              "condition": { "type": "string" },
              "action_on_reject": { "type": "string" }
            }
          },
          "description": "需要human审批的检查点"
        }
      }
    }
  }
}
```

---

## D. 5W2H × 拆解映射表

| 5W2H 维度 | 对应拆解流程步骤 | 对应 Schema 字段 | 映射说明 |
|-----------|---------------|-----------------|---------|
| **What** 做什么 | **P1 目标声明** → 目标分解为子任务列表 | `goal_restatement.what` → `subtasks[].name` | What 是拆解的起点，每个子任务名称就是 What 的最小粒度表达 |
| **Why** 为什么做 | **P1 优先级排序** → 影响验收标准设定 | `goal_restatement.why` → `meta.quality_requirements.*` | Why 回答任务的"价值主张"，决定了验收标准的严苛程度和子任务类型的选择 |
| **Who** 谁来做/审 | **P3 角色分配** → 人机分工决策 | `goal_restatement.who` → `subtasks[].assigned_role` | Who 决定了子任务的 executor/reviewer/escalation 配置，是 human-in-the-loop 的锚点 |
| **When** 什么时候完成 | **P4 依赖图构建** → 关键路径识别 | `goal_restatement.when` → `dependency_graph.critical_path` 和 `subtasks[].effort_estimate` | When 约束影响执行模式选择（serial vs parallel）和工期估算 |
| **Where** 什么范围 | **P2 边界界定** → scope/exclusion 写入每个子任务 | `goal_restatement.where` → `subtasks[].acceptance_criteria` 中隐含边界 | Where 定义了每个子任务的工作边界和数据源范围 |
| **How** 怎么做 | **P5 方法选型** → method_hint 写入子任务 | `goal_restatement.how` → `subtasks[].method_hint` | How 的方法论选择影响具体执行路径，尤其是"条件路由"边（conditional edge） |
| **How Much** 做到什么程度 | **P6 质量标准** → 生成验收标准 | `goal_restatement.how_much` → `subtasks[].acceptance_criteria` | How Much 是验收标准的核心驱动力，直接映射到每个子任务的精度/格式/引用要求 |

**子任务类型与 5W2H 的对应优先级**：

| 子任务类型 | 最相关的 5W2H | 说明 |
|-----------|-------------|------|
| `information_retrieval` | **What/Where** | 检索什么、从哪检索 |
| `analysis_judgment` | **Why/How_Much** | 判断的价值尺度和精度 |
| `creation_generation` | **How/Who** | 用什么方法创造、谁审 |
| `decision_execution` | **Why/When** | 为什么此时做决定 |
| `verification` | **How_Much** | 质量检查直接对应验收标准 |
| `coordination` | **Who** | 协调谁与谁 |

---

## E. 增强后工作流（ASCII 流程图）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        0. 任务输入                                    │
│              (用户原始需求, 含/不含附件)                               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              1. 模糊度检测 (§B.1)                                    │
│                                                                     │
│   ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│   │① 5W2H覆盖率扫描 │    │②语义坍缩探查     │    │③边界模糊词匹配│  │
│   └────────┬────────┘    └────────┬─────────┘    └───────┬───────┘  │
│            └──────────┬───────────┴───────────┬──────────┘          │
│                       ▼                       ▼                    │
│               ┌──────────────┐        ┌──────────────┐              │
│               │ 覆盖 ≥5/7?  │  No    │ 深度检测     │              │
│               │ 坍缩低?     │───────→│ ④+⑤ (§B.1)  │              │
│               │ 模糊词≤1?   │        └──────┬───────┘              │
│               └──────┬───────┘               │                      │
│                      │ Yes                   │                      │
│                      ▼                       ▼                      │
│               ┌─────────────────────────────────────┐               │
│               │         综合判定结果                   │              │
│               │  清晰 / 轻度模糊 / 中度模糊 / 重度模糊 │             │
│               └──────────────────┬──────────────────┘               │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              2. 澄清追问 (§B.2)                                     │
│                                                                     │
│   清晰 ──────────→ 跳过追问                                          │
│   轻度模糊 ───────→ 单轮段落式补全缺失维度                             │
│   中度模糊 ───────→ 单轮结构化（选择题/填空模板）                      │
│   重度模糊 ───────→ 多轮渐进式（首轮缩scope，次轮补细节）               │
│   语义坍缩 ───────→ 反问式："A/B/C三种理解，您指哪个？"                │
│                                                                     │
│   ┌──────────────────────────────────────────────┐                  │
│   │ 轮次上限: 2轮; 超限未解决 → 标记"不可拆解"返回 │                 │
│   └──────────────────────────────────────────────┘                  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              3. 语义坍缩防护 (§B.4)                                 │
│                                                                     │
│   ┌──────────────────────────────────────────┐                      │
│   │ 第一层（检测）: 生成 interpretation_set    │                     │
│   │   → 语义距离足够大 → 通过                   │                    │
│   │   → 语义距离过小 → 返回步骤2补充追问          │                   │
│   └──────────────────┬───────────────────────┘                      │
│                      ▼                                              │
│   ┌──────────────────────────────────────────┐                      │
│   │ 第二层（消歧）: 将 interpretation_set 呈现   │                    │
│   │   → 用户选择 → 被排除的解读记入排除列表      │                   │
│   └──────────────────┬───────────────────────┘                      │
│                      ▼                                              │
│   ┌──────────────────────────────────────────┐                      │
│   │ 第三层（回溯）: 拆解完成后回查              │                    │
│   │   → 依赖图是否混入被排除路径?               │                   │
│   │     No → 通过                              │                    │
│   │     Yes → 坍缩报警, 返回步骤2              │                    │
│   └──────────────────────────────────────────┘                      │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              4. 目标重述 (§B.3)                                     │
│                                                                     │
│   输出结构化 goal_restatement（5W2H 全维度）                         │
│   等待用户确认                                                       │
│   ┌──────────────┐    ┌──────────────┐                              │
│   │ 用户确认 Yes │    │ 用户拒绝 →   │──── 返回步骤2或3              │
│   └──────┬───────┘    └──────────────┘                              │
└──────────┼───────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              5. 五维分类 (保留原始框架)                              │
│                                                                     │
│   meta = { π类型, 知识域, 能力要求, 复杂度L1-L4, 质量要求 }          │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              6. 任务拆解 — 子任务生成 (§C)                          │
│                                                                     │
│   DGI最优粒度 ≈ √(推理步数)                                          │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │ 目标: 目标陈述(what) → 分解为 N 个子任务                     │    │
│   │   ST-001: 子任务1 (name=动宾结构)                           │    │
│   │   ST-002: 子任务2                                           │    │
│   │   ...                                                       │    │
│   │                                                             │    │
│   │ 每个子任务: type/dependency_ids/acceptance_criteria/         │    │
│   │            output_format/assigned_role/method_hint/effort    │    │
│   └────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              7. 依赖图构建                                          │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │  edges[] ← 识别子任务间的 blocking/conditional/feedback 关系  │    │
│   │  critical_path ← 最长路径（决定总工期）                       │    │
│   │                                                             │    │
│   │  parallel_clusters ← 无依赖的子任务归组                       │    │
│   │  例: ST-001→ST-002→ST-003 (串行)                            │    │
│   │       ST-002和ST-004 (并行) → 分配不同agent                  │    │
│   └────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              8. 预验尸检查 (Premortem)                              │
│                                                                     │
│   发散5模式逐项检查:                                                  │
│   □ Sequencing   — 子任务顺序是否合理?                                │
│   □ Omissions    — 是否有遗漏的关键步骤?                              │
│   □ Additions    — 是否引入了不必要的步骤?                            │
│   □ Granularity  — 粒度是否一致 (DGI ≈ √N)?                         │
│   □ Misinterpret — 是否有步骤误解了目标?                              │
│                                                                     │
│   生成 failure_scenarios[] ≥3 个                                     │
│   生成 fallback_plans[] 对应每个失败场景                              │
│   overall_risk → L1~L4                                               │
│                                                                     │
│   预验尸未通过 → 返回步骤6修正                                       │
│   预验尸通过   → 继续                                               │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              9. 专家匹配                                            │
│                                                                     │
│   根据 meta.knowledge_domain + subtasks[].type + assigned_role      │
│   → 匹配 WorkBuddy 专家团或子Agent                                  │
│                                                                     │
│   blocking类任务 → 串行排列                                         │
│   parallel_clusters → 分配给不同agent并行                            │
│   human_checkpoints → 注册审批节点                                   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              10. 执行模式选择 & 输出部署                              │
│                                                                     │
│   execution_plan.mode ∈ { serial, parallel_clusters,               │
│                           human_loop, hybrid }                      │
│                                                                     │
│   输出完整的 v2.3 JSON Schema 到计划文件                               │
│   创建 _plan-tracker.md 记录规划版本                                 │
│   等待用户确认后执行                                                  │
│                                                                     │
│   规划后自检:                                                        │
│   完整性 ≥4/5, 可执行性 ≥4/5, 风险控制 ≥3/5, Token效率 ≥3/5         │
│   综合 ≥3.5 → 通过 → 执行                                            │
│   综合 <3.5 → 返回步骤6修订                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 附录：Schema v2.3 vs v2.x 对比

| 维度 | v2.x（当前） | v2.3（设计） | 提升 |
|------|------------|------------|------|
| 输出结构 | 3字段（π+知识域+复杂度） | 7大模块、30+字段 | 从分类标签→完整执行蓝图 |
| 目标明确 | 无 | 模糊度检测→澄清→语义坍缩防护→目标重述 | 消除欠规约导致的错误执行 |
| 子任务 | 无 | 带依赖/验收标准/角色/方法提示的完整清单 | 可执行、可验证 |
| 依赖关系 | 无 | DAG图+关键路径+并行簇 | 支持并行派发、工期估算 |
| 验收标准 | 无 | 每个子任务独立清单 | 可验证完成、可审计质量 |
| 人机分工 | 无 | executor/reviewer/escalation 三级 | 避免Agent越权或Human疲劳 |
| 预验尸 | 分类后"然后进入预验尸" | 嵌入Schema内部，结构化输出 | 可操作、可审计 |
| 发散5模式 | 调研材料中提到但未使用 | 逐项检查并记录结果 | 系统性防止常见拆解错误 |
