# Team Orchestration Skill — 多智能体对抗编排引擎

> 专家池借鉴了包括 WorkBuddy、QoderWork 的专家功能

## 概述

这是一个 DSH（DeepSeek Harness）Skill，提供**多智能体对抗编排**能力——核心是**五阶段对抗协议（二审终审制）**：对复杂议题组织多视角专家子代理，经举证 → 质证 → 一审 → 二审终审的对抗流程收敛出高质量结论。

```
任务 → 立案(复杂度/分工/并发判定) → 并行举证(N子代理) → 质证(回灌修正)
     → 一审(裁决+回灌修订1轮) → 二审终审(不回灌) → 交付+归档
```

## 核心特性（v3.9.0-dsh）

### ⚖️ 五阶段对抗协议（二审终审制）
立案（5W2H 澄清 + 争点拆解）→ 并行举证（2-6 子代理独立取证）→ 质证（回灌他方产物逐条修正，默认 1 轮、最多 2 轮）→ 一审（裁决 + 回灌修订固定 1 轮）→ **二审终审**（终局裁断，禁止引入新论点）。含**终审前置门禁**（子代理回声收齐才可终审）、BATNA 降级、独立复审（§7.3，优先调度通才批判团）。

### 🧭 聚合域路由
40 专家团归入 **8 大聚合域**（投资分析/资本服务/法律服务/内容全链路/营销增长/工程保障/数据智能/产品设计），定域后**跨团队按需组队**（agent 超网思想：257 agents 组件池按任务组合激活，目录物理保留零破坏）。脚本级支持：`expert-matcher.py --domain 投资分析 --task "..."` 限域召回。

### 📦 任务级 Skill 封装（Agent Skills 思想）
5 大高频任务封装为可复用 skill（触发词 + 团队组合 + 流程 + 输出契约）：**投资分析 / 法律咨询 / 内容生产 / 技术审查 / 深度研究**（`references/skills-pack.md`）——比工具高一层、比完整 agent 低一层的任务能力单元。

### 🧠 通才批判团（general-critics）
`general-critic`（对抗审查主理人：假设检验/偏见检测/五维 rubric）+ `devil-advocate`（魔鬼代言人：最强反论/极端场景/共识压力测试）——平衡垂直专家的盲点，服务于质证与终审质量门禁。

### 🎛 动态派数机制
派数不再拍脑袋：`task-decomposer --concurrency N` 输出 `suggested_subagents{value, range, rationale}`——**N = 复杂度基数 × 分工加成 × 模型并发截断 × 预算硬约束 C(N,q)=N×(2+q)**。L1 直行 / L2 直行信号 / L3+ clamp[2, min(并发, 档位)]；推荐值非强制，main 可覆写留痕。

### 🗄 数据治理
- **并发参考数据保鲜**（`concurrency-data.json`）：模型并发查官方文档（DeepSeek v4-flash=2500，账号粒度），**14 天保鲜期**，过期先派子代理更新，失败用 `max_spawned+1` 渐进试探；每次实际派出强制记录（B 举证 spawn 后 `record --n N`）
- **数据来源查证纪律**（`references/data-provenance.md` + SKILL.md §9.5）：能查官方查官方 → 能再生成就保鲜 → 查不到就如实标注，禁止把推断值当事实

### 🛡 质量防线
- **40/40 测试全绿**（run_smoke：脚本冒烟/引用完整性/编码健康/专家池一致性/动态派数/并发数据）
- **编码门禁**：全包 UTF-8 严格扫描 + C5.2 `?` 替字检测（46 个历史损坏文件根治）
- 双编码回归（GBK 控制台 + UTF-8）

## 专家池（40 团队 / 257 agents）

### 8 大聚合域

| 聚合域 | 团队 | 触发场景 |
|---|---|---|
| 投资分析 | investment-masters + trading-agent + stock-partner + a-share-analysis + equity-research | 股票/估值/多空/买入建议 |
| 资本服务 | pe-vc-investment + investment-banking + wealth-management | 融资/IPO/家族办公室 |
| 法律服务 | chatlaw-team + cn-litigation + enterprise-legal-team + tax-compliance-team | 合同/诉讼/合规/税务 |
| 内容全链路 | ai-content-creator + content-distribution + content-monetization + promo-creator | 视频/文案/分发/变现 |
| 营销增长 | marketing-campaign + sales-battle + seo-content + social-engagement | 投放/线索/SEO/社媒 |
| 工程保障 | engineering-assurance + gstack + devtools-engineering + rum-fullstack + alicloud-engineering + software-company | 架构评审/代码审查/QA/云 |
| 数据智能 | ai-data-copilot + huashu-data-pro | SQL/数据分析 |
| 产品设计 | product-strategy + design-engine + product-design-suite | PRD/UX/设计系统 |

