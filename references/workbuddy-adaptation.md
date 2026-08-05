# WorkBuddy 适配指南 — 专家 / 专家团功能

> 本文件是 `team-orchestration` skill 在 **WorkBuddy** 环境下的适配说明，重点是让 skill 能正确使用 WorkBuddy 原生的「专家 / 专家团」能力。
> 对应上游：OpenCode / CodeBuddy 版 skill 中的 `Agent(name=...)` / `task(subagent_type=...)` 调用，在本环境需改为下方两种模式。

## 0. 核心结论

本 skill 内置的 **28 个专家团，就是 WorkBuddy「专家中心」里真实存在的原生专家团**（插件名完全一致）。
经核验，28/28 全部已安装在你本机：

- 安装位置：`~/.workbuddy/plugins/marketplaces/experts/plugins/<插件名>/`
- 已导出副本：`exported-experts/`（工作区）
- 完整清单与索引：`专家中心全量索引/全部专家总索引(331).html`

因此「适配」不是重新造轮子，而是：
1. **匹配后优先调用 WorkBuddy 原生专家团**（Mode A）；
2. **当必须在当前对话内就地执行团队时**，用 WorkBuddy 的 Agent（子智能体）能力模拟这些专家（Mode B）；
3. 修正脚本路径，使 `expert-matcher.py` / `task-decomposer.py` 等在本环境可直接运行。

## 1. WorkBuddy 专家 / 专家团系统速览

| 概念 | 说明 |
|---|---|
| 专家 (agent) | `expertType="agent"`，单一领域对话角色 |
| 专家团 (team) | `expertType="team"`，由 1 个主理人 + N 个成员 agent 组成的多角色团队 |
| 包结构 | 每个专家/团是一个插件包：`.codebuddy-plugin/plugin.json` + `agents/*.md`（成员人设）+ `skills/`（可选） |
| 入口 | WorkBuddy 左侧栏「**专家**」→ 专家中心，按分类浏览，点开即开启与该专家/团的对话 |
| 与 skill 的关系 | skill 的 `references/workbuddy-experts/<团队>/` 是这 28 个原生团的**人设镜像**（含 `plugin.json` + `agents/*.md`），可离线读取，用于 Mode B 模拟 |

## 2. 28 个专家团 → WorkBuddy 原生映射

全部 28 个团队均已在本机安装（✅）。「插件名」列即 WorkBuddy 专家中心里的团队标识，可直接用于 Mode A 调用。

