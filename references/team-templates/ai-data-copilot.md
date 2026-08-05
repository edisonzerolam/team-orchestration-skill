
# 数据分析团队 SOP
## 基本信息- **团队名称**：
ai-data-copilot（数据分析）- **Agent 数量**?- **触发?*：
数据分?数据查询/数据报告/帮我分析数据
## 团队架构
| Agent | 角色 | 职责 ||-------|------|------|| data-architect | 数据架构?| 设计数据仓库模型，规?SQL 查询逻辑 || sql-developer | SQL 弢?| 编写和优?SQL 查询 || model-engineer | 模型工程?| 建立数据模型，进行统计分?|| visualization-expert | 可视化专?| 设计图表，制?Dashboard || knowledge-synthesizer | 知识综合?| 解读数据发现，连接业务知?|| report-writer | 报告撰写 | 撰写朢终分析报?|
## SOP 流程
### Phase 1：
需求分?**输入**：
用户的数据分析霢?**输出**：
`data-plan.md`**目的**：
理解需求，设计数据获取策略**步骤**?1. data-architect 拆解霢求，确定扢霢数据?2. 识别数据表和关联关系3. 编写数据计划文档
### Phase 2：
SQL 查询**输入**：
data-plan.md**输出**：
`sql-results.md`**目的**：
获取原始数?**步骤**?1. sql-developer 编写 SQL 查询2. 执行查询并验证结?3. 输出原始数据结果
### Phase 3：
建模分?**输入**：
sql-results.md**输出**：
`model-results.md`**目的**：
从数据中提取洞?**步骤**?1. model-engineer 建立分析模型2. 进行统计分析3. 输出模型结果和统计发?
### Phase 4：
可视化**输入**：
model-results.md**输出**：
`dashboard.html`**目的**：
将数据可视?**步骤**?1. visualization-expert 设计图表类型2. 生成 HTML Dashboard3. 交互式图表完?
### Phase 5：
知识综?+ 报告**输入**：
所有分析结?**输出**：
`knowledge-findings.md` + `final-report.md`**目的**：
形成完整分析报?**步骤**?1. knowledge-synthesizer 解读数据发现2. 连接业务知识，形成洞?3. report-writer 撰写朢终报?
## 阶段关卡（Phase Gates?
| 关卡 | 通过条件 | 失败处理 ||------|----------|----------|| PG1-霢求分?| data-plan.md 明确数据源和查询计划 | 返回重新理解霢?|| PG2-SQL查询 | SQL 执行成功，数据量合理 | 优化 SQL 或更换数据源 || PG3-建模分析 | 模型结果统计显著 | 调整模型或补充数?|| PG4-可视?| Dashboard 图表正确展示关键指标 | 调整图表类型或数据映?|| PG5-报告 | 报告包含业务洞察和建?| 补充分析或重新解?|
## 交接协议
### 产出物格?
```yaml---team_id: {team_id}agent_id: data-architectrole: 数据架构?phase: planningstatus: donefindings: |  数据源：
sales_orders + customers  关键指标：
月锢售额、客户留存率---
```
### 验收字段- `phase`：
当前阶?- `status`：
done/in_progress- `findings`：
核心发现描