### 通用对抗层
- `gpt-researcher-team`（深度研究兜底）
- `general-critics`（通才批判团：对抗审查 + 魔鬼代言人）

> 完整索引见 `references/workbuddy-experts/_index.md`（40 团队 257 agents 磁盘实测 / 273 声明）。

## 安装（DSH）

```powershell
# 拷贝到用户级技能根（DSH skill 机制扫描 ~/.agents/skills/，即装即用、零构建）
$src = "C:\path\to\team-orchestration"
$dst = "$env:USERPROFILE\.agents\skills\team-orchestration"
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse

# 冒烟
python "$dst\scripts\task-decomposer.py" --task "帮我分析宁德时代" --json
python "$dst\scripts\expert-matcher.py" --domain 投资分析 --task "帮我分析宁德时代" --json
```

> 本技能为**提示词级编排方法论 + 纯 stdlib Python 决策脚本**，DSH 已内置全部运行时原语（`subagent`/`send_message` 并行与回灌、`ask_user_question` 澄清、`goal`/`todo` 检查点、`pwsh` 执行脚本），详见 `references/dsh-adaptation.md`。

## 快速上手

```bash
# 1. 立案：拆解任务 + 动态派数（复杂度×分工×并发）
python scripts/task-decomposer.py --task "帮我分析宁德时代的基本面" --concurrency 6 --json
#    → complexity: L3-复杂, suggested_subagents: {value:4, range:[2,6], rationale:...}

# 2. 限域召回专家（聚合域路由）
python scripts/expert-matcher.py --domain 投资分析 --task "帮我分析宁德时代" --top-k 3 --json

# 3. 并发参考数据检查（14 天保鲜，过期自动提示更新）
python scripts/concurrency_check.py check

# 4. 按五阶段协议组织对抗（见 SKILL.md §3）
```

## 测试与验证

```bash
python tests/run_smoke.py              # 40/40 全量冒烟
python tests/check_references.py       # 引用完整性（零死链）
python tests/test_file_health.py       # UTF-8 健康 + C5.2 ? 替字门禁
python scripts/check_team_consistency.py   # 专家池声明==资产一致
python scripts/check_agent_completeness.py # agent 模板完整性
```

## 文件结构

```
team-orchestration/
├── SKILL.md                           # 主契约 (v3.9.0-dsh)
├── references/
│   ├── skills-pack.md                 # 任务级 Skill 封装（5 大 skill）
│   ├── data-provenance.md             # 数据来源可靠性矩阵（查证纪律）
│   ├── concurrency-data.json          # 模型并发参考数据（14 天保鲜）
│   ├── trial-court-protocol.md        # 审判庭五阶段详细规范
│   ├── dsh-adaptation.md              # DSH 适配指南
│   ├── workbuddy-experts/             # 40 个移植专家团
│   │   ├── _index.md                  # 分类索引（8 聚合域 + 通用层）
│   │   ├── general-critics/           # 通才批判团（v3.9 自建）
│   │   └── {team}/                    # 每团：plugin.json + agents/*.md
│   ├── knowledge/                     # 42 个领域知识文件
│   └── team-templates/                # 团队模板
├── scripts/                           # 19 个 .py（顶层 16 + self-evolution 3）
│   ├── task-decomposer.py             # 拆解 + 动态派数（--concurrency）
│   ├── expert-matcher.py              # 聚合域路由匹配（--domain）
│   ├── concurrency_check.py           # 并发参考数据检查（check/record/update）
│   ├── trial-court-orchestrator.py    # 案卷/归档/自学习后端
│   └── self-evolution/                # 自进化三件套
├── tests/                             # 40 个测试用例
└── README.md
```

## 专家池来源

本 skill 的 40 个专家团**借鉴了包括 WorkBuddy、QoderWork 的专家功能**，并在 DSH 环境完成适配（脚本路径相对化、plugin.json 双语元数据保留、五阶段对抗协议整合）。

## 协议

MIT License