| 插件名 (skill 团队名) | WorkBuddy 显示名 | 专业 | 分类 | Agent数 | 主理人 | 本地 |
|---|---|---|---|---|---|---|
| **软件公司（02-Engineering）** | | | | | |
| `software-company` | 软件开发团队 | 软件开发交付团队 | 02-Engineering | 5 | 齐活林 | ✅ |
| **产品设计（01-ProductDesign）** | | | | | |
| `design-engine` | 设计原型专家团 | 设计原型专家团 | 01-ProductDesign | 6 | 画统筹 | ✅ |
| `product-strategy-team` | 产品战略团队 | 产品战略与管理 | 01-ProductDesign | 6 | 方向明 | ✅ |
| **工程技术（02-Engineering）** | | | | | |
| `engineering-assurance-team` | 工程保障团队 | 全栈工程保障 | 02-Engineering | 6 | 甄宇航 | ✅ |
| `gstack` | 软件工坊 | 工程工作流团队 | 02-Engineering | 6 | 沽思航 | ✅ |
| `rum-fullstack-team` | 腾讯云 RUM 全链路专家团 | 前端监控全链路工坊 | 02-Engineering | 3 | 莱拉 | ✅ |
| **数据/AI（04-DataAI）** | | | | | |
| `ai-data-copilot` | 智数分析专家团 | 智数分析专家团 | 04-DataAI | 6 | 诺亚 | ✅ |
| `gpt-researcher-team` | 深度研究团队 | 多源深度研究报告工坊 | 04-DataAI | 7 | 顾全之 | ✅ |
| `huashu-data-pro` | 花叔数据分析专家团 | 花叔数据分析专家团 | 04-DataAI | 4 | 主理人 | ✅ |
| **营销增长（05-MarketingGrowth）** | | | | | |
| `content-monetization-team` | 内容变现商业化专家团 | 内容变现商业化专家团 | 05-MarketingGrowth | 5 | 芬利 | ✅ |
| `marketing-campaign-team` | 营销战役团队 | 营销战役与内容 | 05-MarketingGrowth | 5 | 江增量 | ✅ |
| `seo-content-team` | SEO 内容营销团队 | SEO 内容营销团队 | 05-MarketingGrowth | 7 | 搜尔文 | ✅ |
| `social-engagement-team` | 社媒互动增长专家团 | 社媒互动增长专家团 | 05-MarketingGrowth | 5 | 格罗斯 | ✅ |
| **内容创作（06-ContentCreative）** | | | | | |
| `ai-content-creator-team` | 内容创作专家团 | 内容创作专家团 | 06-ContentCreative | 5 | 司远 | ✅ |
| `content-distribution-team` | 全域内容分发专家团 | 全域内容分发专家团 | 06-ContentCreative | 5 | 安拓 | ✅ |
| `humanize-ppt-team` | 卡尔的人感PPT专家团 | PPT大纲、生成、视频、演示与交付专家团 | 06-ContentCreative | 7 | 主理人 | ✅ |
| `promo-creator-team` | 袋鼠帝宣传片创作团队 | 宣传片创作团队 | 06-ContentCreative | 6 | Max | ✅ |
| **销售/电商（07-SalesCommerce）** | | | | | |
| `sales-battle-team` | 销售作战团队 | 销售运营与情报 | 07-SalesCommerce | 5 | 应必达 | ✅ |
| **金融投资（08-FinanceInvestment）** | | | | | |
| `a-share-analysis` | A股研究团队 | A股全链路研究团队 | 08-FinanceInvestment | 8 | 古见远 | ✅ |
| `investment-masters-team` | 投资大师专家团 | AI对冲基金多大师投资分析专家团 | 08-FinanceInvestment | 22 | 贺知衡 | ✅ |
| `stock-partner-team` | 腾讯自选股金融分析专家团 | 腾讯自选股金融分析专家团 | 08-FinanceInvestment | 7 | 圆汇众 | ✅ |
| `trading-agent` | 交易分析团队 | 交易分析团队 | 08-FinanceInvestment | 13 | 何执舟 | ✅ |
| **运营/HR（09-OperationsHR）** | | | | | |
| `hr-operations-team` | HR 运营团队 | 人力运营与HR管理 | 09-OperationsHR | 5 | 任贤达 | ✅ |
| **项目/质量（10-ProjectQuality）** | | | | | |
| `openspec-doc-team` | 专业文档生成团队 | 企业级长文档生成工坊 | 10-ProjectQuality | 4 | 章成文 | ✅ |
| **法律/税务（11-SecurityCompliance）** | | | | | |
| `chatlaw-team` | 中文法律咨询团 | 中文法律咨询团 | 11-SecurityCompliance | 6 | 林律师 | ✅ |
| `enterprise-legal-team` | 企业法务专家团 | 企业法务专家团 | 11-SecurityCompliance | 9 | 法衡中 | ✅ |
| `tax-compliance-team` | 财税合规专家团 | 财税合规专家团 | 11-SecurityCompliance | 6 | 钱合规 | ✅ |
| **行业咨询（12-IndustryConsultant）** | | | | | |
| `opc-team` | 一人公司专家团 | 一人公司专家团 | 12-IndustryConsultant | 9 | 易牧 | ✅ |

## 3. 两种执行模式（关键）

匹配到团队后，按场景二选一：

### Mode A — 原生专家/专家团调用（推荐用于深度任务）

