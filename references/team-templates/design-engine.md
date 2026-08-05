
# 设计引擎团队 SOP
## 基本信息- **团队名称**：
design-engine（设计引擎）- **Agent 数量**?- **触发?*：
设计引?品牌设计/原型设计/帮我设计
## 团队架构
| Agent | 角色 | 职责 ||-------|------|------|| design-director | 设计总监 | 把控整体设计方向，协调各环节 || ux-researcher | UX研究?| 进行用户研究，收集设计需?|| design-system-builder | 设计系统构建?| 建设设计系统和组件库 || ui-designer | UI设计?| 设计界面视觉?|| prototype-builder | 原型构建?| 制作交互原型 || quality-reviewer | 质量评审?| 审核设计质量，确保一致?|
## SOP 流程
### Phase 1：
需求发?**输入**：
产品需求或用户故事**输出**：
`design-brief.md`**目的**：
明确设计目标和约束**步骤**?1. ux-researcher 进行用户研究2. design-director 分析设计霢?3. 输出设计箢?
### Phase 2：
设计系?**输入**：
design-brief.md**输出**：
`design-system.md` + `design-tokens.md`**目的**：
建立设计规范和组件?**步骤**?1. design-system-builder 定义设计token2. 构建组件库和设计规范3. 输出设计系统文档
### Phase 3：
界面设?**输入**：
design-system.md**输出**：
UI设计?**目的**：
完成各页面的视觉设?**步骤**?1. ui-designer 按规范设计各页面2. 确保视觉丢致?3. 输出设计稿文?
### Phase 4：
原型制?**输入**：
UI设计?**输出**：
`prototype.html`**目的**：
制作可交互的原?**步骤**?1. prototype-builder 将设计60转为HTML原型2. 添加页面跳转和交互效?3. 输出可演示的原型
### Phase 5：
质量评?**输入**：
prototype.html + 设计?**输出**：
`quality-review.md`**目的**：
确保设计质量达?**步骤**?1. quality-reviewer 从多维度评审设计2. 识别问题和改进点3. 输出评审报告
### Phase 6：
交付导?**输入**：
所有设计产?**输出**：
`deliverables/` 目录**目的**：
按要求格式导出交付?
## 阶段关卡（Phase Gates?
| 关卡 | 通过条件 | 失败处理 ||------|----------|----------|| PG1-霢?| 设计箢报包含完整的用户画像和需?| 补充用户研究 || PG2-设计系统 | 设计系统包含?0个组件，token完整 | 补充组件?|| PG3-界面 | 设计稿覆盖所有核心页?| 补充页面设计 || PG4-原型 | 原型可交互，页面跳转正确 | 修复交互逻辑 || PG5-评审 | 评审通过，无严重问题 | 修复评审发现的问?|
## 交接协议
```yaml---team_id: {team_id}agent_id: design-directorrole: 设计总监phase: discoverystatus: donefindings: |  设计方向：
简约现代风  目标用户?5-35岁职场人?  核心页面：
首?详情?个人中心---
```