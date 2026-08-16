# WorkBuddy 适配指南（压缩版 · 历史移植参考）

> **superseded（v3.8 · TC-20260816-3 清理）**：本文件为 WorkBuddy 环境移植历史参考。现行事实源：
> - 专家池索引（39 团队完整映射表）：`references/workbuddy-experts/_index.md`
> - DSH 环境适配：`references/dsh-adaptation.md`
> 专家团人设仍按需读取 `references/workbuddy-experts/<团队>/`（plugin.json + agents/*.md）。

## 来源（一行）

本 skill 的 39 个专家团移植自 WorkBuddy (Tencent CodeBuddy) Expert Marketplace（28 原生 + QoderWork 套件 11 新建），脚本路径已改为相对自身，与安装位置无关。

## 两种执行模式（核心语义）

匹配到团队后按场景二选一：

- **Mode A — 原生专家/专家团调用（推荐深度任务）**：主理人完成拆解匹配后，建议用户打开 WorkBuddy「专家中心」对应原生专家团执行（自带工具/人设/SOP）。标准话术：任务建议交给原生专家团「<显示名>（<插件名>）」，请在专家中心搜索打开。
- **Mode B — 当前对话内就地模拟**：读 `references/workbuddy-experts/<团队>/plugin.json` 拿 members/leadAgent → 读主理人 `.md` 了解 SOP → 用 Agent 子智能体起 2~4 个最相关成员（prompt 含角色/专业/人设/分工/输出要求）→ 收齐交叉验证后交付。不要用 `expertType` 启动不存在的内部工具；不拉满全部 agent（奥卡姆剃刀）。

## 脚本运行（命令锚）

脚本路径已相对自身，直接运行（托管 Python 或系统 python 均可）：

```bash
# 任务拆解
python scripts/task-decomposer.py --task "帮我分析宁德时代的基本面和估值" --json

# 专家匹配（自动调用拆解）/ 按领域直接匹配
python scripts/expert-matcher.py --task "帮我分析宁德时代的基本面和估值" --json
python scripts/expert-matcher.py --domains 08-FinanceInvestment --top-k 3

# Mode B 派工方案生成（产物：last_dispatch_plan.md + .json）
python scripts/dispatch-planner.py --task "帮我分析宁德时代的基本面和估值，并给买入建议" --top-k 2
```

## 主理人工作流（压缩）

`目标明确(5W2H≤2轮) → 拆解(task-decomposer) → 匹配(expert-matcher) → 选模式(L1/L2 Mode A；L3/L4 Mode A 优先或 Mode B) → 执行 → 交叉验证 → 审核(🟢/🟡/🔴) → 交付+自进化(self-evolution-log.md)`。主理人铁律：禁止替用户做不可逆决策、禁止跳阶段、成员产出须经主理人汇总。

## 自进化（Loop 1/2/3）

- Loop 1 秒级：执行中反思，追加 `references/workbuddy-experts/<团队>/self-evolution-log.md`
- Loop 2 分钟级：`python scripts/self-evolution/post-task-evolve.py`
- Loop 3 小时级：`python scripts/self-evolution/proactive-search.py --experts all`

## 与审判庭核心机制的集成

| 适配章节 | 被审判庭哪层使用 |
|---------|----------------|
| Mode A/B | Phase B 举证阶段的资产注入（子代理 prompt 中推荐） |
| 脚本运行 | 审判庭脚本扩展（trial-court-orchestrator.py + asset-resolver.py） |
| 自进化 | 审判庭自学习层 S2/S3 |

---
*本适配由 WorkBuddy 安装工程生成（v2.5.0，审判庭核心机制版），2026-08-16 压缩为历史参考。*
