# 专家匹配引擎

## 输入

- 拆解后的任务特征向量 T（π, 知识域, 能力, 复杂度, 质量）
- 可用专家池 E（28 个 WorkBuddy 专家团 + 原生 6 个 subagent）
- 历史评分数据库

## 评分公式

```
Score(T, E_i) =
  α × domain_match(T, E_i)        # 领域匹配度 (权重 0.35)
  + β × capability_match(T, E_i)  # 能力匹配度 (权重 0.30)
  + γ × performance_score(E_i)     # 历史表现分 (权重 0.20)
  - δ × current_load(E_i)         # 当前负载惩罚 (权重 0.15)
```

### domain_match 计算

从 `plugin.json` / 每个专家团的 `categoryId` 和 `displayDescription` 中提取领域特征向量, 与任务 T 的领域向量计算余弦相似度。

### capability_match 计算

从每个 Agent MD 的 frontmatter 和"核心能力"章节提取能力关键词, 与任务需求的能力维度做交集评分。

### performance_score

基于专家评分数据库 `expert-scores.json` 中的历史评分。

### current_load

当前会话中已分配的专家数量（避免单专家过载）。

## 匹配策略

```
Score > 0.8 → 直调（单专家即可）
0.5 < Score ≤ 0.8 → 推荐团队（可能需要多专家协作）
Score ≤ 0.5 → 提示专家池无高匹配专家，或退回到通用 agent
```

## 团队组建

当任务复杂度 ≥ L3 或知识域 > 1 时，自动组建团队：

```
1. 选主理人：匹配合度最高的团队 Lead
2. 选成员：为每个子任务匹配最佳成员
3. 生成 SOP：从该团队的 agent 定义中提取工作流
4. 确认：向用户展示团队配置
```
