# 专家匹配引擎

## 输入

- 拆解后的任务特征向量 T（π, 知识域, 能力, 复杂度, 质量）
- 可用专家池 E（28 个 WorkBuddy 专家团 + 原生 6 个 subagent）
- 历史评分数据库 `expert-scores.json`
- 权重矩阵 `weight-matrix.json`（6 种 task_type × 4 维度）
- 探索日志 `exploration-log.json`（ε-greedy 冷启动）

## 评分公式

```
Score(T, E_i) =
  α × domain_match(T, E_i)        # 领域匹配度
  + β × capability_match(T, E_i)  # 能力匹配度
  + γ × performance_score(E_i)     # 历史表现分
  - δ × current_load(E_i)         # 当前负载惩罚
```

### 权重矩阵

不同 PI 类型使用不同权重组合（`shared/weight-matrix.json`）：

| task_type | α (domain) | β (capability) | γ (performance) | δ (load) |
|-----------|-----------|----------------|-----------------|----------|
| 信息检索型 | 0.40 | 0.25 | 0.20 | 0.15 |
| 分析判断型 | 0.35 | 0.30 | 0.20 | 0.15 |
| 创作生成型 | 0.25 | 0.40 | 0.20 | 0.15 |
| 决策执行型 | 0.30 | 0.25 | 0.25 | 0.20 |
| 协作讨论型 | 0.30 | 0.30 | 0.20 | 0.20 |
| 质量验证型 | 0.35 | 0.35 | 0.15 | 0.15 |

未知类型回退到默认值 `[0.35, 0.30, 0.20, 0.15]`。

### domain_match 计算

从 `plugin.json` / `teams-index.json` 每个专家团的 `categoryId` 和 `displayDescription` 中提取领域特征向量, 与任务 T 的领域向量计算余弦相似度。

### capability_match 计算

从每个 Agent MD 的 frontmatter 和"核心能力"章节提取能力关键词, 与任务需求的能力维度做交集评分。

### performance_score

基于专家评分数据库 `expert-scores.json` 中的历史评分，上限 1.0。

### current_load

当前会话中已分配的专家数量（避免单专家过载），惩罚上限 1.0。

## 匹配策略

```
Score > 0.75 → 直调（单专家即可）
0.45 < Score ≤ 0.75 → 推荐团队（可能需要多专家协作）
Score ≤ 0.45 → 降级到通用 agent
```

### force_team
当 `force_team=true` 时跳过直调判断，强制走团队路径。通过 `path-selector.py --force-team` 传入。

### ε-greedy 探索（冷启动）
新专家团在积累足够评分数据前，使用 ε-greedy 策略探索：
- ε_init = 0.15，decay = 0.95（每次探索后衰减），floor = 0.02
- 探索基线：Score ≥ 0.45 时用排名加权随机，否则均匀随机
- 满 5 次探索后自动毕业（停止探索）
- 探索标记：match 返回值带 `_exploration: true` 标志
- 日志记录至 `shared/exploration-log.json`

## 团队组建

当任务复杂度 ≥ L3 或知识域 > 1 时，自动组建团队：

```
1. 选主理人：匹配合度最高的团队 Lead
2. 选成员：为每个子任务匹配最佳成员（可用 no_explore=true 关闭探索）
3. 生成 SOP：从该团队的 agent 定义中提取工作流
4. 确认：向用户展示团队配置
```

## 三阶分层加载

| Tier | 缓存策略 | TTL | 内容 |
|------|---------|-----|------|
| Tier 1 | 永不过期 | ∞ | `teams-index.json`（28 团索引） |
| Tier 2 | 短缓存 | 300s | `plugin.json`（单团详情） |
| Tier 3 | 用完即弃 | 无 | `agents/*.md`（Agent 定义） |

### 热/温/冷分级
- Hot：7 天内使用过 → 优先保留在 Tier 2 缓存
- Warm：30 天内使用过 → 正常 TTL
- Cold：超过 30 天未使用 → 下次使用时重新加载
- 状态记录在 `shared/teams-tier.json`

### Token 预算控制
- Standard 模式：完整加载所有层级
- Economy 模式：≥85% token 使用率时自动降级，metadata_only + 最多 5 agents
- 记账记录在 `shared/token-ledger.json`
