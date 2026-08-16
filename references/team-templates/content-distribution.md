# 内容分发团队 SOP

## 基本信息

- **团队名称**：content-distribution（内容分发）
- **Agent 数量**：5
- **触发词**：内容分发、多平台发布、社媒运营/帮我分发内容

## 团队架构

| Agent | 角色 | 职责 |
|-------|------|------|
| strategy-director | 策略总监 | 制定全平台分发策略，分析各平台特点 |
| platform-analyst | 平台分析师 | 研究各平台算法、用户画像、流量规则 |
| domestic-strategist | 国内平台策略师 | 负责抖音/小红书/微信/微博等国内平台 |
| international-strategist | 国际平台策略师 | 负责 YouTube/Instagram/TikTok 等国际平台 |
| calendar-manager | 排期管理师 | 制定内容发布排期 |

## SOP 流程

### Phase 1：策略制定

**输入**：待分发的内容 + 目标平台
**输出**：`distribution-plan.md`
**目的**：制定分发策略和优先级

**步骤**：
1. strategy-director 分析内容特点
2. 确定目标平台和分发优先级
3. 制定整体分发计划

### Phase 2：平台分析

**输入**：distribution-plan.md
**输出**：`platform-analytics.md`
**目的**：深入了解各平台特点

**步骤**：
1. platform-analyst 研究各平台算法和规则
2. 分析各平台用户画像
3. 输出平台分析报告

### Phase 3：国内平台分发

**输入**：platform-analytics.md
**输出**：各国内平台适配版本 + 排期
**目的**：完成国内平台分发

**步骤**：
1. domestic-strategist 调整内容适配各平台
2. 制定发布时间和频率
3. 输出各平台适配版本

### Phase 4：国际平台分发

**输入**：platform-analytics.md
**输出**：各国际平台适配版本 + 排期
**目的**：完成国际平台分发

**步骤**：
1. international-strategist 调整内容适配国际平台
2. 处理语言和文化适配
3. 输出国际版本

### Phase 5：排期汇总

**输入**：各平台分发计划
**输出**：`content-calendar.md`
**目的**：形成完整的发布排期

**步骤**：
1. calendar-manager 汇总所有平台排期
2. 优化发布时间避免冲突
3. 输出统一的排期表

## 阶段关卡（Phase Gates）

| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-策略 | 分发计划包含至少3个目标平台 | 补充平台分析 |
| PG2-平台分析 | 各平台用户画像和算法规则清晰 | 深入调研平台规则 |
| PG3-国内分发 | 每个目标国内平台都有适配方案 | 补充平台适配 |
| PG4-国际分发 | 国际版本语言准确，文化适配合理 | 重新翻译和适配 |
| PG5-排期 | 排期表覆盖所有平台，时间无冲突 | 调整发布时间 |

## 交接协议

### 产出物格式

```yaml
---
team_id: {team_id}
agent_id: strategy-director
role: 策略总监
phase: strategy
status: done
findings: |
  目标平台：抖音、小红书、YouTube
  分发优先级：抖音>小红书>YouTube
  预计总曝光：50万
---
```

### 验收字段

- `phase`：当前阶段
- `status`：done/in_progress
- `findings`：平台策略和预期效果
