# 任务级 Skill 封装（Skills Pack · v3.9 · TC-20260816-5）

> 定位：Agent Skills 思想落地（B站《Agent Skills 实战》核心观点：任务级能力封装 = 工具+人设+流程 → 可复用 skill，比工具高一层、比完整 agent 低一层）。把高频任务封装为"触发词 + 团队组合 + 流程 + 输出契约"，专家团作为**人设池**、skill 作为**任务模板**。
> 协同：聚合域路由（SKILL.md §8.1）——定域 → 域内 agent 池跨团队组队 → 按 skill 流程执行。

## Skill-01 投资分析（试点）

| 项 | 内容 |
|---|---|
| **触发词** | 分析/估值/买入/卖出/多空/基本面/技术面/持仓建议 |
| **团队组合** | 投资分析域（investment-masters + trading-agent + stock-partner + a-share-analysis + equity-research）——按任务维度激活：基本面→investment-masters/equity-research；技术面→trading-agent/stock-partner；A股→a-share-analysis |
| **流程** | ① 定标的/问题（5W2H ≤2 轮）→ ② 并行举证（域内 2-4 agents：价值派/技术派/风险派独立估值）→ ③ 质证（1 轮，分歧>2 追加）→ ④ 数值聚合（统计聚合优先：估值/目标价取中位数+区间）→ ⑤ 二审终审（加权投票 believability）→ ⑥ 输出 BUY/SELL/HOLD + 依据 + 置信度 |
| **输出契约** | 投资结论（方向 + 目标价区间 + 置信度 + 关键依据 + 风险）+ 延续 A3 格式（conclusions/evidence/risks/actions） |
| **工具链** | financial MCP（如有）/ knowledge（stock-analyst/hk-stock-analysis/macro-analyst/valuation-expert/money-flow-tracker） |
| **验证** | expert-matcher 对"帮我分析宁德时代"应召回投资分析域团队（score 前三在域内） |

## Skill-02 法律咨询（定稿）

| 项 | 内容 |
|---|---|
| **触发词** | 合同/诉讼/起诉/合规/知产/税务/仲裁/劳动纠纷 |
| **团队组合** | 法律服务域（chatlaw-team + cn-litigation + enterprise-legal-team + tax-compliance-team）——按问题类型路由：一般咨询→chatlaw；诉讼/仲裁→cn-litigation；企业合规/合同→enterprise-legal；税务→tax-compliance |
| **流程** | ① 案情采集（当事人/事实/诉求 5W2H）→ ② 法条+判例研究（域内并行：检索条文/类案）→ ③ 质证（1 轮，分歧>2 追加）→ ④ 法律意见撰写（依据条文 + 风险等级 + 诉讼策略建议）→ ⑤ 终审（禁止引入新论点） |
| **输出契约** | 法律意见书：结论 + 依据条文（精确到条/款）+ 风险等级（高/中/低）+ 行动建议（下一步清单）+ 置信度 |
| **工具链** | knowledge 最小集（contract-reviewer/legal-researcher/litigation-strategist/ip-specialist/privacy/regulatory/tax-compliance/precedent）+ 法条检索 MCP（如有） |
| **验证** | `expert-matcher --domain 法律服务 --task "帮我审一份劳动合同" --top-k 3` 应召回 chatlaw/enterprise-legal 前列 |

## Skill-03 内容生产（定稿）

| 项 | 内容 |
|---|---|
| **触发词** | 文案/视频/宣传片/图文/分发/变现/投放素材 |
| **团队组合** | 内容全链路域（ai-content-creator + content-distribution + content-monetization + promo-creator）——流水线路由：创作→ai-content-creator；分发→content-distribution；变现→content-monetization；宣传片→promo-creator |
| **流程** | ① 需求定义（平台/受众/目标）→ ② 创作（域内并行：文案+视觉+视频多稿）→ ③ 审核（合规/风格/转化要素）→ ④ 分发方案（平台适配+排期）→ ⑤ 变现与复盘（数据→优化建议） |
| **输出契约** | 内容包：成稿 + 分发排期 + 预期指标 + 复盘要点 + 置信度 |
| **工具链** | knowledge（content-director/scriptwriter/video-editor/visual-artist/synthesis-writer）+ 平台 MCP（如有） |
| **验证** | `expert-matcher --domain 内容全链路 --task "写一篇小红书种草文案" --top-k 3` 应召回 ai-content-creator 前列 |

## Skill-04 技术审查（定稿）

| 项 | 内容 |
|---|---|
| **触发词** | 代码审查/架构评审/QA/安全审计/云迁移/性能优化 |
| **团队组合** | 工程保障域（engineering-assurance + gstack + devtools-engineering + rum-fullstack + alicloud-engineering + software-company）——路由：架构→engineering-assurance；代码/QA→gstack+devtools；云→alicloud；前端监控→rum |
| **流程** | ① 审查范围界定（代码/架构/安全/云）→ ② 域内并行审查（多视角：架构师/QA/安全）→ ③ 质证合并（问题分级：阻断/严重/建议）→ ④ 修复方案（含验证方法）→ ⑤ 终审（问题清单 + 优先级 + 验收标准） |
| **输出契约** | 审查报告：问题清单（级别+位置+影响）+ 修复建议（方案+验证）+ 验收标准 + 置信度 |
| **工具链** | knowledge（platform-adapter/platform-analyst/ai-data-copilot）+ git/MCP（如有） |
| **验证** | `expert-matcher --domain 工程保障 --task "做一次代码审查" --top-k 3` 应召回 gstack/engineering-assurance 前列 |

## Skill-05 深度研究（定稿）

| 项 | 内容 |
|---|---|
| **触发词** | 调研/研究报告/行业分析/竞品分析/技术综述 |
| **团队组合** | gpt-researcher-team（通用对抗兜底，独立）+ 数据智能域（ai-data-copilot/huashu-data-pro 数据支撑）——主研→gpt-researcher 五阶段；数据取数→ai-data-copilot；Excel/本地数据→huashu-data-pro |
| **流程** | ① 研究问题定义（假设+范围）→ ② 数据收集（域内：联网调研+数据分析）→ ③ 多源交叉验证（≥2 独立来源）→ ④ 报告框架（大纲→逐章）→ ⑤ 终审（结论 + 局限 + 置信度） |
| **输出契约** | 研究报告：摘要 + 关键发现 + 证据链（来源独立）+ 局限 + 置信度 |
| **工具链** | knowledge（industry-researcher/stock-analyst 等按域取）+ 联网检索 MCP |
| **验证** | `expert-matcher --domain 数据智能 --task "调研一下A股半导体行业" --top-k 3` 应召回 ai-data-copilot/huashu-data-pro（gpt-researcher 经通用兜底路径） |

---
*Skill 封装目录（01-05 全部定稿）。新增 skill 遵循：触发词明确 + 团队组合可路由（聚合域）+ 流程有终态门 + 输出契约可校验。*
