# 专家匹配引擎

## 输入

- 拆解后的任务特征向量 T（π, 知识域, 能力, 复杂度, 质量）
- 可用专家池 E（39 个 WorkBuddy 专家团，199 agents，见 `workbuddy-experts/_index.md`）
- 历史评分数据库（由归档写端自动生成，见 README「自学习数据说明」）

## 评分公式（v3.1 现行：四维加权乘法式）

> 权重**唯一权威定义**位于 `config.yaml` → `matcher.weights`，本文档仅描述公式，不重复定义数值。修改权重只改 config.yaml。

```
Score(E_i) = min(
    category×W_cat + bigram×W_bigram + capability×W_cap + history×W_hist,
    1.0
)
```

- **category**：任务领域分类与专家 category_id 的匹配（0 或 1，可累加取 min 1.0）
- **bigram**：任务文本与专家描述（description_zh + capabilities）的中文 bigram Jaccard 相似度
- **capability**：领域关键词在专家 capabilities 中的命中
- **history**：历史表现分数（0..1；冷启动无数据时为 0）
- **入选阈值**：`score >= min_score`（`config.yaml` → `matcher.min_score`，当前 0.25），按降序取 `top_k`（默认 3）

## 匹配策略

```
Score ≥ 0.6   → 高匹配（首选团队）
0.25 ≤ Score < 0.6 → 弱匹配（建议，可人工确认）
Score < 0.25  → 不入选，提示专家池无高匹配专家，或退回通用 agent
```

## 团队组建

当任务复杂度 ≥ L3 或知识域 > 1 时，自动组建团队：

```
1. 选主理人：匹配合度最高的团队 Lead
2. 选成员：为每个子任务匹配最佳成员
3. 生成 SOP：从该团队的 agent 定义中提取工作流
4. 确认：向用户展示团队配置
```

## 实现说明

- 实现文件：`scripts/expert-matcher.py`（`match()` 函数）
- 维度命名统一为 `category / bigram / capability / history`（与 config.yaml 键名一致）
- 历史维度权重若需调整，改 `config.yaml` 即可；写端在 `trial-court-orchestrator.py` 归档时写入历史评分文件

---

## 分域加载决策表（Phase 0 · 完整版）

> 与 SKILL.md §8.1 同源，此处为完整展开（团队完整目录名对照 + 用法）。**定位：文档级判断纪律工具，非契约、非白名单**。
> 守卫：① 非白名单可追加；② 冲突以 expert-matcher 得分 + lead 判断为准；③ 通用对抗兜底（gpt-researcher-team）始终可选。"默认跳过 ≠ 禁止读取"。

### 命名对照（短名 → plugin.json 完整目录名）
| 常用短名 | 完整目录名（expert-matcher key） |
|---------|----------------------------------|
| investment-masters | investment-masters-team |
| stock-partner | stock-partner-team |
| ai-content-creator | ai-content-creator-team |
| content-distribution | content-distribution-team |
| content-monetization | content-monetization-team |
| marketing-campaign | marketing-campaign-team |
| sales-battle | sales-battle-team |
| seo-content | seo-content-team |
| engineering-assurance | engineering-assurance-team |
| product-strategy | product-strategy-team |
| enterprise-legal | enterprise-legal-team |
| tax-compliance | tax-compliance-team |

### 分级模型速查
| tier | 内容 | 何时加载 |
|------|------|----------|
| T0 核心/always | SKILL.md + §8.1 + _index 分组头 | 每任务 |
| T1 分域/按需 | 目标域团队 plugin.json + knowledge 最小集 | 命中任务域 |
| T2 惰性/进队才读 | 单 agent agents/*.md 人设（`read_agent_md` 已内置） | 该 agent 进 B 阶段 |

> 价值说明：现有流水线（expert-matcher 打分召回 + dispatch-planner 逐 agent 读 600 字）**天然惰性**，本表主要省主理人**定域判断成本**，token 收益有限且仅限"病态过度读取"情境封顶。
