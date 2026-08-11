---
name: team-orchestration
version: 3.4.0-zcode
disable-model-invocation: true
description: "多智能体团队编排引擎 — 五阶段对抗协议(二审终审制) + A3契约 + 降级路径 + 视觉识别路由(实测验证) + 后台送达契约。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags: [orchestration, team, multi-agent, trial-court, two-instance, vision]
---

# Team Orchestration v3.4.0-zcode

## 1 触发条件

满足**任一**即走五阶段对抗协议（二审终审制）：① >1 子代理 ② main+子代理协作 ③ 多角度执行。
不满足 → 直行（单 agent）。直行中复杂度升级 → 自动切换。

## 2 规模门 + 降级路径

- **L1-L2**（单维度/低争议/子任务≤3）：直行，单 agent + 自我批判。
- **L3+**（多维/高争议/跨领域）：五阶段对抗协议（二审终审制）。
- **降级**：若无法确定合适的 2+ 差异化视角，降为单 agent + 自我批判（不硬凑团队）。
- **升级**：L2 涉及 ≥3 领域 → 升为 L3。

## 3 五阶段流程（二审终审制）

```
立案(main直思) ──► 并行举证(N子代理) ──► 质证(回灌→修正) ──► 一审(裁决→回灌修订1轮) ──► 二审终审(不回灌)
```

> **与审判庭协议的关系**：五阶段是审判庭完整协议（Phase A 立案/B 举证/C 质证/D 一审/E 二审终审）的**精简视图**；复杂议题按 `references/trial-court-protocol.md` 展开执行（含案卷归档、自学习 S1/S2、终审七段式）。

**A 立案**（main 内存中完成，无需脚本）：
1. 5W2H 澄清（模糊则追问 ≤2 轮）
2. 拆 1 核心争点 + 2-5 子争点
3. 选角色（见 §6）+ 为每角色选定专业视角
4. 从上下文已有技能/MCP/连接器中选取可用资产

**B 并行举证**：同一消息并行拉起 2-6 个 Agent 子代理，每个 prompt 按 §4 四要素模板。子代理独立举证，可联网/调 MCP/用技能。

**C 质证**：
1. 汇总 B 产物 → 回灌给每个子代理 → 逐条质证他方 → 修正己方（**默认 1 轮**；分歧>2 追加 1 轮，最多 2 轮）
2. 分歧收敛判定（分歧≤1 即进入一审）→ 产物落盘 02-质证/

**D 一审（裁决 + 回灌修订）**：
1. main 逐条裁断：采信/部分采信/排除（每项说明理由）→ 产出《一审判决书》（**中间产物**，落盘 03-一审/first-instance-verdict.md，流程中展示摘要，不单独交付）
2. 把《一审判决书》+ 各方最新产物回灌给每个子代理 → 逐条回应判决（服判/异议+理由）+ 立场再修订（**固定 1 轮**，不因收敛提前、不追加第二轮）→ P{i}(C) 落盘 04-回灌修订/

**E 二审终审**：
1. 汇总一审修订产物 → main 终局裁断：采信/部分采信/排除（每项说明理由，禁止引入新论点）
2. 产出《终审意见书》（**二审终审，不再回灌**）→ 交付用户
3. 归档（异步，不阻塞交付）

## 4 子代理 Prompt 四要素 + A3 契约

每个子代理 prompt 必须包含：
1. **目标**：你是「{角色名}」，专业：{领域}，立场：{正/反/中立}。争点：{具体子问题}。
2. **格式**：严格输出 A3 JSON — `{"role":"...","artifacts":{"conclusions":[],"evidence":[],"risks":[],"actions":[]},"confidence":0.0,"uncertainties":[]}`
3. **工具**：可用资产列表（从 A 阶段选取注入）。
4. **边界**：聚焦你的视角，不越界；存疑标注"不确定"；≤400 字。

### 4.3 交接与收敛契约（v3.3 增强 · TC-20260809）

> 处理大量跨 agent 交接时降低上下文污染、收敛无界重试。核心：**交接只传摘要、验收只卡 schema、收敛有上限**。

- **C1 结构化交接摘要**：子代理回传/交接时，只传结构化 A3 摘要（conclusions + evidence + risks + actions）。evidence 须携带 **artifact 指针**（来源路径/引用名），质证阶段按指针取原始论述，**不传全量对话**，防上下文随对抗轮次恶化。
- **C2 重试上限 + 达标阈值**：质证默认 1 轮、分歧 >2 追加 1 轮、**最多 2 轮**；一审回灌修订**固定 1 轮**（二审终审制：不因收敛提前、不追加第二轮，修订后直接进入二审终审）。单个子代理产出**因相同原因不达标**时最多重试 2 次即收敛（固定上限，防 token 失控）；不同原因可继续，但累计 >2 次仍收敛并标记"低可信度"。
- **C3 输出 schema 级检查**：每子代理输出的 A3 须过字段完整性校验——**硬键** `role / artifacts{conclusions,evidence,risks,actions} / confidence / uncertainties` 缺失即判不达标触发 C2 重试；**软键**（confidence 数值偏离、uncertainties 为空等）仅 **warning 不重试**，避免主观字段假阳性。校验宿主=接入 C2 重试闭环（A3 产出 → 校验 → 不达标重试），复用 `scripts/cross-validator.py`。单子代理累计消耗超 token 阈值即终止并返回部分结果。

### 4.1 子代理模型选择（视觉识别路由）

