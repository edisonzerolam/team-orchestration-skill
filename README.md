# Team Orchestration Skill — 多智能体团队编排引擎

> 专家池借鉴了包括 WorkBuddy、QoderWork 的专家功能

## 概述

这是一个 OpenCode / CodeBuddy 兼容的 Skill 包, 提供**多智能体团队编排**能力。核心流程:

```
任务 → 第一性原理拆解 → 动态专家匹配 → 团队执行 → 自验证+审核 → 交付 → 三环自进化
```

## 核心特性

### 🔍 第一性原理任务拆解
不依赖预定义模板, 从任务本质出发逐层拆解 (5 维: 本质类型/知识域/能力/复杂度/质量要求)

### 🎯 动态专家匹配
40 个专家团 (257 个子 Agent) 可选, 按领域匹配度/能力匹配度/历史表现/负载评分自动推荐

### 🤝 完整团队协作
- 10 个预设团队模板 (快速路径)
- 39 个移植专家团 (深度路径)
- 主理人铁律: 禁止代写、禁止跳过阶段、禁止直连

### ✅ 自验证 + 审核门 (强制)
所有产出物必须经过 @reviewer 审核 🟢/🟡/🔴

### 🔄 三环自进化
| 环 | 速度 | 做什么 |
|----|------|--------|
| Loop 1 | 秒级 | 执行中反思, 追加 self-evolution-log.md |
| Loop 2 | 分钟级 | 事后回顾, 更新 expert-scores.json |
| Loop 3 | 小时级 | 主动联网搜索, 半自动知识合并 |

## 40 个专家团一览

### 金融投资 (4)
| 专家团 | Agent数 | 主理人 | 说明 |
|--------|---------|--------|------|
| investment-masters-team | 22 | 贺知衡 | 13位投资大师+6位分析师并行 |
| trading-agent | 13 | 何执舟 | 5阶段交易分析, 输出HTML |
| stock-partner-team | 7 | 圆汇众 | 六位炒股大神实战经验 |
| a-share-analysis | 8 | 古见远 | A股全链路研究, 6 Workflow |

### 内容创作 (4)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| ai-content-creator-team | 5 | AI多模态: 视频/图文/剪辑/改编 |
| content-distribution-team | 5 | 12+平台一站式分发 |
| content-monetization-team | 5 | CPS/CPE/CPM变现 |
| promo-creator-team | 6 | 产品宣传片全流程制作 |

### 营销增长 (4)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| marketing-campaign-team | 5 | 内容/策划/SEO/品牌 |
| sales-battle-team | 5 | 客户研究/外联/竞情/预测 |
| seo-content-team | 7 | 5阶段SEO内容营销 |
| social-engagement-team | 5 | 社媒互动增长 |

### 设计/PPT (2)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| design-engine | 6 | 71套设计系统, 需求→原型→审查 |
| humanize-ppt-team | 7 | PPT大纲→HTML→视频→演讲→质检 |

### 工程/技术 (4)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| software-company | 5 | 软件开发全流程 |
| engineering-assurance-team | 6 | 架构/SRE/审查/测试 |
| gstack | 6 | 产品审查/安全审计/QA |
| rum-fullstack-team | 3 | 腾讯云RUM |

### 法律/税务 (3)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| chatlaw-team | 6 | 4阶段法律咨询 |
| enterprise-legal-team | 9 | 8项企业法务 |
| tax-compliance-team | 6 | 企业税务合规 |

### 研究/数据 (3)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| gpt-researcher-team | 7 | 5阶段深度研究 |
| huashu-data-pro | 4 | 数据分析全链路 |
| ai-data-copilot | 6 | SQL/EDA/RAG/可视化 |

### HR/运营 (2)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| hr-operations-team | 5 | 招聘/绩效/合规 |
| opc-team | 9 | 一人公司方法论 |

### 产品 (1)
| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| product-strategy-team | 6 | PRD/用户研究/路线图 |

### 其余团队（12，完整索引见 `references/workbuddy-experts/_index.md`）

| 专家团 | Agent数 | 说明 |
|--------|---------|------|
| equity-research | 6 | 深度报告/行业研究/年报点评（**新建·stub**） |
| wealth-management | 6 | 资产配置/基金分析/财务规划（**新建·stub**） |
| pe-vc-investment | 6 | 项目筛选/尽调/Term Sheet/回报建模（**新建·stub**） |
| investment-banking | 6 | IPO/并购/债券/财务建模（**新建·stub**） |
| product-design-suite | 7 | UX全流程11场景28技能（**新建·stub**） |
| alicloud-engineering | 7 | 阿里云运维/Terraform/迁移SOP（**新建·stub**） |
| devtools-engineering | 5 | 多仓Git/AI测试/接口逻辑分析（**新建·stub**） |
| cn-litigation | 6 | 民商事诉讼全生命周期（**新建·stub**） |
| consulting-delivery | 6 | 咨询交付：研究/框架/报告/简报（**新建·stub**） |
| ecommerce-1688 | 6 | 1688选品/运营/数据/转化（**新建·stub**） |
| tech-service-transfer | 6 | 科技服务转化：需求挖掘/成果匹配（**新建·stub**） |
| openspec-doc-team | 4 | 企业级长文档生成（原有） |

