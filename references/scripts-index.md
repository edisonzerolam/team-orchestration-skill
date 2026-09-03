# 脚本索引与数据查证（SKILL.md §9-§9.5 外移 · TC-20260816-9 瘦身）

> 由 SKILL.md 正文外移，按需读取。跑脚本前查本节。

## 9 可选辅助脚本（非主流程必须）

以下脚本可辅助决策但**不阻塞**主流程，main 可跳过直接思考：
> scripts/ 下共 **21 个 .py（顶层 18 + self-evolution/ 下 3）**。审判庭后端（trial-court-orchestrator / asset-resolver / cross-validator）+ 前端（task-decomposer/expert-matcher/dispatch-planner）互补，按需运行。
> **案卷隔离（v3.10.3 · TC-20260816-9）**：`deliverables/trial/` 为真实任务数据（含路径/内容），**禁止进入带 remote 的 git 仓库**——归档位置默认工作区根 `deliverables/trial/`，若工作区 git 仓库有 remote，用 TRIAL_BASE 环境变量指向仓库外目录（如 `~/.dsh/trial-archive`）。

**前端（决策参考）**：
- `python scripts/task-decomposer.py --task "..." --json`（复杂度参考）
- `python scripts/expert-matcher.py --task "..." --json`（专家团召回参考）
- `python scripts/dispatch-planner.py --task "..." --top-k 2`（派工方案草稿）

**审判庭后端（案卷/归档/自学习，现行）**：
- `python scripts/trial-court-orchestrator.py docket ...`（案卷/归档/自学习后端）
- `python scripts/asset-resolver.py --snapshot`（资产快照生成）；`--task "<任务>"`（技能触发词路由召回，v3.10 · TC-20260816-7）
- **多机技能注册表（v3.10.1 · TC-20260816-7）**：`python scripts/skill-registry-agent.py`（远程技能枚举——部署到目标机运行，输出本机技能 JSON）；主控侧 `asset-resolver.py --registry-merge <json> --host-alias <别名>`（合并进 `references/skill-registry.json`）/ `--registry-check`（保鲜检查，7 天）/ `--registry-list`（列出远程技能）。**定期更新**：立案 `--registry-check` 驱动刷新；也可在 DSH GUI 注册轮询任务（如每周日 3 点：ssh_exec 各目标机跑 skill-registry-agent → 取回合并）实现无人值守
- `python scripts/cross-validator.py ...`（举证交叉验证，接入 A3 evidence 校验）

**激活资产（v3.5 增强 · P0-3 索引补齐）**：
- `python scripts/token_budget.py --limits '{"举证":12000,...}'`（分阶段 token 预算，**WARN 80% / BLOCK 100%**，接入 §3 各阶段入口）
- `python scripts/checkpoint_manager.py --root <检查点目录> --action save|load|next|plan ...`（步骤检查点/断点续传，配合 §3 检查点协议）
- `python scripts/self_heal.py`（错误分类与恢复，已集成 orchestrator `self-heal` 子命令）
- `python scripts/auto-decider.py`（错误自动决策 retry/skip/abort，已集成 orchestrator `auto-decide` 子命令）
- `python scripts/cycle_detector.py --edges edges.json`（spawn 调用环检测，阻断 A→B→A→B 死循环；orchestrator 内部已接线）

**其余脚本**（兜底索引，均可在 scripts/ 目录内直接查看与运行）：`concurrency_check.py`（模型并发参考数据检查：fresh/stale + max_spawned+1 试探，立案时用）、`health-monitor.py`（运行态健康监控）、`self_learning.py`（自学习统计）、`check_team_consistency.py` / `check_agent_completeness.py`（v3.3 校验）、`self-evolution/knowledge-merger.py` / `post-task-evolve.py` / `proactive-search.py`（自进化三件套）。完整调用方式见 `references/zcode-adaptation.md` §2。

## 9.5 外部数据查证纪律（v3.9 · TC-20260816-6 补强）

技能依赖的记录与外部数据，按来源分层管理（详见 `references/data-provenance.md`）：

1. **自身执行记录**（docket-*/trial-count/expert-scores/自学习）：来源=本技能运行产物，可靠性高；查证=案卷重放对照，无需外部验证。
2. **官方文档来源**（concurrency-data.json）：模型并发查模型提供方官网 rate limit 页（如 DeepSeek: api-docs.deepseek.com/quick_start/rate_limit/）；**保鲜期 14 天**，过期先派子代理更新，失败用 max_spawned+1 试探（见 §3A 立案步骤 3）。
3. **本机扫描数据**（last-asset-snapshot.json / asset-issue-map.md）：资产快照，**即过期即失真**——使用时核对 `snapshot_at`，>30 天提示重新 `--snapshot` 再生成。
4. **市场导入数据**（workbuddy-experts/）：provenance 字段（`_source`/`_enhancedWith`）保留来源；上游损坏不可复核时**如实标注**，不虚构对照。
5. **推断/补全数据**（knowledge/*.md 中修复推断值）：分两类——可查证类（法条/税率/行业标准）经 web_search 核实后使用；**不可查证类（原始字节丢失的上下文推断）必须标注"推断值"**，使用时不作为权威依据。

> 原则：**能查官方查官方，能再生成就保鲜，查不到就如实标注**——禁止把推断值当事实使用。
