# 专家库索引（QoderWork 融合版）

> 来源: 内置 28 专家团 (WorkBuddy/CodeBuddy) + QoderWork 套件市场 23 插件融入
> 融合日期: 2026-07-31
> 总数: 39 个专家团（28 原有 + 11 新建），6 个原有团队已增强。
> 补齐状态(2026-08-09): 11 个新建团队已补齐为成员完整（agent-template 标准 + verified 标记），见 `_template/agent-template.md`

## 融合说明

| 融合方式 | 数量 | 说明 |
|---------|------|------|
| 新建独立团队 | 11 | QoderWork 套件无内置对应，直接吸收 |
| 增强现有团队 | 6 | 能力重叠，将套件能力并入描述 |
| 保持原有不变 | 22 | 无对应套件，原样保留 |

## 分类索引

> **domain 映射（Phase 0 分级加载）**：本表按 categoryId 分组，即"任务域 = 分组头"。定域时用 SKILL.md §8.1 触发词 → 落到下列分组即可。tier 统一为：`plugin.json` 元数据属 **T1 分域**、单 agent `agents/*.md` 人设属 **T2 惰性**（进队才读）。若任务跨域，取命中度最高域为主、通用对抗兜底。

### 08-FinanceInvestment 金融投资 (8)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [investment-masters-team](investment-masters-team/) | 22 | 贺知衡 | 13位投资大师+6位分析师+价值投资Python工具 | 原有+增强 |
| [trading-agent](trading-agent/) | 13 | 何执舟 | 5阶段交易分析, 输出HTML报告 | 原有 |
| [stock-partner-team](stock-partner-team/) | 7 | 圆汇众 | 六位实战炒股大神经验蒸馏 | 原有 |
| [a-share-analysis](a-share-analysis/) | 8 | 古见远 | A股全链路研究, 6 Workflow | 原有 |
| [equity-research](equity-research/) | 6 | 研主编 | 深度报告/行业研究/年报/业绩点评/研报精编 | **新建·已补齐** |
| [wealth-management](wealth-management/) | 6 | 财管家 | 资产配置/基金分析/财务规划/税务规划 | **新建·已补齐** |
| [pe-vc-investment](pe-vc-investment/) | 6 | 投委会主席 | 项目筛选/尽调/Term Sheet/回报建模/退出 | **新建·已补齐** |
| [investment-banking](investment-banking/) | 6 | 保荐人 | IPO/并购/债券/监管问询/路演/财务建模 | **新建·已补齐** |

### 06-ContentCreative 内容创作 (4)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [ai-content-creator-team](ai-content-creator-team/) | 5 | 司远 | AI多模态内容生产 | 原有 |
| [content-distribution-team](content-distribution-team/) | 5 | 安拓 | 一站式多平台内容分发 | 原有 |
| [content-monetization-team](content-monetization-team/) | 5 | 芬利 | CPS/CPE/CPM变现 | 原有 |
| [promo-creator-team](promo-creator-team/) | 6 | Max | 产品宣传片全流程制作 | 原有 |

### 05-MarketingGrowth 营销增长 (4)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [marketing-campaign-team](marketing-campaign-team/) | 5 | 江增量 | 全链路营销：内容/SEO/品牌/广告合规/绩效 | 原有+增强 |
| [sales-battle-team](sales-battle-team/) | 5 | 应必达 | 销售全周期 | 原有 |
| [seo-content-team](seo-content-team/) | 7 | 搜尔文 | 5阶段SEO内容营销 | 原有 |
| [social-engagement-team](social-engagement-team/) | 5 | 格罗斯 | 社媒互动增长 | 原有 |

### 01-ProductDesign 产品与设计 (3)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [product-strategy-team](product-strategy-team/) | 6 | 方向明 | 产品全生命周期：PRD/用户故事/竞品/指标/路线图 | 原有+增强 |
| [design-engine](design-engine/) | 6 | 画统筹 | 71套设计系统, 6角色视觉产出 | 原有 |
| [product-design-suite](product-design-suite/) | 7 | 设计总监 | UX全流程11场景28技能（用研/IA/交互/可用性） | **新建·已补齐** |