**做法**：主理人（你）完成「目标明确 + 拆解 + 匹配」后，**直接建议用户打开对应的 WorkBuddy 专家团**，由原生团在其自身对话上下文中执行（它自带工具、人设与 SOP，效果最好）。

**给用户的标准话术**：
> 这个任务建议交给 WorkBuddy 原生专家团「**<显示名>（<插件名>）**」处理。请在左侧栏「专家」→ 专家中心 → 搜索「<显示名>」或「<插件名>」打开它，把任务交给它即可。

**适用**：A股研究、法律咨询、税务合规、PPT制作、深度研究等需要专家自带工具链的任务。

**核验**：若用户反馈专家中心搜不到某团队，先用 `experts-download/` 或 `exported-experts/` 中的对应包在专家中心安装（或用 `expert-manager` 技能管理）。

### Mode B — 当前对话内就地模拟（用于必须在本会话完成协作时）

**做法**：主理人读取 skill 内置的团队人设，用 WorkBuddy 的 **Agent（子智能体）** 能力把成员「请进」当前对话，各自给结论，再由主理人汇总。这是本环境对 `Agent(name=...)` 的等价替代。

**步骤**：
1. 读 `references/workbuddy-experts/<团队>/plugin.json`，拿到 `members`（主理人 + 成员）与 `teamInfo.leadAgent`。
2. 读主理人 `.md`（如 `a-share-advisor.md`）了解该团的 SOP 与产出格式。
3. 按任务需要，用 Agent 工具起 **2~4 个最相关的成员** 作为 `general-purpose` 子智能体，每个的 prompt 包含：
   - 该成员的「角色 / 专业 / 人设」（从 `agents/<member>.md` 提取）
   - 任务背景与主理人给的分工
   - 输出要求（结构化、带置信度、标注不确定项）
4. 收齐各成员产出 → 主理人做交叉验证（Layer 1.5）→ 自验证 + 审核（Layer 2）→ 交付。

**子智能体 prompt 模板**：
```
你是 WorkBuddy 专家团「<显示名>」的成员「<成员中文名>（<member id>）」，专业：<profession>。
你的人设：<从 agents/<member>.md 提取的核心定位与原则，2-4 句>。

任务背景：<一句话>
主理人分配的分工：<具体子问题>
其他成员会从 <相关维度> 给结论，请聚焦你的专业，不要越界。

输出要求：
1. 直接给结论，分点，带数据/依据；
2. 对不确定的结论标注「不确定」并说明原因；
3. 不超过 400 字。
```

**注意**：
- 不要用 `expertType` 字段去「启动」一个不存在的 WorkBuddy 内部工具——WorkBuddy 没有按名字 spawn 任意专家的子智能体工具，Mode B 是读取人设 + Agent 模拟的务实方案。
- 默认不拉满 188 个 agent；按「角色分配」只起最相关的几个（奥卡姆剃刀）。

## 4. 主理人工作流（WorkBuddy 版）

```
接到任务
 → [目标明确] 用 5W2H 检测模糊度，必要时向用户澄清（≤2 轮）
 → [拆解] 运行 scripts/task-decomposer.py --task "..." --json
 → [匹配] 运行 scripts/expert-matcher.py --task "..." --json
            （或直接 --domains 08-FinanceInvestment 等）
 → [选模式] L1/L2 → 视情况 Mode A 建议原生团；L3/L4 → Mode A 优先，或 Mode B 就地编排
 → [执行] Mode A：建议用户打开原生专家团；Mode B：先运行 scripts/dispatch-planner.py 生成派工方案，再读人设 + Agent 子智能体协作
 → [交叉验证 Layer 1.5] 多来源三角互证，单来源标注中等置信
 → [自验证+审核] 每个结论自带检核；主理人做 Layer 2 审核 → 🟢/🟡/🔴
 → [交付 + 自进化] 记录反馈到 self-evolution-log.md（团队目录内）
```

