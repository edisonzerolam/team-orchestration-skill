
# 法律咨询团队 SOP

## 基本信息
- **团队名称**：chatlaw（法律咨询）
- **Agent 数量**：6
- **触发词**：法律咨询、合同审查/劳动纠纷/婚姻/法律问题

## 团队架构
| Agent | 角色 | 职责 |
|-------|------|------|
| intake-specialist | 分诊专员 | 收集案情，判断法律性质，分诊到对应领域 |
| legal-researcher | 法律研究员 | 检索相关法律条文、司法解释 |
| precedent-analyst | 判例分析师 | 搜索类似判例，分析裁判方向 |
| contract-reviewer | 合同审查员 | 审查合同条款，识别法律风险 |
| litigation-strategist | 诉讼策略师 | 制定诉讼或应诉策略 |
| report-compiler | 报告撰写员 | 撰写法律咨询意见书 |

## SOP 流程

### Phase 1：信息采集
**输入**：用户的法律问题描述
**输出**：`case-plan.md` + `case-facts.md`
**目的**：完整收集案情，确定法律关系
**步骤**：
1. intake-specialist 分析问题类型（民事/刑事/行政）
2. 收集关键事实要素
3. 确定适用的法律领域

### Phase 2：法律研究
**输入**：case-facts.md
**输出**：`legal-research.md`
**目的**：确定适用的法律规则
**步骤**：
1. legal-researcher 检索相关法律条文
2. 梳理法律逻辑链条
3. 输出法律研究报告

### Phase 3：判例分析
**输入**：legal-research.md
**输出**：`precedent-analysis.md`
**目的**：通过判例验证法律适用
**步骤**：
1. precedent-analyst 搜索相关判例
2. 分析裁判结果和理由
3. 评估本案的法律风险

### Phase 4：建议输出
**输入**：precedent-analysis.md
**输出**：`legal-advice.md`
**目的**：给出具体法律建议
**步骤**：
1. litigation-strategist 制定行动策略
2. 识别风险点和应对方案
3. 形成法律建议文件

### Phase 5：报告撰写
**输入**：所有分析结果
**输出**：`legal-consultation-report.md`
**目的**：形成完整法律咨询报告
**步骤**：
1. report-compiler 整合已有分析
2. 按标准格式撰写咨询报告
3. 明确给出法律意见和行动建议

## 阶段关卡（Phase Gates）
| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-信息采集 | 案情要素完整，关键事实无遗漏 | 补充提问遗漏信息 |
| PG2-法律研究 | 法律依据准确，条文引用规范 | 重新检索法律依据 |
| PG3-判例分析 | 找到至少2个相关判例 | 扩大检索范围 |
| PG4-建议输出 | 建议具体可操作，风险点覆盖 | 补充策略细节 |
| PG5-报告 | 报告格式规范，法律意见明确 | 按模板调整格式 |

## 交接协议
### 产出物格式
```yaml
team_id: {team_id}
agent_id: intake-specialist
role: 分诊专员
phase: intake
status: done
findings: |
  法律领域：劳动纠纷
  关键事实：未签劳动合同，工作2年
  法律风险：高（双倍工资差额）
```
### 验收字段
- `phase`：当前阶段
- `status`：done/in_progress
- `findings`：核心案情摘要和法律判断