> **平台现状（ZCode 2026-08-09 三路运行时验证——视觉路由当前不可用）**：
> 1. **main 直读**：✗ 失败 — `Media omitted ... model does not support image input`（deepseek-v4-flash text-only）。
> 2. **mini-vision 子代理**：✗ `Agent type 'mini-vision' not found. Available agents: general-purpose, Explore` — **ZCode 运行时不消费 `~/.config/opencode/agents/*.md` 为 subagent_type**，仅暴露 general-purpose/Explore 两种内置类型。
> 3. **general-purpose 子代理读图**：✗ 失败 — 子代理继承 main 的 text-only 模型。且 `~/.zcode/v2/config.json` 模型池全表 text-only（mimo-v2.5 亦声明 text-only），**当前无任何视觉模型**。

- **视觉任务路由（ZCode 实测）**：**三路不可用**，视觉任务当前只能走外部通道：
  1. **外部 OCR/视觉通道转文本**（当前唯一可行路径）：图片先经外部 OCR 转结构化文本，再喂子代理处理。
  2. **切换视觉模型**：若 ZCode 引入带视觉的模型（注册表 modalities 支持 image），main 直读即可。
  3. **注册用户级 agents**：调研 ZCode「Settings → Subagents」是否可将 agents/*.md 注册为可调用类型。
- **兜底约定**：子代理 prompt 不传图片路径，只传「图片的文本化内容」；无法文本化时向用户说明。
- **若视觉信息与文字冲突**：以直接观察/主证据为准，裁决注明依据。

### 4.2 后台子代理送达契约 + 看门狗（ZCode 2026-08-09 适配）

> **ZCode 实测口径**：无收件箱机制。子代理产物 = `task` 调用返回值（同步）或后台任务完成通知 + `agent_*/task.output` 产物文件；主环境 SendMessage(to: agentId) 可与已 spawn agent 通信（agent 间直连受限）。

- **产物收集 = 事实来源**：判定 worker 是否完成，以 `task` 返回结果 / Agent 工具 `run_in_background` 完成通知为准；后台任务可用 `task_id` 续接同一子会话。
- **并行契约**：同一消息多次 `task` 调用即并行（2-6 个）；每个子代理 prompt 末尾**必须**写明"返回结构化 A3 JSON 结果"。
- **看门狗**：spawn 每个后台 worker 后设超时（建议 5 分钟），超时主动用 `TaskOutput`/读产物文件拉取其产出，绝不无限期等待。
- **收尾兜底**：并行 spawn 后、进入质证前，强制核对全部 task 返回值已收齐再继续；不因"通知未弹出"就停在等待态。
- **禁止轮询**：后台任务完成会收到通知，不要 sleep/轮询等待。

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

- 二审终审禁止引入新论点（未在举证/质证/一审回灌修订出现不可采信）
- 可信度 = 最薄弱证据的可信度
- 每轮质证与一审回灌修订标注「变与不变」
- 主理人铁律：禁止代写 / 禁止跳阶段 / 禁止成员直连

## 7.1 终审意见书最小契约（v3.1 · 二审终审制）

终审产出即**终审意见书**（二审终局文书；一审判决书为中间产物，落盘 `03-一审/first-instance-verdict.md`，结构见 `references/trial-court-protocol.md` §6.2），章节结构：
1. 议题与争点（核心 1 + 子 2-5）
2. 各方举证摘要（每方 A3 JSON 的 `artifacts.conclusions` 要点）
3. 质证与一审修订记录（质证轮数 + 回灌修订轮 + 每轮「变与不变」）
4. 裁决理由（逐条：采信 / 部分采信 / 排除 + 理由；二审禁止引入新论点）
5. 最终结论（含可信度 = 最薄弱证据的可信度；标注"二审终审，不再回灌"）

**A3 JSON 字段映射**：`role`→举证方；`artifacts.conclusions`→争点结论；`artifacts.evidence`→依据；`confidence`→可信度；`uncertainties`→存疑项。

**归档**（异步，不阻塞交付）：**工作区根** `deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（docket_id 格式 TC-YYYYMMDD-N；TRIAL_BASE 支持环境变量覆盖，见 `references/zcode-adaptation.md` §5）。

## 8 参考文件（按需读取）

| 文件 | 用途 |
|------|------|
| `references/trial-court.md` | 完整审判庭协议细节（现行补充协议） |
| `references/trial-court-protocol.md` | 审判庭五阶段详细执行规范（二审终审制：一审裁决/回灌修订/二审终审，含案卷归档/自学习S1/S2/终审七段式） |
| `references/trial-court-architecture.md` | 审判庭架构（v2 历史，内容与上重复，存档参考） |
| `references/workbuddy-experts/_index.md` | 39 专家团索引 |
| `references/workbuddy-adaptation.md` | WorkBuddy 专家/技能/MCP 资产体系（OpenCode/ZCode 下作专家池索引参考） |
| `references/zcode-adaptation.md` | **ZCode 适配指南（实测：task 调度、mini-vision 视觉路由、产物收集、TRIAL_BASE、路径映射）** |
| `references/opencode-adaptation.md` | OpenCode 适配历史（v3.2.0-opencode，存档参考） |
| `references/cross-validation.md` | 交叉验证规则 |
| `references/test-workflow.md` | **改本技能逻辑/契约/脚本前必先读，作为回归门禁（触发守则见该文件 §3.1/§4）** |

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