### 02-Engineering 工程与云原生 (7)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [software-company](software-company/) | 5 | 齐活林 | 软件开发全流程 | 原有 |
| [engineering-assurance-team](engineering-assurance-team/) | 6 | 甄宇航 | 架构/SRE/代码审查/测试/质量工程/接口分析 | 原有+增强 |
| [gstack](gstack/) | 6 | 沽思航 | 产品审查/安全审计/QA | 原有 |
| [rum-fullstack-team](rum-fullstack-team/) | 3 | 莱拉 | 腾讯云RUM前端监控 | 原有 |
| [alicloud-engineering](alicloud-engineering/) | 7 | 云架构师 | 阿里云运维/Terraform/迁移SOP | **新建·已补齐** |
| [devtools-engineering](devtools-engineering/) | 5 | 工具链负责人 | 多仓Git/AI测试/接口逻辑分析 | **新建·已补齐** |
| [humanize-ppt-team](humanize-ppt-team/) | 7 | 主理人 | PPT大纲→视频→演讲→质检 | 原有 |

### 11-SecurityCompliance 法律与财税 (4)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [chatlaw-team](chatlaw-team/) | 6 | 林律师 | 4阶段法律咨询 | 原有 |
| [enterprise-legal-team](enterprise-legal-team/) | 9 | 法衡中 | 企业法务+合同管理（审查/红线/NDA/电子签） | 原有+增强 |
| [tax-compliance-team](tax-compliance-team/) | 6 | 钱合规 | 企业财税一体化（税务/记账/预算/内审/报表） | 原有+增强 |
| [cn-litigation](cn-litigation/) | 6 | 主诉律师 | 民商事诉讼全生命周期（20技能4层） | **新建·已补齐** |

### 04-DataAI 研究与咨询 (4)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [gpt-researcher-team](gpt-researcher-team/) | 7 | 顾全之 | 5阶段深度研究 | 原有 |
| [huashu-data-pro](huashu-data-pro/) | 4 | 数据主管 | 数据分析全链路 | 原有 |
| [ai-data-copilot](ai-data-copilot/) | 6 | 诺亚 | SQL/EDA/RAG/可视化 | 原有 |
| [consulting-delivery](consulting-delivery/) | 6 | 项目总监 | 咨询交付：桌面研究/框架/报告/标杆/高管简报 | **新建·已补齐** |

### 07-SalesCommerce 电商与供应链 (2)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [ecommerce-1688](ecommerce-1688/) | 6 | 电商总监 | 1688买方选品/卖方运营/数据/转化 | **新建·已补齐** |
| [sales-battle-team](sales-battle-team/) | 5 | 应必达 | 销售全周期（也归属营销增长） | 原有 |

### 09-OperationsHR 组织运营 (2)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [hr-operations-team](hr-operations-team/) | 5 | 任贤达 | 招聘/绩效/合规 | 原有 |
| [opc-team](opc-team/) | 9 | 易牧 | 一人公司方法论 | 原有 |

### 12-IndustryConsultant 行业咨询 (2)

| 专家团 | Agent 数 | 主理人 | 说明 | 来源 |
|--------|---------|--------|------|------|
| [tech-service-transfer](tech-service-transfer/) | 6 | 转化总监 | 科技服务转化：需求挖掘/成果匹配/量产/融资 | **新建·已补齐** |
| [openspec-doc-team](openspec-doc-team/) | 4 | 章成文 | 企业级长文档生成 | 原有 |

## 融合适配记录

| 适配项 | 处理 |
|--------|------|
| QoderWork 套件 → plugin.json | 字段映射：folderName→name, description→displayDescription.zh |
| categoryId 分配 | 按领域归入现有分类体系 |
| agents/*.md 人设 | 新建团队生成主理人 stub，成员待按需补充 |
| 增强团队 | 更新 displayDescription + profession，标注 _enhancedWith |
| expert-matcher.py | 无需修改（自动发现机制） |