**主理人铁律（适配版）**：
- 禁止**替用户做不可逆决策**（如「买/卖」「发律师函」）——只给带置信度的建议；
- 禁止跳过「目标明确 / 拆解 / 审核」阶段；
- 成员（子智能体）产出须经主理人汇总，不直接以成员名义交付给用户。

## 5. 脚本运行（WorkBuddy 环境）

本环境用托管 Python（Windows 无 `python3` 命令）。脚本路径已改为**相对自身**，与安装位置无关。

```powershell
# 托管 Python
$PY = "C:/Users/林昌/.workbuddy/binaries/python/versions/3.13.12/python.exe"
$SK = "C:/Users/林昌/.workbuddy/skills/team-orchestration"

# 任务拆解
& $PY "$SK/scripts/task-decomposer.py" --task "帮我分析宁德时代的基本面和估值" --json

# 专家匹配（自动调用拆解）
& $PY "$SK/scripts/expert-matcher.py" --task "帮我分析宁德时代的基本面和估值" --json

# 按领域直接匹配
& $PY "$SK/scripts/expert-matcher.py" --domains 08-FinanceInvestment --top-k 3

# Mode B 派工方案生成（自动拆解+匹配，输出派工计划与逐成员子任务）
& $PY "$SK/scripts/dispatch-planner.py" --task "帮我分析宁德时代的基本面和估值，并给买入建议" --top-k 2
# 也支持直接指定团队 / 按领域：
# & $PY "$SK/scripts/dispatch-planner.py" --teams a-share-analysis stock-partner-team --task "..."
# & $PY "$SK/scripts/dispatch-planner.py" --domains 08-FinanceInvestment --top-k 2
# 产物：last_dispatch_plan.md（可读）+ last_dispatch_plan.json（机器读）
```

> Mode B 执行协议（如何按派工方案拉起 Agent 子智能体）见 SKILL.md 的「Mode B 执行协议」一节。

> 匹配结果中的 `name` 即第 2 节的「插件名」，可直接用于 Mode A 在专家中心打开，或用于 Mode B 读取 `references/workbuddy-experts/<name>/` 人设。

## 6. 自进化（Loop 1/2/3）

- **Loop 1（秒级）**：执行中反思，追加 `references/workbuddy-experts/<团队>/self-evolution-log.md`。
- **Loop 2（分钟级）**：事后回顾 → `scripts/self-evolution/post-task-evolve.py`。
- **Loop 3（小时级）**：主动联网增强 → `scripts/self-evolution/proactive-search.py --experts all`。
- 脚本 `EXPERT_DIR` 已改为相对路径，可直接运行。

## 7. 与审判庭核心机制的集成

v2.5 升级后，本适配指南作为**资产桥接层**中专家团的底层实现：

| 适配章节 | 被审判庭哪层使用 | 说明 |
|---------|----------------|------|
| §1-2 专家团速览+映射表 | 资产桥接层 Expert Resolver | 议题匹配时读取团队分类 |
| §3 Mode A/B | Phase B 举证阶段的资产注入 | 在子代理 prompt 中推荐 Mode A 原生团 |
| §4 主理人工作流 | 映射为审判庭四阶段 (见 `trial-court-architecture.md`) | 原步骤拆入立案→举证→质证→终审 |
| §5 脚本运行 | 审判庭脚本扩展 | 新增 `trial-court-orchestrator.py` + `asset-resolver.py` |
| §6 自进化 | 审判庭自学习层 S2/S3 | 专家调度优化读取 workbuddy 团队的 self-evolution-log |

**资产桥接层的完整设计（⚠️ 该文档已标注 DEPRECATED，v3.1 以 config.yaml 为唯一权重源）**：`references/workbuddy-asset-bridge.md`
**审判庭架构文档**：`references/trial-court-architecture.md`

---
*本适配由 WorkBuddy 在安装工程 `team-orchestration` skill（v2.5.0，审判庭核心机制版）时生成。28/28 原生专家团已确认本机安装。*
