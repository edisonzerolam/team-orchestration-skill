
# A股研究团队 SOP

## 基本信息
- **团队名称**：a-share-analysis（A股研究）
- **Agent 数量**：8
- **触发词**：A股分析、帮我分析A股、研究A股、分析股票

## 团队架构
| Agent | 角色 | 职责 |
|-------|------|------|
| macro-analyst | 宏观分析师 | 分析宏观经济环境、货币政策财政政策 |
| market-strategist | 市场策略师 | 分析市场整体趋势、资金流向情绪指标 |
| industry-researcher | 产业研究员 | 分析产业链上下游、竞争格局、政策影响 |
| stock-analyst | 个股分析师 | 分析个股基本面、财务数据、竞争力 |
| valuation-expert | 估值专家 | DCF估值/PE/PB比较、相对估值 |
| money-flow-tracker | 资金追踪员 | 追踪主力资金、北向资金融资融券 |
| risk-assessor | 风险评估师 | 评估市场风险、信用风险流动性风险 |
| synthesis-writer | 综合撰写员 | 汇总各方分析，撰写最终研究报告 |

## SOP 流程

### Phase 1：宏观分析
**输入**：用户指定的股票或行业
**输出**：`macro-analysis.md`
**目的**：了解宏观环境对投资的影响

### Phase 2：市场分析
**输入**：macro-analysis.md
**输出**：`market-analysis.md`
**目的**：判断当前市场位置和情绪

### Phase 3：产业分析
**输入**：market-analysis.md
**输出**：`industry-analysis.md`
**目的**：理解产业逻辑和竞争格局

### Phase 4：个股分析
**输入**：industry-analysis.md
**输出**：`stock-analysis.md`
**目的**：评估个股的投资价值

### Phase 5：估值分析
**输入**：stock-analysis.md
**输出**：`valuation-analysis.md`
**目的**：得出估值区间

### Phase 6：资金分析
**输入**：valuation-analysis.md
**输出**：`money-analysis.md`
**目的**：判断资金面的支持

### Phase 7：风险评估
**输入**：money-analysis.md
**输出**：`risk-analysis.md`
**目的**：识别主要风险因素

### Phase 8：综合报告
**输入**：所有分析结果
**输出**：`final-research-report.md`
**目的**：形成完整投资研究报告

## 阶段关卡（Phase Gates）
| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-宏观 | 宏观环境描述完整，包含至少一个关键指标 | 补充宏观数据 |
| PG2-市场 | 市场趋势判断明确，资金流向数据完整 | 重新评估市场 |
| PG3-产业 | 产业链梳理完整，政策影响分析到位 | 补充产业调研 |
| PG4-个股 | 财务数据准确，竞争力分析全面 | 补充数据 |
| PG5-估值 | 估值方法合理，区间明确 | 调整估值假设 |
| PG6-资金 | 资金流向数据新鲜，主力动向明确 | 补充资金数据 |
| PG7-风险 | 风险因素覆盖全面（至少两项） | 补充风险识别 |

## 交接协议
### 产出物格式
```yaml
team_id: {team_id}
agent_id: macro-analyst
role: 宏观分析师
phase: macro
status: done
findings: |
  宏观环境：经济复苏初期，货币政策稳健
  关键指标：GDP增速5.2%，CPI同比0.8%
```
### 验收字段
- `phase`：当前阶段
- `status`：done/in_progress
- `findings`：核心发现，包含数据支撑
