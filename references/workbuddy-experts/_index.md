# WorkBuddy 专家库移植索引

> 来源: WorkBuddy (Tencent CodeBuddy) Expert Marketplace
> 移植日期: 2026-07-10
> 总数: 302 个专家团, 520 个子 Agent

## 分类索引

### 01-金融投资 (4)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [investment-masters-team](investment-masters-team/) | 22 | 贺知衡 · 基金经理 | 13位投资大师+6位分析师并行分析 |
| [trading-agent](trading-agent/) | 13 | 何执舟 · 首席策略官 | 5阶段交易分析, 输出HTML报告 |
| [stock-partner-team](stock-partner-team/) | 7 | 圆汇众 · 投研主编 | 六位实战炒股大神经验蒸馏 |
| [a-share-analysis](a-share-analysis/) | 8 | 古见远 · A股策略官 | A股全链路研究, 6 Workflow |

### 02-内容创作 (4)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [ai-content-creator-team](ai-content-creator-team/) | 5 | 司远 · 创意总监 | AI多模态内容生产 |
| [content-distribution-team](content-distribution-team/) | 5 | 安拓 · 分发策略师 | 一站式多平台内容分发 |
| [content-monetization-team](content-monetization-team/) | 5 | 芬利 · 商业化策略师 | CPS/CPE/CPM变现 |
| [promo-creator-team](promo-creator-team/) | 6 | Max | 产品宣传片全流程制作 |

### 03-营销增长 (4)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [marketing-campaign-team](marketing-campaign-team/) | 5 | 江增量 | 内容/策划/SEO/品牌 |
| [sales-battle-team](sales-battle-team/) | 5 | 应必达 | 销售全周期 |
| [seo-content-team](seo-content-team/) | 7 | 搜尔文 | 5阶段SEO内容营销 |
| [social-engagement-team](social-engagement-team/) | 5 | 格罗斯 | 社媒互动增长 |

### 04-设计/PPT (2)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [design-engine](design-engine/) | 6 | 画统筹 | 71套设计系统, 6角色 |
| [humanize-ppt-team](humanize-ppt-team/) | 7 | 主理人 | PPT大纲→视频→演讲→质检 |

### 05-工程/技术 (4)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [software-company](software-company/) | 5 | PM | 软件开发全流程 |
| [engineering-assurance-team](engineering-assurance-team/) | 6 | 工程总监 | 架构/SRE/代码审查/测试 |
| [gstack](gstack/) | 6 | Lead | 产品审查/安全审计/QA |
| [rum-fullstack-team](rum-fullstack-team/) | 3 | Lead | 腾讯云RUM |

### 06-法律/税务 (3)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [chatlaw-team](chatlaw-team/) | 6 | 林律师 | 4阶段法律咨询 |
| [enterprise-legal-team](enterprise-legal-team/) | 9 | 法衡中 | 8项企业法务 |
| [tax-compliance-team](tax-compliance-team/) | 6 | 合规总监 | 企业税务合规 |

### 07-研究/数据 (3)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [gpt-researcher-team](gpt-researcher-team/) | 7 | 顾全之 | 5阶段深度研究 |
| [huashu-data-pro](huashu-data-pro/) | 4 | 数据主管 | 数据分析全链路 |
| [ai-data-copilot](ai-data-copilot/) | 6 | 诺亚 | SQL/EDA/RAG/可视化 |

### 08-HR/运营 (2)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [hr-operations-team](hr-operations-team/) | 5 | HR总监 | 招聘/绩效/合规 |
| [opc-team](opc-team/) | 9 | 主理人 | 一人公司方法论 |

### 09-产品 (1)

| 专家团 | Agent 数 | 主理人 | 说明 |
|--------|---------|--------|------|
| [product-strategy-team](product-strategy-team/) | 6 | 产品总监 | PRD/用户研究/路线图 |

### 10-虚拟团 (3)

| 虚拟团 | Agent 数 | 说明 |
|--------|---------|------|
| [game-development](game-development/) | 21 | 游戏开发全流程：策划/美术/程序/QA/运营 |
| [industry-consulting](industry-consulting/) | 25 | 行业研究与战略咨询：分析师/顾问/研究员 |
| [tencent-ecosystem](tencent-ecosystem/) | 15 | 腾讯生态集成：云架构/营销/合规/技术 |

### 独立专家 (271)

来自 agency-agents 的 271 个独立专家，按 19 个品类组织。详见 [groups/README.md](groups/README.md)。

## 独立专家（S2 新增）

经 S2 从 `agency-agents/` 导入 271 个独立专家到 `workbuddy-experts/`：

- 每个独立专家一个目录，含 `plugin.json`（expertType: individual）+ `agents/expert.md`
- 自动分组到虚拟团（game-development / industry-consulting / tencent-ecosystem / ungrouped）
- 完整清单见 [shared/manifest-post-s2.json](../shared/manifest-post-s2.json)
- 回滚方式: `python3 scripts/migrate-workbuddy.py undo shared/manifest-post-s2.json`

## 移植适配

| 适配项 | 处理 |
|--------|------|
| `connect_cloud_service` | 已删除 |
| `Agent(name=...)` | 改为 `task(subagent_type=...)` |
| `SendMessage` | 保留语义 |
| `plugin.json` | 完全保留 |
| avatars/ | 未移植 |