> agents 计数口径：实装 **255**（agents/*.md 磁盘实测）；声明 **268**（plugin.json agents[]，2026-08-16 功能自检更新）。


## 安装

### OpenCode
```bash
# 将 team-orchestration 目录复制到 skills 目录
cp -r team-orchestration ~/.config/opencode/skills/
```

### CodeBuddy
```bash
# 作为本地插件加载
codebuddy --plugin-dir /path/to/team-orchestration
```

### DeepSeek Harness / DSH（已适配）
本仓库已适配 DSH（DeepSeek Harness）：作为 **DSH Skill** 安装（**非插件**——本技能是提示词级编排方法论 + 纯 stdlib Python 决策脚本，DSH 已内置全部所需运行时原语：`subagent`/`send_message` 并行与回灌、`ask_user_question` 澄清、`goal`/`todo` 检查点、`pwsh` 执行脚本）。DSH 的 skill 机制扫描 `~/.agents/skills/`（user-agents 根，rank 500，即装即用、零构建、watcher 自动发现），详见 skill 内 `references/dsh-adaptation.md`。

```powershell
# 安装（拷贝到用户级技能根）
$src = "C:\path\to\team-orchestration"
$dst = "$env:USERPROFILE\.agents\skills\team-orchestration"
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse

# 冒烟
python "$dst\scripts\task-decomposer.py" --task "帮我分析宁德时代" --json
python "$dst\scripts\expert-matcher.py" --task "帮我分析宁德时代" --json
```

> **可见性说明**：DSH 官方 frontmatter 字段 `disable-model-invocation: true` 会把技能从模型目录彻底排除（模型看不到、无法加载）——本包已移除该字段，使模型可在技能目录中看到并按其触发词调用。

### 作为独立 Skill 使用
在 AGENTS.md 或 CLAUDE.md 中添加:
```markdown
涉及多 agent 协作/团队分工/并行任务 → 加载 `team-orchestration`
```

## 使用方法

### 快速路径 (使用预设模板)
加载 `team-orchestration` skill 后, 系统自动按 10 个预设模板匹配。

### 专家匹配路径
```bash
# 1. 拆解任务
python3 scripts/task-decomposer.py --task "帮我分析腾讯股票"

# 2. 匹配专家
python3 scripts/expert-matcher.py --domains 08-FinanceInvestment

# 3. 按推荐的专家团 SOP 执行
```

### 自进化
```bash
# Loop 2: 事后回顾
python3 scripts/self-evolution/post-task-evolve.py

# Loop 3: 主动联网增强
python3 scripts/self-evolution/proactive-search.py --experts all
```

## 文件结构

```
team-orchestration/
├── SKILL.md                           # 主入口 (v3.9.0-dsh)
├── references/
│   ├── first-principles.md            # 第一性原理拆解框架
│   ├── expert-matching.md             # 专家匹配评分算法
│   ├── self-evolution-protocol.md     # 三环自进化协议
│   ├── workbuddy-experts/             # 39 个移植专家团
│   │   ├── _index.md                  # 分类索引
│   │   └── {team}/                    # 每个专家团一个目录
│   │       ├── plugin.json            # 元数据 (双语)
│   │       ├── agents/*.md            # Agent 定义 (255个)
│   │       └── self-evolution-log.md  # 自进化日志
│   ├── knowledge/                     # 42 个领域知识文件
│   ├── team-templates/                # 10 个团队模板
│   ├── task-lifecycle.md              # 任务生命周期
│   ├── phase-gates.md                 # 阶段关卡
│   └── communication.md               # Agent 通信模式
├── scripts/
│   ├── task-decomposer.py             # 任务拆解器
│   ├── expert-matcher.py              # 专家匹配器
│   ├── self-evolution/                # 自进化引擎
│   │   ├── post-task-evolve.py        # Loop 2
│   │   ├── proactive-search.py        # Loop 3
│   │   └── knowledge-merger.py        # 知识合并
│   ├── self_heal.py                   # 自我修复
│   ├── health-monitor.py              # 健康监控
│   └── auto-decider.py                # 自动决策
└── README.md
```

## 专家池来源

本 skill 的 40 个专家团**借鉴了包括 WorkBuddy、QoderWork 的专家功能**，并在 DSH 环境完成适配（脚本路径相对化、plugin.json 双语元数据保留、五阶段对抗协议整合）。

## 协议

MIT License

## 自学习数据说明
> **生成时机**：`expert_scores.json` 由 `scripts/trial-court-orchestrator.py` 归档时自动生成，或执行 `python scripts/trial-court-orchestrator.py init-learning` 一次性初始化；history 权重 0.10 冷启动时为 0，不影响匹配。
