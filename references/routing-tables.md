# 路由与参考索引（SKILL.md §8-§8.2 外移 · TC-20260816-9 瘦身）

> 由 SKILL.md 正文外移，按需读取。立案定域/技能路由/参考文件清单用本节。

## 8 参考文件（按需读取）

| 文件 | 用途 |
|------|------|
| `references/trial-court.md` | 完整审判庭协议细节（现行补充协议） |
| `references/agent-teams-absorption.md` | **dsh-agent-teams 优秀设计吸收（v3.6）：依赖感知任务图 + durable 邮箱 + 成员 persona + 工具级越权防护 + 磁盘即真相 + 归档化删除 + fail-loud 纪律（§4.0/§4.2.1/A5 的详版模板）** |
| `references/trial-court-protocol.md` | 审判庭五阶段详细执行规范（二审终审制：一审裁决/回灌修订/二审终审，含案卷归档/自学习S1/S2/终审七段式） |
| `references/workbuddy-experts/_index.md` | 40 专家团索引 |
| `references/workbuddy-adaptation.md` | WorkBuddy 移植历史参考（压缩版；现行事实源=`workbuddy-experts/_index.md` + `dsh-adaptation.md`） |
| `references/skills-pack.md` | **任务级 Skill 封装（v3.9 · TC-20260816-5）：触发词 + 团队组合 + 流程 + 输出契约（Agent Skills 思想落地）** |
| `references/data-provenance.md` | **数据来源可靠性矩阵（v3.9 · TC-20260816-6）：记录/外部数据的来源分层与查证方式** |
| `references/zcode-adaptation.md` | **ZCode 适配指南（实测：task 调度、mini-vision 视觉路由、产物收集、TRIAL_BASE、路径映射）** |
| `references/dsh-adaptation.md` | **DSH 适配指南（实测映射：subagent/send_message 调度、视觉路由、检查点/续审、脚本调用、安装落点与可见性）** |
| `references/opencode-adaptation.md` | OpenCode 适配历史（v3.2.0-opencode，存档参考） |
| `references/cross-validation.md` | 交叉验证规则 |
| `references/test-workflow.md` | **改本技能逻辑/契约/脚本前必先读，作为回归门禁（触发守则见该文件 §3.1/§4）** |

## 8.1 加载决策（分域路由）· Phase 0

> **守卫（三行，必读）**：① 非白名单团队仍可**追加读取**（懒加载，不阻断）；② 冲突时以 `expert-matcher` 检索结果 + lead 判断为准；③ 通用对抗兜底（`gpt-researcher-team`）**始终可选**。
> **定位**：本文是**文档级判断纪律工具**（省 lead 定域判断成本 + 有界读取），**不承诺 token 百分比节省**；"默认跳过 ≠ 禁止读取"。

**定域流程**：立案用下方触发词 → 定 `domain` → 加载该域 T1 团队头寸 + knowledge 最小集 → 进队 agent 人设按需（T2 惰性，`read_agent_md` 已内置）。

**聚合域路由（v3.9 · TC-20260816-5；v3.10.3 · TC-20260816-9 补全）**：40 团队归入 10 组（8 业务域 + 通用对抗 + 通用兜底），完整归组见 **`references/domain-map.json`**（40 团全覆盖，categoryId 13 类归并），域入口文件 `references/workbuddy-experts/_domain/<domain>.md`（立案定域只读该入口）。定域后**跨团队按需组队**（agent 超网思想：257 agents 为组件池，按任务组合激活，不物理合并目录）。团队目录/plugin.json 保留，expert-scores/脚本引用零破坏：

| 聚合域 | 团队（目录保留） | 触发词补充 |
|---|---|---|
| 投资分析 | investment-masters + trading-agent + stock-partner + a-share-analysis + equity-research | 买入/卖出/估值/多空 |
| 资本服务 | pe-vc-investment + investment-banking + wealth-management | 融资/IPO/家族办公室 |
| 法律服务 | chatlaw-team + cn-litigation + enterprise-legal-team + tax-compliance-team | 起诉/合同审查/合规 |
| 内容全链路 | ai-content-creator + content-distribution + content-monetization + promo-creator | 视频/文案/分发/变现 |
| 营销增长 | marketing-campaign + sales-battle + seo-content + social-engagement | 投放/线索/SEO/社媒 |
| 工程保障 | engineering-assurance + gstack + devtools-engineering + rum-fullstack + alicloud-engineering + software-company | 架构评审/代码审查/QA/云 |
| 数据智能 | ai-data-copilot + huashu-data-pro | SQL/数据分析（gpt-researcher 独立=通用对抗兜底） |
| 产品设计 | product-strategy + design-engine + product-design-suite | PRD/UX/设计系统 |

