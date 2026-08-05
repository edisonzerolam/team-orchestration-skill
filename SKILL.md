---
name: team-orchestration
version: 3.2.0
disable-model-invocation: true
description: "多智能体团队编排引擎 — 三阶段对抗协议 + A3契约 + 降级路径 + 视觉识别路由(实测验证) + 后台送达契约。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags: [orchestration, team, multi-agent, trial-court, vision]
---

# Team Orchestration v3.2.0

## 1 触发条件

满足**任一**即走三阶段对抗协议：① >1 子代理 ② main+子代理协作 ③ 多角度执行。
不满足 → 直行（单 agent）。直行中复杂度升级 → 自动切换。

## 2 规模门 + 降级路径

- **L1-L2**（单维度/低争议/子任务≤3）：直行，单 agent + 自我批判。
- **L3+**（多维/高争议/跨领域）：三阶段对抗协议。
- **降级**：若无法确定合适的 2+ 差异化视角，降为单 agent + 自我批判（不硬凑团队）。
- **升级**：L2 涉及 ≥3 领域 → 升为 L3。

> **OpenCode 执行环境**：子代理通过 `task(subagent_type="general")` 拉起（可选 `debug-expert`/`code-reviewer` 等专长子代理），同一消息多个 task 调用即并行。专家人设读取 `references/workbuddy-experts/<团队>/agents/*.md` 注入 prompt。详见 `references/opencode-adaptation.md`。

## 3 三阶段流程

```
立案(main直思) ──► 并行举证(N子代理) ──► 质证+终审(回灌→裁决)
```

> **与审判庭协议的关系**：三阶段是审判庭四阶段（Phase A 立案/B 举证/C 质证/D 终审）的**精简视图**；复杂议题按 `references/trial-court-protocol.md` 展开执行（含案卷归档、自学习 S1/S2、终审六段式）。

**A 立案**（main 内存中完成，无需脚本）：
1. 5W2H 澄清（模糊则追问 ≤2 轮）
2. 拆 1 核心争点 + 2-5 子争点
3. 选角色（见 §6）+ 为每角色选定专业视角
4. 从上下文已有技能/MCP/连接器中选取可用资产

**B 并行举证**：同一消息并行拉起 2-6 个 Agent 子代理，每个 prompt 按 §4 四要素模板。子代理独立举证，可联网/调 MCP/用技能。

**C 质证+终审**：
1. 汇总 B 产物 → 回灌给每个子代理 → 逐条质证他方 → 修正己方（**默认 1 轮**；分歧>2 追加 1 轮，最多 2 轮）
2. main 逐条裁断：采信/部分采信/排除（每项说明理由）
3. 产出终审意见书 → 交付用户
4. 归档（异步，不阻塞交付）

## 4 子代理 Prompt 四要素 + A3 契约

每个子代理 prompt 必须包含：
1. **目标**：你是「{角色名}」，专业：{领域}，立场：{正/反/中立}。争点：{具体子问题}。
2. **格式**：严格输出 A3 JSON — `{"role":"...","artifacts":{"conclusions":[],"evidence":[],"risks":[],"actions":[]},"confidence":0.0,"uncertainties":[]}`
3. **工具**：可用资产列表（从 A 阶段选取注入）。
4. **边界**：聚焦你的视角，不越界；存疑标注"不确定"；≤400 字。

### 4.1 子代理模型选择（视觉识别路由）

> **平台现状（OpenCode 2026-08-06 适配）**：
> 1. **main 直读已验证可行**：OpenCode main agent 用 Read 工具直接读图（若当前模型支持视觉）；否则委托 `task(subagent_type="mini-vision")` 子代理读图（全局规则「图片委托规则」）。
> 2. **子代理视觉能力**：OpenCode 子代理模型能力取决于各自配置；`mini-vision`（MiMo V2.5）为专用视觉子代理，读图返回结构化 JSON。
> 3. 视觉任务不依赖具体模型 ID 硬编码（OpenCode 无模型清单文件概念），按 `task` 工具可用子代理类型路由。

