# 内容变现团队 SOP

## 基本信息
- **团队名称**：content-monetization（内容变现）
- **Agent 数量**：5
- **触发词**：内容变现、商业模式/收益优化/帮我赚钱

## 团队架构
| Agent | 角色 | 职责 |
|-------|------|------|
| revenue-strategist | 收益策略师 | 制定整体变现策略，分析各模式优劣 |
| cps-specialist | CPS专家 | 规划佣金分成模式的选品和推广策略 |
| cpe-cpm-specialist | CPE/CPM专家 | 负责按效果/千次展示付费的变现策略 |
| marketplace-strategist | Marketplace策略师 | 评估应用商店/电商平台的变现潜力 |
| revenue-analyst | 收益分析师 | 分析收益数据，建立收益预测模型 |

## SOP 流程

### Phase 1：收益策略制定
**输入**：内容资产 + 用户画像
**输出**：`monetization-plan.md`
**目的**：确定最优变现路径
**步骤**：
1. revenue-strategist 分析内容资产特征
2. 评估各变现模式的适用性
3. 制定整体变现策略

### Phase 2：CPS 模式规划
**输入**：monetization-plan.md
**输出**：`cps-strategy.md`
**目的**：规划佣金分成模式
**步骤**：
1. cps-specialist 选择推广产品
2. 制定推广计划和佣金优化策略
3. 输出 CPS 策略文档

### Phase 3：CPE/CPM 模式规划
**输入**：monetization-plan.md
**输出**：`cpe-cpm-strategy.md`
**目的**：规划广告变现模式
**步骤**：
1. cpe-cpm-specialist 设计广告展示策略
2. 优化广告填充率和点击率
3. 输出 CPE/CPM 策略文档

### Phase 4：Marketplace 评估
**输入**：monetization-plan.md
**输出**：`marketplace-strategy.md`
**目的**：评估平台内购买模式
**步骤**：
1. marketplace-strategist 评估各平台费用
2. 设计内购项目和定价策略
3. 输出 Marketplace 策略文档

### Phase 5：收益分析与报告
**输入**：所有策略文档
**输出**：`revenue-model.md`
**目的**：建立收益模型，输出预测报告
**步骤**：
1. revenue-analyst 汇总各模式预期收益
2. 建立收益预测模型
3. 输出综合收益模型报告

## 阶段关卡（Phase Gates）
| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-策略 | 变现计划包含至少2种变现模式 | 补充模式分析 |
| PG2-CPS | CPS策略包含至少5个推广产品和佣金预期 | 补充选品分析 |
| PG3-CPE/CPM | 广告策略包含填充率和CPM预期数据 | 优化广告配置 |
| PG4-Marketplace | Marketplace策略包含至少3个竞品对比 | 补充平台分析 |
| PG5-收益分析 | 收益模型包含各模式收益预期 | 调整模型参数 |

## 交接协议

### 产出物格式
```yaml
---
team_id: {team_id}
agent_id: revenue-strategist
role: 收益策略师
phase: strategy
status: done
findings: |
  推荐变现模式：CPS + CPE/CPM组合
  预期月收益：5-8万元
  变现优先级：CPS>CPE/CPM>Marketplace
---
```

### 验收字段
- `phase`：当前阶段
- `status`：done/in_progress
- `findings`：变现策略和预期收益
