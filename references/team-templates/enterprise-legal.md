
# 企业法务团队 SOP
## 基本信息- **团队名称**：
enterprise-legal（企业法务）- **Agent 数量**?- **触发?*：
企业法?合同审查/法务咨询/法律顾问/合规审查
## 团队架构
| Agent | 角色 | 职责 ||-------|------|------|| triage-lawyer | 分诊律师 | 判断法律问题类型，分诊到对应法务模块 || contract-specialist | 合同专家 | 审查和起草各类商业合?|| employment-specialist | 劳动法专?| 处理劳动关系、劳动合同劳动纠?|| privacy-specialist | 隐私法专?| 审查数据隐私合规（GDPR/个人信息保护法） || product-legal | 产品法务 | 审查产品功能的法律风?|| regulatory-specialist | 监管合规专家 | 审查行业监管合规要求 || ai-governance-specialist | AI治理专家 | 审查AI产品和算法的合规?|| ip-specialist | 知识产权专家 | 处理专利、商标著作权问题 || ma-specialist | 并购法务专家 | 处理投资并购的法务尽职调?|
## SOP 流程
### Phase 1：
法律分?**输入**：
企业法律问题描?**输出**：
`legal-triage.md`**目的**：
确定法律问题类型和优先?**步骤**?1. triage-lawyer 分析问题类型2. 识别涉及的法律领?3. 制定法务处理计划
### Phase 2：
模块化法务审查**输入**：
legal-triage.md**输出**：
各专业领域的法务分析文?**目的**：
按领域进行专业审查**步骤**（根据问题类型择相关模块）：
1. contract-specialist ?合同分析和起?2. employment-specialist ?劳动法审?3. privacy-specialist ?隐私合规审查4. product-legal ?产品法律风险评估5. regulatory-specialist ?监管合规审查6. ai-governance-specialist ?AI合规审查7. ip-specialist ?知识产权审查8. ma-specialist ?并购尽职调查
### Phase 3：
综合报?**输入**：
各模块法务分析**输出**：
综合法务意见书**目的**：
形成统丢的法律意?**步骤**?1. 各专家汇总分析结?2. 评估法律风险等级3. 给出综合建议和行动方?
## 阶段关卡（Phase Gates?
| 关卡 | 通过条件 | 失败处理 ||------|----------|----------|| PG1-分诊 | 分诊结果准确，法律领域判断正?| 重新评估问题类型 || PG2-合同审查 | 合同条款无重大法律风?| 修改合同条款 || PG3-劳动?| 劳动合规审查覆盖扢有用工场?| 补充合规整改 || PG4-隐私合规 | 隐私政策符合法规要求 | 调整隐私政策 || PG5-产品合规 | 产品法律风险≤低风险 | 修改产品设计 || PG6-监管合规 | 监管合规棢查过 | 补充合规措施 || PG7-AI治理 | AI产品通过合规审查 | 调整AI算法或产?|| PG8-IP审查 | 无知识产权侵权风?| 规避设计或申请许?|| PG9-并购 | 尽调报告无重大法律障?| 调整交易结构或放?|
## 交接协议
```yaml---team_id: {team_id}agent_id: triage-lawyerrole: 分诊律师phase: triagestatus: donefindings: |  法律领域：
合同法 + 劳动?  紧程度：
?  建议处理顺序：
合同审?
> 劳动合规 
> 隐私审查---
```
### 验收字段- `phase`：
当前阶?- `status`：
done/in_progress- `findings`：
法律判断和处理建议