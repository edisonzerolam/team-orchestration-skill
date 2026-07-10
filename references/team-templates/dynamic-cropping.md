# 模板动态裁剪规则

## 动机

大团(>7 agents) 全量加载消耗大量 Token，多数子 Agent 不参与当前子任务。通过裁剪保留核心角色，节省 40-78% Token。

## 核心原则

1. **按子任务类型裁剪**：仅保留与当前子任务类型相关的角色
2. **20% 弹性容量**：裁剪后预留 20% 弹性槽位（按人数）
3. **最小团队**：裁剪后人数 ≥ 3（≤3 人的团队不裁剪）
4. **角色优先级**：每个团队配置 `role_priority` 列表，裁剪时优先保留靠前的角色
5. **运行时增补**：执行中发现缺少必要角色时自动增补

## 子任务类型 → 所需角色映射

| 子任务类型 | 所需角色关键词 | 说明 |
|-----------|--------------|------|
| `information_retrieval` | researcher, analyst, data | 调研/搜索/数据采集 |
| `analysis_judgment` | analyst, strategist, evaluator, assessor, researcher | 分析/判断/评估 |
| `creation_generation` | writer, designer, developer, creator, artist | 创作/生成/设计 |
| `decision_execution` | executor, implementer, operator, lead, manager | 执行/实施/操作 |
| `collaboration_discussion` | lead, moderator, reviewer, sceptic | 讨论/辩论/研讨 |
| `quality_verification` | reviewer, tester, auditor, inspector | 验证/审查/测试 |
| `general`（兜底） | 全部保留（不裁剪） | 未知类型不裁剪 |

## 裁剪算法

```
输入: team_name, subtasks, complexity
输出: cropped_agents

1. 从 subtasks 提取所有 unique 子任务类型
2. 查找 cropping-config.json 中该 team 的配置
3. 无配置 → 不裁剪（返回全量 agent 列表）
4. 从 agent 的 role title/description 匹配所需角色关键词
5. 按 role_priority 排序 → 取 base_size 个
6. 计算弹性槽位 = ceil(base_size × elastic_ratio)
7. 如果弹性槽位 > 0 → 从候选列表补充
8. 结果 < min_size → 保留 min_size 个
```

## 运行时增补触发条件

- 执行阶段发现子任务类型未覆盖 → 自动从原团队补一个匹配该类型的 agent
- 执行中连续 2 个子任务失败 → 增补 1 个同角色的 agent
- 用户主动要求扩大团队 → force_team 参数跳过裁剪