- **视觉任务路由（已验证）**：**优先 main 直接读取**（当前模型支持视觉时不产生子代理成本）。
- **子代理必须看图**：main 先读图提取信息，再将文本结论喂给子代理处理（推荐，已验证可行）；或委托 `mini-vision` 子代理结构化读图。
- **若视觉信息与文字冲突**：以 main 直读的直接观察为准，裁决注明依据。
- **模型可用性核对**：OpenCode 下检查 `task` 工具可用子代理类型（`mini-vision` 为视觉子代理）。

### 4.2 后台子代理送达契约 + 看门狗（OpenCode 适配）

> **OpenCode 差异**：WorkBuddy 的 `teams/<team>/inboxes/` 收件箱机制在 OpenCode 下不存在。OpenCode 的 `task` 工具为同步调用：子代理完成后直接返回结果给 main，不存在实时消息流或 "completed" 通知。多子代理并行 = 同一消息多次 `task` 调用。

- **产物收集 = 事实来源**：OpenCode 下子代理产物即 `task` 调用返回值，无需收件箱。
- **并行契约**：每个子代理 prompt 末尾**必须**写明"返回结构化 A3 JSON 结果"。
- **看门狗**：OpenCode 下无后台 worker；如需超时控制，由 main 自行把握 task 数量与轮次（建议单轮 ≤6 个子代理）。

## 5 合并策略

- 封闭题（是/否、选型）→ 投票制：多数采信 + 少数留痕。
- 开放题（方案、策略）→ 辩论制：main 综合采信，逐条说明理由。

## 6 角色分配

| 子代理数 | 角色 | 适用 |
|---------|------|------|
| 2 | 正/反 | 简单二分 |
| 3 | 正/反/中立 | 权衡问题（默认） |
| 4-6 | 多学科专家团 | 跨领域复杂议题 |