> 任务级 skill 封装（触发词 + 团队组合 + 流程）见 `references/skills-pack.md`。

## 8.2 技能路由表（v3.10 · TC-20260816-7）

> 任务域 → 当前机器技能候选（多客户端根）。**优先实时召回**：`asset-resolver.py --task "<任务>" [--project-dir <工作区>]` 按触发词匹配（2-gram 中英）；本表为**静态兜底**（asset-resolver 不可用时）。子代理 prompt 按 §4-3 注入技能候选（≤5），候选外技能不注入。敏感技能（disable-model-invocation）已被 asset-resolver 自动排除。

| 任务域 | 技能候选（agents 源优先） | 触发例 |
|--------|--------------------------|--------|
| product | create-prd / product-strategy / user-stories / prioritize-features / lean-canvas / wwas | PRD/路线图/需求拆解/排优先级 |
| marketing | marketing-plan / copywriting / ad-creative / ads / cro / aso / customer-research / competitor-analysis / competitor-profiling / competitors / cold-email / pricing | 营销方案/文案/投放/转化/ASO/竞品/冷邮/定价 |
| content | story-studio（故事族编排器）/ wewrite（公众号）/ baoyu-image-gen / baoyu-comic / baoyu-translate / baoyu-slide-deck / bili-daily / stop-slop | 公众号/网文/配图/漫画/翻译/PPT/字幕 |
| taste/design | design-taste-frontend / frontend-ui-engineering / high-end-visual-design / baoyu-diagram / image-to-code | 前端/视觉/图表/设计系统 |
| security | skillspector / intended-vs-implemented / security-and-hardening / auditor | 技能安全扫描/代码审计/合规 |
| tool | firecrawl（族）/ sql-queries / graphify / browser-cdp / firecrawl-parse | 抓取/查询/知识图谱/浏览器/解析 |
| data | analytics / cohort-analysis / sentiment-analysis / metrics-dashboard | 埋点/留存/反馈/指标 |
| strategy | foresight（前瞻分析）/ pestle-analysis / swot-analysis / competitor-analysis / competitor-profiling | 预测/情景推演/PESTLE/SWOT/竞争情报 |

> 域冲突时以 asset-resolver 触发词得分 + main 判断为准；未命中任何域 → 不注入技能候选（子代理仅凭 available_skills 自动面）。

**兜底（表外/跨界/新团队）**：触发词未命中静态表时，交语义判断 —— `python scripts/expert-matcher.py --task "<任务原文>" --top-k 4 --json`，按其得分高的团队为准；仍无高分(score<0.25)则回退通用对抗（gpt-researcher-team）。优先级：静态表(快) → LLM语义(matcher) → 通用兜底。冲突以 matcher 语义得分为准。

| 任务域 | 触发词例 | T1 expert 团队（完整目录名） | T1 knowledge（最小） | 默认跳过（启发式） |
|--------|---------|---------------------------|---------------------|------------------|
| 投资/金融 | 股票/基金/A股/港股/PE/VC/估值 | investment-masters-team, trading-agent, stock-partner-team, a-share-analysis, equity-research, wealth-management, pe-vc-investment, investment-banking | stock-analyst, hk-stock-analysis, macro-analyst, valuation-expert, money-flow-tracker | content / marketing / product / engineering / legal |
| 法律/财税 | 合同/诉讼/合规/知产/税务/仲裁 | cn-litigation, chatlaw-team, enterprise-legal-team, tax-compliance-team | contract-reviewer, legal-researcher, litigation-strategist, ip-specialist, privacy, regulatory, tax-compliance, precedent | investment / content / product / engineering |
| 内容创作 | 视频/脚本/文案/视觉/宣传/分发 | ai-content-creator-team, content-distribution-team, content-monetization-team, promo-creator-team | content-director, scriptwriter, video-editor, visual-artist, synthesis-writer | legal / investment / engineering |
| 营销增长 | 营销/SEO/销售/社媒/增长 | marketing-campaign-team, sales-battle-team, seo-content-team, social-engagement-team | prompt-patterns, platform-analyst | legal / investment / engineering |
| 产品设计 | PRD/UX/竞品/设计系统 | product-strategy-team, design-engine, product-design-suite | prompt-patterns | marketing / legal / investment |
| 技术工程 | 开发/架构/云/测试/审查 | software-company, engineering-assurance-team, gstack, rum-fullstack-team, alicloud-engineering, devtools-engineering | platform-adapter, platform-analyst, ai-data-copilot | investment / legal / content |
| **通用多agent对抗** | 无法归类 / 跨 3+ 域 L3 | gpt-researcher-team + general-critics（通才批判团）+ 通用 agent 池 | 不预载，仅 T0 | 无（降级不硬选） |

> 完整版与命名对照见 `references/expert-matching.md`「分域加载决策表（Phase 0）」。
