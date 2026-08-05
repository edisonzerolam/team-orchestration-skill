
# 工程保障团队 SOP
## 基本信息- **团队名称**：
engineering-assurance（工程保障）- **Agent 数量**?- **触发?*：
代码审?工程保障/架构设计/SRE/质量保障
## 团队架构
| Agent | 角色 | 职责 ||-------|------|------|| architecture-reviewer | 架构审查?| 评估系统架构设计，识别架构风?|| code-reviewer | 代码审查?| 审查代码质量，发现潜在bug || sre-specialist | SRE专家 | 保障系统可靠性，制定监控告警策略 || test-planner | 测试规划?| 设计测试策略，规划测试用?|| documentation-writer | 文档撰写?| 撰写抢术文档和运维手册 || engineering-lead | 工程负责?| 统筹协调，决策技术方?|
## SOP 流程
### Phase 1：
架构审?**输入**：
待审查的系统架构文档或代码**输出**：
`architecture.md`**目的**：
评估架构合理和可扩展?**步骤**?1. architecture-reviewer 分析系统架构2. 识别架构反模式和风险?3. 输出架构审查报告
### Phase 2：
代码审?**输入**：
待审查的代?**输出**：
`code-review-report.md`**目的**：
发现代码质量问?**步骤**?1. code-reviewer 审查代码规范和辑2. 识别潜在bug和安全风?3. 输出代码审查报告
### Phase 3：
SRE保障**输入**：
架?+ 代码审查结果**输出**：
`sre-report.md`**目的**：
制定可靠保障方?**步骤**?1. sre-specialist 设计监控指标2. 制定告警规则和响应流?3. 输出 SRE 报告
### Phase 4：
测试规?**输入**：
architecture.md**输出**：
`test-plan.md`**目的**：
设计完整的测试策略**步骤**?1. test-planner 设计测试策略2. 规划测试用例覆盖3. 输出测试计划文档
### Phase 5：
文档撰?**输入**：
所有审查和规划结果**输出**：
`documentation/` 目录**目的**：
形成完整的抢术文?**步骤**?1. documentation-writer 整合扢有技术文?2. 撰写运维手册和故障处理指?3. 输出文档目录
## 阶段关卡（Phase Gates?
| 关卡 | 通过条件 | 失败处理 ||------|----------|----------|| PG1-架构 | 架构设计无严重风险，可扩展达?| 重新设计架构 || PG2-代码 | 重大bug数≤0，中等bug数≤3 | 修复代码问题 || PG3-SRE | 监控覆盖率≥80%，告警响应SLA明确 | 补充监控配置 || PG4-测试 | 测试用例覆盖率≥85% | 补充测试用例 || PG5-文档 | 文档完整，可直接用于运维 | 补充缺失文档 |
## 交接协议
```yaml---team_id: {team_id}agent_id: architecture-reviewerrole: 架构审查?phase: architecturestatus: donefindings: |  架构评分?/10  主要风险：
单点故障风险，数据库扩展不?  建议：
引入主备切换机?---
```