专家人设库：`references/workbuddy-experts/`（39 团队 199 agents，按需读取 agents/*.md 注入 prompt；11 个新建团队为 stub 待补充）。

## 7 质量门禁

- 终审禁止引入新论点（未在举证/质证出现不可采信）
- 可信度 = 最薄弱证据的可信度
- 每轮质证标注「变与不变」
- 主理人铁律：禁止代写 / 禁止跳阶段 / 禁止成员直连

## 7.1 终审意见书最小契约（v3.1）

终审产出即**终审意见书**，章节结构：
1. 议题与争点（核心 1 + 子 2-5）
2. 各方举证摘要（每方 A3 JSON 的 `artifacts.conclusions` 要点）
3. 质证记录（轮数 + 每轮「变与不变」）
4. 裁决理由（逐条：采信 / 部分采信 / 排除 + 理由；禁止引入新论点）
5. 最终结论（含可信度 = 最薄弱证据的可信度）

**A3 JSON 字段映射**：`role`→举证方；`artifacts.conclusions`→争点结论；`artifacts.evidence`→依据；`confidence`→可信度；`uncertainties`→存疑项。

**归档**（异步，不阻塞交付）：`deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（docket_id 格式 TC-YYYYMMDD-N）。

## 8 参考文件（按需读取）

| 文件 | 用途 |
|------|------|
| `references/trial-court.md` | 完整审判庭协议细节（现行补充协议） |
| `references/trial-court-protocol.md` | 审判庭四阶段详细执行规范（案卷归档/自学习S1/S2/终审六段式） |
| `references/trial-court-architecture.md` | 审判庭架构（v2 历史，内容与上重复，存档参考） |
| `references/workbuddy-experts/_index.md` | 39 专家团索引 |
| `references/workbuddy-adaptation.md` | WorkBuddy 专家/技能/MCP 资产体系（OpenCode 下作专家池索引参考） |
| `references/opencode-adaptation.md` | **OpenCode 适配指南（脚本路径、子代理映射、平台差异）** |
| `references/cross-validation.md` | 交叉验证规则 |
| `references/test-workflow.md` | **改本技能逻辑/契约/脚本前必先读，作为回归门禁（见 §8 下触发守则）** |

**归档路径**（OpenCode）：`skill 目录/deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（docket_id 格式 TC-YYYYMMDD-N）。

## 8.1 加载决策（分域路由）· Phase 0

> **守卫（三行，必读）**：① 非白名单团队仍可**追加读取**（懒加载，不阻断）；② 冲突时以 `expert-matcher` 检索结果 + lead 判断为准；③ 通用对抗兜底（`gpt-researcher-team`）**始终可选**。
> **定位**：本文是**文档级判断纪律工具**（省 lead 定域判断成本 + 有界读取），**不承诺 token 百分比节省**；"默认跳过 ≠ 禁止读取"。

**定域流程**：立案用下方触发词 → 定 `domain` → 加载该域 T1 团队头寸 + knowledge 最小集 → 进队 agent 人设按需（T2 惰性，`read_agent_md` 已内置）。
**兜底（表外/跨界/新团队）**：触发词未命中静态表时，交语义判断 —— `python scripts/expert-matcher.py --task "<任务原文>" --top-k 4 --json`，按其得分高的团队为准；仍无高分(score<0.25)则回退通用对抗（gpt-researcher-team）。优先级：静态表(快) → LLM语义(matcher) → 通用兜底。冲突以 matcher 语义得分为准。

| 任务域 | 触发词例 | T1 expert 团队（完整目录名） | T1 knowledge（最小） | 默认跳过（启发式） |
|--------|---------|---------------------------|---------------------|------------------|
| 投资/金融 | 股票/基金/A股/港股/PE/VC/估值 | investment-masters-team, trading-agent, stock-partner-team, a-share-analysis, equity-research, wealth-management, pe-vc-investment, investment-banking | stock-analyst, hk-stock-analysis, macro-analyst, valuation-expert, money-flow-tracker | content / marketing / product / engineering / legal |
| 法律/财税 | 合同/诉讼/合规/知产/税务/仲裁 | cn-litigation, chatlaw-team, enterprise-legal-team, tax-compliance-team | contract-reviewer, legal-researcher, litigation-strategist, ip-specialist, privacy, regulatory, tax-compliance, precedent | investment / content / product / engineering |
| 内容创作 | 视频/脚本/文案/视觉/宣传/分发 | ai-content-creator-team, content-distribution-team, content-monetization-team, promo-creator-team | content-director, scriptwriter, video-editor, visual-artist, synthesis-writer | legal / investment / engineering |
| 营销增长 | 营销/SEO/销售/社媒/增长 | marketing-campaign-team, sales-battle-team, seo-content-team, social-engagement-team | prompt-patterns, platform-analyst | legal / investment / engineering |
| 产品设计 | PRD/UX/竞品/设计系统 | product-strategy-team, design-engine, product-design-suite | prompt-patterns | marketing / legal / investment |
| 技术工程 | 开发/架构/云/测试/审查 | software-company, engineering-assurance-team, gstack, rum-fullstack-team, alicloud-engineering, devtools-engineering | platform-adapter, platform-analyst, ai-data-copilot | investment / legal / content |
| **通用多agent对抗** | 无法归类 / 跨 3+ 域 L3 | gpt-researcher-team + 通用 agent 池 | 不预载，仅 T0 | 无（降级不硬选） |

> 完整版与命名对照见 `references/expert-matching.md`「分域加载决策表（Phase 0）」。

## 9 可选辅助脚本（非主流程必须）

以下脚本可辅助决策但**不阻塞**主流程，main 可跳过直接思考：
> 三脚本（trial-court-orchestrator / asset-resolver / cross-validator）为审判庭**后端实现**（案卷/归档/自学习），与前端脚本（task-decomposer/expert-matcher/dispatch-planner）互补，按需运行。
- `python scripts/task-decomposer.py --task "..." --json`（复杂度参考）
- `python scripts/expert-matcher.py --task "..." --json`（专家团召回参考）
- `python scripts/dispatch-planner.py --task "..." --top-k 2`（派工方案草稿）
- `python scripts/trial-court-orchestrator.py docket ...`（案卷/归档/自学习后端，现行）
- `python scripts/asset-resolver.py --snapshot`（资产快照生成，现行）
- `python scripts/cross-validator.py ...`（举证交叉验证，接入 A3 evidence 校验，现行）
