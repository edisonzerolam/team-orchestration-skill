---
# ==== 已停用（老板指令 2026-09-10：先安装但停用，后续再进行检查修复）====
# 恢复方式：删掉下面两行即可（或把 disable-model-invocation 改为 false）
#   仅 /点名可用 -> 只删 user-invocable 行
disable-model-invocation: true
user-invocable: false
# ==== v3.13.0-dsh · 2026-09-13 · 插件反向吸收（吸收来源：dsh-agent-teams 插件 v0.1.17 · @nanmicoder/dsh-agent-teams）====
# 新增 references/structured-contract.md （结构化契约：kind/contract/verdict+findings/attempt/三层质量门/reviewPolicy）
#      references/web-staged-lifecycle.md （两阶段生命周期：staged 审批 / halted / resume(reason) / escalated）
# 五阶段对抗协议与二审终审制本体语义未变（仅新增结构化落点）；改动登记见 references/merge-history.md 2026-09-13 条目。

name: team-orchestration
version: 3.13.0-dsh
description: "多智能体团队编排引擎 — 五阶段对抗协议(二审终审制) + A3契约 + 降级路径 + 主理人同步领活(非协议派发不空等) + 视觉识别路由(实测验证) + 后台送达契约 + 依赖感知任务图/成员persona(吸收dsh-agent-teams) + 提问中转协议(防子代理死锁)。触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组"
tags: [orchestration, team, multi-agent, trial-court, two-instance, vision, task-graph, question-relay, free-pool, sensenova]
---

# Team Orchestration v3.13.0-dsh

## 0 首次运行适配（v3.10.1 · TC-20260816-7）

> 本技能适配多种桌面 agent / harness / AI 客户端（DSH / ZCode / OpenCode / Claude Code / Codex / WorkBuddy）。**安装后首次触发时自动适配当前客户端**：

1. 跑 `python scripts/detect-runtime.py`（环境变量锚 + 用户目录特征加权判定）
2. 按 `references/runtime-adaptation.json` 的 `adaptation_doc` 加载对应适配文档（如 DSH → `references/dsh-adaptation.md`）
3. **技能根检测（v3.10.2 · TC-20260816-7）**：asset-resolver 自动收集**当前机器**全部客户端技能根（~/.agents/skills、~/.dsh/skills、~/.workbuddy/skills、~/.claude/skills、~/.codex/skills + 工作区项目级 `--project-dir`）——**换机安装即扫新机器的技能**，无需任何配置
4. 按该文档的工具映射执行五阶段协议（子代理拉起/产物收集/提问中转/检查点各客户端不同）
5. `unknown`（无锚点）→ 向用户确认客户端类型 → 选择适配文档；无对应文档按通用协议（磁盘案卷 + A3 契约）执行

> **子代理技能面（已实测 · TC-20260816-7）**：DSH 子代理经 available_skills 注入面发现本机技能（约 203 个，与 main 一致），skill 工具可按名称加载技能正文（实测 `schema` 加载成功）——**编排器子代理天然"发现并使用当前机器技能"，无需额外注入**；§4-3 的技能候选清单用于约束子代理聚焦候选（防误触发），非加载前提。

> 适配状态写入案卷 `00-立案/案卷信息.json` 的 `runtime` 字段；后续案卷沿用同一判定，不重复检测（跨客户端迁移时重新检测）。

## 1 触发条件

满足**任一**即走五阶段对抗协议（二审终审制）：① >1 子代理 ② main+子代理协作 ③ 多角度执行。
不满足 → 直行（单 agent）。直行中复杂度升级 → 自动切换。

## 2 规模门 + 降级路径

- **L1-L2**（单维度/低争议/子任务≤3）：直行，单 agent + 自我批判。
- **L3+**（多维/高争议/跨领域）：五阶段对抗协议（二审终审制）。
- **降级**：若无法确定合适的 2+ 差异化视角，降为单 agent + 自我批判（不硬凑团队）。降级后仍派子代理时，main 同步领活不空等（§4.6）。
- **升级**：L2 涉及 ≥3 领域 → 升为 L3。

**Effort 分级预算（v3.5 增强 · P1-1）**：规模门判定后按档分配 tool-call / token / 子代理数上限。**注意：此为预算档，非规模门档位**——规模门只有 L1/L2/L3+ 三档、无 L4 档（见 `references/test-workflow.md` B2），L4 在此仅作预算上限参考，避免与 B2 混淆。

| 档位 | 子代理数上限 | token 预算上限 | 质证轮数上限 | 超预算处理 |
|------|------------|--------------|------------|-----------|
| L1 | ≤1 | ≤4k | 0（直行） | `scripts/token_budget.py` warn/block |
| L2 | ≤3 | ≤8k | 1 | warn（80%）/ block（100%） |
| L3 | ≤6 | ≤16k | 2 | warn（80%）/ block（100%） |
| L4（仅预算参考） | ≤8 | ≤32k | 2 | warn（80%）/ block（100%） |

**BATNA 降级显式化（v3.5 增强 · P1-6）**：降级路径落盘时写「降级原因 + 原拟方案 + 保底方案（BATNA）」，记录到案卷 `06-资产使用记录`。

## 3 五阶段流程（二审终审制）

```
立案(main直思) ──► 并行举证(N子代理) ──► 质证(回灌→修正) ──► 一审(裁决→回灌修订1轮) ──► 二审终审(不回灌)
```

> **与审判庭协议的关系**：五阶段是审判庭完整协议（Phase A 立案/B 举证/C 质证/D 一审/E 二审终审）的**精简视图**；复杂议题按 `references/trial-court-protocol.md` 展开执行（含案卷归档、自学习 S1/S2、终审七段式）。
> **能力接缝映射（吸收 dsh-agent-teams D1）**：本技能复用的宿主能力（`subagent`/`send_message` spawn+wake、`workflow` 批量编排、`checkpoint_manager` 检查点、`pwsh` 跑决策脚本、磁盘案卷为真相源）的 DSH 等价映射见 `references/dsh-adaptation.md` §1/§3；每个 adversarial 阶段有显式终端门（§4.2.1 任务状态机 `completed|failed|cancelled`），依赖未到终态不得启动下一阶段。

**A 立案**（main 内存中完成，无需脚本）：
1. 5W2H 澄清（模糊则追问 ≤2 轮）
2. 拆 1 核心争点 + 2-5 子争点
3. 选角色（见 §6）+ 为每角色选定专业视角；**动态派数（v3.9 · TC-20260816-6）**：L3+ 先跑 `python scripts/task-decomposer.py --task "<任务>" --concurrency <并发上限> --json` 取 `suggested_subagents`（{value, range, rationale}）作**推荐派数**（非强制，main 可覆写并留痕理由；L1/L2 直行信号不走并行举证）。**并发参考数据（v3.9 补强）**：立案时先跑 `python scripts/concurrency_check.py check`——若 `status=stale`（参考数据 >14 天未更新）→ **先派 1 个子代理**查模型提供方官方文档（web_search/browser）更新 `references/concurrency-data.json`（`concurrency_check.py update --official N --source URL`）；**更新失败/不可用** → 采用 `suggested`（= 上次更新至今最大派出数 +1 试探）；每次实际派出后跑 `concurrency_check.py record --n <N>` 记录历史。
4. **资产路由（v3.10.2 · TC-20260816-7）**：跑 `python scripts/asset-resolver.py --task "<任务原文>" [--project-dir <工作区>]`（或读 `references/last-asset-snapshot.json` 快照）→ 按触发词召回**当前机器**技能（多客户端根：~/.agents/skills、~/.dsh/skills、~/.workbuddy/skills、~/.claude/skills、~/.codex/skills + 项目级）→ 取技能候选 top-N（≤5，按域相关度）+ MCP/连接器 → 注入子代理 prompt；快照 `snapshot_at` >30 天先 `--snapshot` 再生成（§9.5-3 保鲜）。**可选增强（非主路径）**：多机注册表远程技能（`references/skill-registry.json`，SSH 拉取，命中标注「在 <host> 机」）——立案 `--registry-check`（保鲜 7 天）驱动刷新，详见 `references/routing-tables.md` §8（参考文件索引）
5. **（v3.6 · 吸收 dsh-agent-teams）登记依赖感知任务图**：把阶段/子争点记为 `tasks.json`（含 dependencies）；**资产可用性不预检**，在**首次真正 spawn 时 fail-loud**（含可操作错误，如视觉路由三路不可用时的 OCR 兜底提示），不因兄弟资产时序在立案期随机失败。

**B 并行举证**：同一消息并行拉起 2-6 个 Agent 子代理，每个 prompt 按 §4 四要素模板。子代理独立举证，可联网/调 MCP/用技能。**派出记录（强制，v3.9 补强）**：spawn 后**立即**跑 `python scripts/concurrency_check.py record --n <实际派出数>`——记录每次任务实际派出数（口径：B 举证 spawn 数；C 质证追加时追加记录）——这是并发参考数据 `max_spawned` 的唯一事实来源，禁止跳过。

**C 质证**：
1. 汇总 B 产物 → 回灌给每个子代理 → 逐条质证他方 → 修正己方（**默认 1 轮**；分歧>2 追加 1 轮，最多 2 轮）
2. 分歧收敛判定（分歧≤1 即进入一审）→ 产物落盘 02-质证/
3. **追加派数（v3.9 · TC-20260816-6）**：质证发现视角缺口时，main 可定向追加子代理（≤2）——**追加须由质证缺口触发**（如缺某领域视角/证据需独立验证），追加后复检 `C(N,q)=N×(2+q)` 预算不超 BLOCK；q_max=2（质证轮数上限，C2 契约）

**D 一审（裁决 + 回灌修订）**：
1. main 逐条裁断：采信/部分采信/排除（每项说明理由）→ 产出《一审判决书》（**中间产物**，落盘 03-一审/first-instance-verdict.md，流程中展示摘要，不单独交付）
2. 把《一审判决书》+ 各方最新产物回灌给每个子代理 → 逐条回应判决（服判/异议+理由）+ 立场再修订（**固定 1 轮**，不因收敛提前、不追加第二轮）→ P{i}(C) 落盘 04-回灌修订/

**检查点（v3.5 增强 · P0-4；v3.10.3 · TC-20260816-8 键名对齐）**：**02-质证/** 与 **04-回灌修订/** 落盘后各设一次检查点（`scripts/checkpoint_manager.py`，**step_id = 阶段名**（`--step 02-质证` / `--step 04-回灌修订`，与案卷 `resume_from` 的阶段名一致），state 含 `{docket_id, 轮数, 分歧数}`）。中断恢复：新会话读案卷 JSON 的 `resume_from` + 检查点目录——`--action plan --steps "00-立案,01-举证,02-质证,03-一审,04-回灌修订,05-二审终审"` 返回 next 阶段，**从最后完成的阶段继续**，不重跑已完阶段。跨会话断点恢复协议见 `references/zcode-adaptation.md` §9。

**新会话读案卷续审（v3.5 增强 · P0-4）**：接手进行中案卷时（对标 `references/workbuddy-experts/opc-team/` 的 state 文件机制）：① 读案卷信息 JSON（`00-立案/案卷信息.json`，含 `resume_from` / `skipped_phases` 字段）→ ② 向用户展示进度摘要（已完成阶段/当前阶段/剩余子争点）→ ③ 从断点继续，**不重复提问**已澄清过的 5W2H。

**E 二审终审**：
0. **终审前置门禁（v3.8 · TC-20260816-3）**：进入终审前必须满足「回声收齐或终止确认」——① 全部子代理本争点回声（产物 + 完成通知）已收集完毕；或 ② 经 `list_agents` 确认全部子代理已终止（ready / 无运行中、不再产生新回声）。两者满足其一才可终审；仍有子代理运行且存在未收集回声时**不得**进入终审（不因"通知未弹出"无限等待，但须主动确认终止态——与 §4.2 收尾兜底互补：质证前核对任务返回值收齐，终审前核对回声/通知收齐）。**结构化落点（v3.13 · 吸收 dsh-agent-teams）**：该门禁在案卷 `tasks.json` 对应终审任务上落 `echoGate{expected,collected,confirmedAt,reason}`（`reason` ∈ `echo_collected` \| `agents_terminated`）——原「回声收齐或终止确认」语义不变，只是由文字判定变为可审计字段（见 `references/structured-contract.md` §A3）。
1. 汇总一审修订产物 → main 终局裁断：采信/部分采信/排除（每项说明理由，禁止引入新论点）
2. 产出《终审意见书》（**二审终审，不再回灌**）→ 交付用户
3. 归档（异步，不阻塞交付）：**archive-not-delete**（v3.6 · 吸收 dsh-agent-teams）——将**全案卷**（tasks.json 依赖图 + 各阶段事件 + 分歧数/回灌轮数/收敛路径 + believability 权重）随终审意见书归档于 `deliverables/trial/YYYY-MM-DD/<docket_id>/`，供复盘与自学习挖掘。

## 4 子代理 Prompt 四要素 + A3 契约

每个子代理 prompt 必须包含：
1. **目标**：你是「{角色名}」，专业：{领域}，立场：{正/反/中立}。争点：{具体子问题}。
2. **格式**：严格输出 A3 JSON — `{"role":"...","artifacts":{"conclusions":[],"evidence":[],"risks":[],"actions":[]},"confidence":0.0,"uncertainties":[]}`；如需用户澄清，附加**软键** `"questions":[{"q":"...","context":"...","needed_by":"..."}]`（最多 2 条，仅"无法自查的实质歧义"才写）。
3. **工具**：可用资产列表（从 A 阶段选取注入）——**技能候选格式**（v3.10 · TC-20260816-7）：`技能 <name>（<触发词/用途>，source=<agents|workbuddy|...>）`；**子代理经本机 available_skills 注入面发现技能、用 skill 工具按 name 加载正文（已实测可用）**，聚焦候选清单内技能，不自发调用候选外技能（防上下文污染与误触发）。
4. **边界**：聚焦你的视角，不越界；存疑标注"不确定"；≤400 字；**后台子代理无用户交互面——禁止调用 `ask_user_question` 等提问类工具**（会永久挂起死锁，实测 TC-stops-001）；需澄清时写 A3 `questions` 字段，由主理人中转。
5. **成员 persona 块（v3.6 · 吸收 dsh-agent-teams）**：追加自包含 persona（身份/署名 + 团队上下文 + 案卷状态位置只读 + 工作规则：收到指派→认领→in_progress→completed+output→向队长短报 + 你是 worker 不建团/加员/删团/裁决 + 反盲从每条结论自带反论）。完整模板见 `references/agent-teams-absorption.md` §3。

### 4.5 提问中转协议（v3.7 · 实测教训 TC-stops-001）

> 背景：子代理直接调用 `ask_user_question` 会在后台永久挂起（无交互面 → 无人应答 → 死锁，实测 TC-stops-001）。正解 = **提问中转**：子代理把澄清需求写成结构化数据，由 main 唯一对外提问并回灌。

- **四步协议**：
  1. **子代理侧**：禁止提问类工具（§4 边界）；澄清需求写入 A3 `questions` 软键（q/context/needed_by，≤2 条/子代理）。
  2. **main 收集**：汇总全部子代理 `questions` → **合并同类项** → **过滤可自查项**（main 能读文件/搜索答掉的不问用户——"先想办法再开口问"）。
  3. **main 提问**：一次 `ask_user_question` 携带合并后问题（带选项/推荐答案）。
  4. **main 回灌**：答案经 `send_message` 回灌给相关子代理（depth-1）→ 子代理带答案进入下一轮次重新举证/修订。
- **边界（防滥用/防二次死锁）**：
  - 澄清轮次上限：每子代理 ≤2 问；整体澄清 ≤1 轮；超限走"标记不确定"降级——**不计入质证/回灌轮次**（不破坏 C2 固定轮次语义）。
  - 用户不答/答不足：不无限等——子代理带 `uncertainties` 继续，main 裁决时降权。
  - **main 中立**：转发问题不附加自己的倾向（反盲从纪律延伸，防信息级联）。
  - 兼容 C1/C2/C3：questions 随 A3 摘要走 C1 交接；为**软键**（缺失仅 warning 不重试）。

### 4.0 主理人纪律（工具级越权防护 · v3.6）

> 把"禁止成员越权/直连"从提示词纪律升级为可执行层（吸收 dsh-agent-teams 的 captain-only tool deny）。

- 对 `subagent`/`subagent_fork` 的成员，在 prompt 中显式声明 **deny 列表**：不可建团/加员/删团/创建任务/终审裁决；验收时校验其 `artifacts.actions` 未含越权项。
- **技能 deny（v3.10 · TC-20260816-7）**：`disable-model-invocation` 敏感技能（baoyu-post-to-wechat/weibo/x、baoyu-danger-gemini-web/x-to-markdown、baoyu-electron-extract、baoyu-wechat-summary、notebooklm、revops、social）**不得被子代理自动调用**——仅用户显式点名时由 main 直接调用（与 AGENTS.md 第六节互洽）；asset-resolver 已按 frontmatter 门禁自动排除它们（快照技能段不含敏感技能）。
- **角色视角裁剪**：给立案官/举证/质证/一审/二审每角色一块 scope（允许产物 + 禁止动作，如"二审不得引入新论点"直接写入 persona 禁止项）。
- **横向通信 vs 裁决**：允许成员间**交换信息/产物**（`send_message` depth-1）；**禁止绕过主理人裁决**与变更团队权。细化原"禁止成员直连"铁律（禁绕过裁决，不禁横向通信）。

### 4.3 交接与收敛契约（v3.3 增强 · TC-20260809）

> 处理大量跨 agent 交接时降低上下文污染、收敛无界重试。核心：**交接只传摘要、验收只卡 schema、收敛有上限**。

- **C1 结构化交接摘要**：子代理回传/交接时，只传结构化 A3 摘要（conclusions + evidence + risks + actions）。evidence 须携带 **artifact 指针**（来源路径/引用名），质证阶段按指针取原始论述，**不传全量对话**，防上下文随对抗轮次恶化。
- **C2 重试上限 + 达标阈值**：质证默认 1 轮、分歧 >2 追加 1 轮、**最多 2 轮**；一审回灌修订**固定 1 轮**（二审终审制：不因收敛提前、不追加第二轮，修订后直接进入二审终审）。单个子代理产出**因相同原因不达标**时最多重试 2 次即收敛（固定上限，防 token 失控）；不同原因可继续，但累计 >2 次仍收敛并标记"低可信度"。
- **C3 输出 schema 级检查**：每子代理输出的 A3 须过字段完整性校验——**硬键** `role / artifacts{conclusions,evidence,risks,actions} / confidence / uncertainties` 缺失即判不达标触发 C2 重试；**软键**（confidence 数值偏离、uncertainties 为空、`questions` 缺失等）仅 **warning 不重试**，避免主观字段假阳性。校验宿主=接入 C2 重试闭环（A3 产出 → 校验 → 不达标重试），复用 `scripts/cross-validator.py`。单子代理累计消耗超 token 阈值即终止并返回部分结果。**（v3.13 · 吸收 dsh-agent-teams）** 在既有 A3 硬键之外**可选**扩展 C1 交接摘要软键 `handoffSummary{conclusions,evidence[{claim,artifact}],risks,actions}`——与 `questions` 同为**软键**（缺失仅 warning、**不触发 C2 重试**），保持 C3 软键语义不变。

### 4.4 反盲从义务（v3.5 增强 · P0-5）

> 防信息级联：多子代理同源引用会制造"虚假多数"。核心：**自反证、独立证据收敛、main 不预流露倾向**。

- **① 自反证义务**：子代理 prompt「边界」中追加——每条结论必须自带 1 条最强反论并回应；缺失则该条结论置信度上限 0.6。
- **② 收敛需独立证据**：分歧收敛判定不能只看"多数一致"——多数方须有 ≥2 个独立来源支持才可判收敛；仅共识但单源 → 标「共识但单源」，进入一审时降低采信权重（见 §5 加权投票）。
- **③ main 纪律**：质证/回灌修订阶段，main 在举证收齐前不表达个人立场倾向，避免信息级联引导子代理。

### 4.1 子代理模型选择（视觉识别路由）

> **统一结论（v3.5 · P1-5 口径统一）**：**ZCode 运行时视觉路由三路不可用** —— ① main 直读失败；② mini-vision 子代理类型运行时不可调用；③ 子代理继承 main 的 text-only 模型。**视觉任务当前唯一可行路径 = 外部 OCR/视觉通道转文本**后喂子代理处理。与 `references/zcode-adaptation.md` §4、`references/test-workflow.md` §2.C C7 同口径（ZCode 2026-08-09 三路运行时验证）：
> 1. **main 直读**：✗ 失败 — `Media omitted ... model does not support image input`（deepseek-v4-flash text-only）。
> 2. **mini-vision 子代理**：✗ `Agent type 'mini-vision' not found. Available agents: general-purpose, Explore` — ZCode 运行时仅暴露 general-purpose/Explore 两种内置 subagent 类型。
> 3. **general-purpose 子代理读图**：✗ 失败 — 子代理继承 main 的 text-only 模型。注：`~/.zcode/v2/config.json` 模型池注册表中或有带视觉的模型（TC-20260809-002 反编译实证），但**运行时不可通过现有调用路径触达**，故结论仍为"三路不可用"。

- **视觉任务路由（ZCode 实测）**：**三路不可用**，视觉任务当前只能走外部通道：
  1. **外部 OCR/视觉通道转文本**（当前唯一可行路径）：图片先经外部 OCR 转结构化文本，再喂子代理处理。
  2. **切换视觉模型**：若 ZCode 运行时可触达带视觉的模型（注册表 modalities 支持 image 且 main/子代理可切换），main 直读即可。
  3. **注册用户级 agents**：调研 ZCode「Settings → Subagents」是否可将 agents/*.md 注册为可调用类型。
- **兜底约定**：子代理 prompt 不传图片路径，只传「图片的文本化内容」；无法文本化时向用户说明。
- **若视觉信息与文字冲突**：以直接观察/主证据为准，裁决注明依据。

> **案卷元状态写权限（TC-20260816-10）**：子代理可落盘自己的 A3 产物（evidence 文件）；但 tasks.json / resume_from / cross_exam / status 等案卷元状态仅 main 统一写入。成员如需券变，经 agent_message 向 main 请求。



### 4.2 后台子代理送达契约 + 看门狗（ZCode 2026-08-09 适配）

> **ZCode 实测口径**：无收件箱机制。子代理产物 = `task` 调用返回值（同步）或后台任务完成通知 + `agent_*/task.output` 产物文件；主环境 SendMessage(to: agentId) 可与已 spawn agent 通信（agent 间直连受限）。

- **产物收集 = 事实来源**：判定 worker 是否完成，以 `task` 返回结果 / Agent 工具 `run_in_background` 完成通知为准；后台任务可用 `task_id` 续接同一子会话。
- **并行契约**：同一消息多次 `task` 调用即并行（2-6 个）；每个子代理 prompt 末尾**必须**写明"返回结构化 A3 JSON 结果"。**并发上界（v3.9 · TC-20260816-6）**：MAX_CONCURRENT=6 为**编排层实测稳定值**（DSH 子代理调度 + 上下文 + 预算约束下）；**模型官方并发不构成约束**（deepseek-v4-flash=2500 账号粒度，见 api-docs.deepseek.com rate_limit，429 超限可工单扩容）；--concurrency 可调，受 tier_cap 截断；五阶段对抗（含回灌轮次）建议 4-6。
- **看门狗**：spawn 每个后台 worker 后设超时（建议 5 分钟），超时主动用 `TaskOutput`/读产物文件拉取其产出，绝不无限期等待。
- **收尾兜底**：并行 spawn 后、进入质证前，强制核对全部 task 返回值已收齐再继续；不因"通知未弹出"就停在等待态。**终审前回声核对（v3.8 · TC-20260816-3）**：进入 E 二审终审前同样强制核对——全部子代理回声已收集（产物落盘）或经 `list_agents` 确认已终止（无未处理通知），未收齐且未终止时不得终审（见 §3 E 前置门禁）。
- **禁止轮询**：后台任务完成会收到通知，不要 sleep/轮询等待。

### 4.2.1 依赖感知任务图 + durable 邮箱增强（v3.6 · 吸收 dsh-agent-teams）

> 吸收自 `references/agent-teams-absorption.md`（来源 dsh-agent-teams）。在不改五阶段主流程前提下，把进度/运维层显式化。

- **任务状态机**：把 A-E 阶段登记为带状态的显式任务，迁移白名单 `pending→claimed→in_progress→completed|failed|cancelled`（终态无出边，禁从 completed 跳回）。案卷 `00-立案/tasks.json` 记录 `{id,subject,status,assignee,dependencies[],output}`；**执行代次三件套（v3.13 · 吸收 dsh-agent-teams）**：追加 `attempt`（单调执行代次）/ `attemptId`（当前代次能力凭证，成员更新任务必须回带）/ `handoffId`+`reassigning`（交接期禁派发）——重派即使旧 `attemptId` 失效，**用旧凭证的更新被拒并判 stale**（字段语义见 `references/structured-contract.md` §A5）。
- **依赖门控**：每阶段声明依赖（立案⊲∅；举证⊲立案；质证⊲全部举证；一审⊲质证；二审⊲一审）；**依赖未全 completed 不得启动**——质证必须在全部举证收齐后开始（结构性替代人工核对）。
- **磁盘即真相，事件仅审计**：任务/成员/邮箱状态以落盘为准；会话事件日志仅作确定性复盘。成员完成任务却忘走仪式→主理人以 `status`/文件汇总（不采信自报）。
- **persist 纪律**：同一案卷内落盘操作**串行 + 原子写**（先临时文件再 rename）；读产物遇畸形段→降级低可信警告不崩溃；读 `案卷信息.json`/`tasks.json` 前做结构校验，失败即判不可续。
- **一主理人一团队**：主理人同时只主持一个进行中案卷；成员以 `list_agents`/activity 实时监控。
- **viewer-scoped**：质证成员在回灌前只见己方产物（天然隐藏他方论点，防对抗泄漏）。

### 4.6 主理人同步领活纪律（非协议派发不空等 · v3.9.1 · TC-20260902）

> 适用范围：**非五阶段对抗协议**的子代理派发场景——§1 直行中的并行派发、§2 降级路径、并行任务派发、常规编排。协议内 B 举证/C 质证阶段 main 须保持中立裁决位（§4.4 ③ 不预流露倾向），**不适用本条**（main 领举证工作会污染裁决）。

- **不空等原则**：main 派出子代理后不得进入等待态——在同一消息内自领一份与子代理**无依赖冲突**的工作，与子代理并行推进；子代理运行期间 main 的工作照常进行，完成后才进入收集/汇总。
- **领活优先级**：① 无依赖的独立子任务（自己专业视角最能出活的那份）② 案卷/汇总骨架准备 ③ 上下文与资产核查。有依赖的裁决/汇总工作须等收齐后再做，不得用它替代并行领活。
- **并发适配（ZCode 实测 · 与 §4.2 并行契约互洽）**：同消息最多 spawn 2，被拒减 1 重派；剩余并发额度由 main 自身份额补足——常态即"spawn N + main 领 1 份"。
- **份额入账**：main 自领工作写入案卷 `tasks.json`（`assignee=main`），与子代理任务同一状态机管理；main 不代写子代理已认领的份额（领活≠越俎代庖），也不因领活豁免自己的裁决/验收职责。
- **禁止反例**：spawn 后 sleep/轮询等待（§4.2 已禁）；领活后只挂名不产出；领的活与某子代理任务重叠造成重复劳动。

### 4.8 免费池角色路由（v3.12 · 2026-09-13 · dsh-plugin-subagent-director 落地）

> DSH 环境专属：`subagent_role` 工具全局可用（director 插件，settings `subagent-director` 段 7 角色）。**完整调用规则（R1-R7 七条纪律 + 并发限制 + 派单通道 + 验证方法）以 `~/.dsh/skills/dsh-free-pool/INVOKE-RULES.md` 为单一事实源**，本节只列编排层增量。ZCode/其他 harness 无此工具，本节不适用。

- **派单优先级（DSH）**：L1 跑量/调研/分析/编码的**非裁决位**子任务 → 优先 `subagent_role({role, prompt})`（免费池，省 token）；终审/质证裁决/需用户交互的任务 → 保留主对话付费模型（或 AgentTeams `arbitrator` 成员）。
- **角色选择判据**：数据分析→sensenova-analyst（>256k→agnes-analyst）；调研长文→sensenova-researcher（超长→agnes-researcher）；批量跑量→sensenova-batch-runner / agnes-batch-runner；编码→agnes-coder。
- **异质性红线（对齐 §4.7）**：sensenova 三池同源 = 1 个独立来源，**不得**让两个 sensenova 角色互查/互审；跨供应商（agnes ↔ sensenova）才算 2 来源，可交叉质证。
- **降级**：角色 `fallback` 已配置池挂自动切付费池（kuaitu/qwen3.8-27b-2）；连续 3 次同类失败熔断，派发记录注明降级原因。
- **并发（编排层增量，五阶段对抗专用）**：B 举证并行派单受 INVOKE-RULES R5 约束（sensenova 单池 ≤20 / agnes 单池 ≤6 / 跨池 ≤12）；**质证/对抗角色必须跨供应商**（sensenova 举证 ↔ agnes 质证），同池角色不得互查（R6）。
- **批量规则题（编排层增量）**：B 举证的清单核对/格式转换子任务，派单 prompt 必须含示例 + 明确总数（R3，两池分组规则贯彻弱的跨模型共性）。
- **人设注入（编排层增量）**：workflow/subagent 派免费池时 persona 必含边界纪律段（R2）；`subagent_role` 走 director 已内置完整人设，无需手动拼。
- **与 §4.6 领活纪律不冲突**：`subagent_role` 派单后 main 照常同步领活；免费池角色无交互面，questions 字段回传由 main 中转。

### 4.7 上下文防火墙与异质性（v3.11 · TC-20260906-2 · 依据近3月调研共识）

- **子代理=上下文防火墙，不是并行算力**：派发目的一是隔离上下文（把大文件扫描/长检索限制在子代理窗口内），二是异质视角对抗；"多开几个提速度"不是合法理由（HN/Reddit 共识 + MAST 失败学）。子代理提示词必须**自包含**（工具协议+环境坑+熔断纪律），回传**压缩为单消息**结构化结论，禁止让子代理把原始材料整段带回。
- **异质性强制**：互查/对抗角色不得由同质配置担任——同能力模型互相强化而非纠错（arXiv 2608.02827 偏置共识）。对抗协议的多/空/风控天然异构，符合；同模型多实例重复背书不计为独立来源。
- **隔离三件套**：受限工具面（只读任务不给写）、递归上限（子代理不再 spawn 子代理，除非协议允许）、单消息回传。

## 5 合并策略

- 封闭题（是/否、选型）→ **加权投票制（v3.5 增强 · P0-6）**：每方投票权重 = **believability = 历史命中率（`learning-data/expert_scores.json`，缺省 0.5）× 独立来源数（≥1）**。多数采信改**加权多数采信 + 少数留痕**；等权投票不再作为默认。权重计算见 `references/cross-validation.md` §置信度评分算法。
- 开放题（方案、策略）→ 辩论制：main 综合采信，逐条说明理由。
- **统计聚合优先（v3.5 增强 · P1-6）**：数值型子争点（估值/比例/预测）由各子代理**独立估值后聚合**（中位数/均值+区间），**不用辩论结论替代数值统计**；非数值型才走辩论。
- **共识 vs 投票细化（v3.5 增强 · P2-5）**：多子代理对开放题强共识时记录「共识达成路径（独立推导 or 互相引用）」；引用链 ≥2 层的共识降权。
- **self-consistency 采样投票（v3.5 增强 · P2-4，可选）**：数值型子争点在预算允许时，可由同一子代理对同一题采样 3 次独立答案取多数一致；**可选增强、不默认开启**（ZCode 无温度控制，收益有限）。

> **加权投票（v3.5 增强）**：封闭题投票按 believability 加权——每方权重 = 历史命中率（`learning-data/expert_scores.json`，缺省 0.5）× 独立来源数；等权投票不再作为默认。权重计算见 `references/cross-validation.md` §置信度评分算法。

## 6 角色分配

| 子代理数 | 角色 | 适用 |
|---------|------|------|
| 2 | 正/反 | 简单二分 |
| 3 | 正/反/中立 | 权衡问题（默认） |
| 4-6 | 多学科专家团 | 跨领域复杂议题 |

**动态派数推荐（v3.9 · TC-20260816-6）**：上表为**视角模式基线**；实际派数由 `task-decomposer --concurrency N` 按 复杂度 × 分工域数 × 模型并发 计算推荐值（L3+ 区间 [2,6]；L1/L2 直行信号）。推荐值非强制，main 可覆写。**预算硬约束（覆盖全档位）**：任何派数（含直行信号下手动派 2-3）进入各阶段前须过 `C(N,q)=N×(2+q)` 预算校验（WARN 80% / BLOCK 100%）；质证追加须由缺口触发且追加后复检。

专家人设库：`references/workbuddy-experts/`（40 团队 257 agents（磁盘 agents/*.md 与 plugin.json agents[] 声明完全一致，2026-08-16 实测），按需读取 agents/*.md 注入 prompt）。

**专家池渐进披露（v3.5 增强 · P2-5）**：立案时先注入最小集（§8.1 已定域，仅 T1 团队头寸 + knowledge 最小集），阶段推进**按需追加**（如质证中发现缺某领域视角，再补注入相关 agent 人设），不做全量披露——省上下文且避免立场污染。

## 7 质量门禁

- 二审终审禁止引入新论点（未在举证/质证/一审回灌修订出现不可采信）
- 可信度 = 最薄弱证据的可信度
- 每轮质证与一审回灌修订标注「变与不变」
- 主理人铁律：禁止代写 / 禁止跳阶段 / 禁止成员直连（细化：**禁绕过裁决**，不禁横向通信）
- **磁盘即真相**（v3.6）：任务/邮箱/状态以落盘为准，事件日志仅审计；终审仅接受 `completed` 证据，blocked/failed → 复审/重派（见 §7.3）
- **终审结构化落盘（v3.13 · 吸收 dsh-agent-teams）**：终审裁断以 `verdict{pass,needs_revision,reject} + findings[{id,severity,problem,requiredFix}]` 结构化落盘（中文裁断↔三态映射、severity 四级与五维 rubric 的确定性映射见 `references/structured-contract.md` §A4）；`pass` 不得残留未解决 `high`/`blocker`
- **交付门清单（v3.13 · 吸收 dsh-agent-teams）**：交付前须逐条过**交付门清单**（review 全 `pass`、`failed` 必有后续、终审存在且五维达标、`changedPaths` 落在 `inScope` 内、独立来源 ≥`minIndependentSources`、无未解决高危、`escalated=false`）——与「磁盘即真相 / 仅接受 completed 证据」并列，清单见 `references/structured-contract.md` §A8

## 7.1 终审意见书最小契约（v3.1 · 二审终审制）

终审产出即**终审意见书**（二审终局文书；一审判决书为中间产物，落盘 `03-一审/first-instance-verdict.md`，结构见 `references/trial-court-protocol.md` §6.2），章节结构：
1. 议题与争点（核心 1 + 子 2-5）
2. 各方举证摘要（每方 A3 JSON 的 `artifacts.conclusions` 要点）
3. 质证与一审修订记录（质证轮数 + 回灌修订轮 + 每轮「变与不变」）
4. 裁决理由（逐条：采信 / 部分采信 / 排除 + 理由；二审禁止引入新论点）；**逐条字段化（v3.13 · 吸收 dsh-agent-teams）**：每条裁决写 `{id,severity,problem,requiredFix}`，`severity` 由 §7.2 五维 rubric 的最低分按确定性映射得出（≤0.3 `blocker` / ≤0.6 `high` / ≤0.8 `medium` / >0.8 `low`），原始五维分须同时保留在 `rubricScores`（映射表见 `references/structured-contract.md` §A4）
5. 最终结论（含可信度 = 最薄弱证据的可信度；标注"二审终审，不再回灌"）

**A3 JSON 字段映射**：`role`→举证方；`artifacts.conclusions`→争点结论；`artifacts.evidence`→依据；`confidence`→可信度；`uncertainties`→存疑项。

**归档**（异步，不阻塞交付）：**工作区根** `deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（docket_id 格式 TC-YYYYMMDD-N；TRIAL_BASE 支持环境变量覆盖，见 `references/zcode-adaptation.md` §5）。

## 7.2 裁决偏差对冲 + 回退重审契约（v3.5 增强 · P0-1）

**裁决偏差对冲**：① **先独立推导再引用**——二审终审对每子争点先写 main 独立判断，再引他方产物佐证/反驳，顺序不可反（防被多数方结论锚定）；② **五维 rubric**——依据充分性/来源独立性/论证自洽/与质证一致/反证回应各 0-1 分，**任一维 ≤0.3 该条判 fail，回退一审重审**（不跳过、禁止直接交付）；③ **位置交换**——开放题裁决前做一次"立场互换推演"（若采信反方，正方最强反驳是什么？）并记录在终审意见书"裁决理由"备注列。

**回退重审契约**（与 C2 固定轮次语义互洽）：
- 回退重审限**同一子争点最多 1 次回退**；超过仍 fail → 走 §7.3 独立复审/升级路径。
- 回退仅重做 **main 侧独立裁决**（重写该子争点的一审/终审理由），**不重新回灌子代理**——保持 C2「一审回灌修订固定 1 轮」语义不被破坏，也不追加质证轮次。
- **五维 rubric 全维达标后才进二审**；未达标不可直接交付。
- 重审次数写入案卷 `cross_exam` 字段（`rehear_count`），与阶段轮数一同可审计。
- 阶段顺序约束：回退重审不改变 A→B→C→D→E 的推进方向（见 `references/test-workflow.md` §2.A A2 判据说明）。
- **回退次数结构化（v3.13 · 吸收 dsh-agent-teams）**：回退重审次数记为 `rehearsalCount`，与质证轮次 `round` **解耦**（回退只重做 main 侧独立裁决，不追加质证轮次），随案卷 `cross_exam` 字段一并落盘可审计。
- **超限升级（v3.13）**：`rehearsalCount` 超过 `reviewPolicy.finalReviewMaxRehearsals`（默认 1）→ 置 `escalated=true` 并走 §7.3；**`escalated` 不是 halt**（halted 是人工拉停，须 `resume(reason)` 恢复，见 `references/structured-contract.md` §A7 / `references/web-staged-lifecycle.md`）。

## 7.3 独立复审/升级路径（v3.5 增强 · P1-4）

任一子争点置信度 <0.3（cross-validation 判定"不可信"）或整体重审 >2 次 → **不得直接交付**，走独立复审（**全新上下文复核子代理**，看全案卷、不看一审已给结论）或升级用户人工仲裁；留痕入案卷 `06-资产使用记录`/`07-反馈记录`。**独立复审优先调度 `general-critics` 通才批判团**（general-critic 对抗审查 + devil-advocate 反论压力测试，v3.9 · TC-20260816-5）——平衡垂直专家盲点，产出五维 rubric 独立打分。**结构化登记与异质性约束（v3.13 · 吸收 dsh-agent-teams）**：独立复审作为**显式任务**登记（`kind=review` + `reviewStage=final` 的重审分支，或独立 `independent-review` 任务），assignee 须**未参与本争点一审/终审**且**来源组（`sourceTag`）不同于一审 reviewer**（§4.7 异质性强制 + §4.8 R6：同池重复背书不计独立来源）；**无法满足异质性 → 置 `escalated=true`，禁止降级为同源复审**（见 `references/structured-contract.md` §A7）。


> **门禁语义边界（TC-20260816-10）**：eval-gate 通过表示“评估集内技能召回未退化”；token_budget 达标表示“未超预算”；两者均不表示方案正确或交付达标。质量达标由 §7.2 五维 rubric + §7.3 终审独立裁断。


> **执行核心改动门禁（TC-20260816-10）**：SKILL.md §1-§7.3 为执行核心。改前须：① git tag 快照 ② merge-history.md 记录改动意图。改后须：③ eval-gate.py 验证技能召回未退化。改进优先走 references/ 增量文件。


## 8 路由与脚本参考（按需读取 · TC-20260816-9 瘦身）

> 路由/脚本明细已外移 references/，本节为**路由句**——何时读哪个文件：

- **定域 / 团队匹配**（立案步骤 3）：`references/routing-tables.md` §8.1 聚合域表 + `scripts/expert-matcher.py`；40 团归 10 组见 `references/domain-map.json`（域入口 `workbuddy-experts/_domain/<domain>.md`）。
- **技能路由**（立案步骤 4 / 子代理技能候选）：`references/routing-tables.md` §8.2 技能路由表（asset-resolver 不可用时的静态兜底）。
- **脚本调用**（各阶段工具/参数）：`references/scripts-index.md`（21 脚本 + 用法）。
- **免费池子代理路由**（数据分析/调研/批处理三类任务省 token 派发）：`references/sensenova-lite-agents.md`（v3.9.3：`sensenova-analyst`/`sensenova-researcher`/`sensenova-batch-runner` 三池指派判据、降级链、懒加载与换绑纪律）。
- **外部数据查证**：`references/scripts-index.md` §9.5 / `references/data-provenance.md`（来源分层 + 保鲜）。
- **结构化契约 / 质量门 / 执行代次**（派单与裁决任务的字段：kind、contract、verdict+findings、attempt、三层质量门、reviewPolicy）：`references/structured-contract.md`（v3.13 · 吸收 dsh-agent-teams）。
- **两阶段生命周期**（staged 审批 / awaiting_feedback / halted / resume(reason) / escalated）：`references/web-staged-lifecycle.md`（v3.13 · 吸收 dsh-agent-teams）。
- **参考文件完整索引**：`references/routing-tables.md` §8。

> **案卷隔离（v3.10.3）**：`deliverables/trial/` 禁入带 remote 的 git 仓库——TRIAL_BASE 指向仓库外（如 `~/.dsh/trial-archive`）。

## 10 When NOT to Use（v3.5 增强 · P2-3）以下场景**不建议**走五阶段对抗协议，直接降级/直行更合适：
- **纯确定性问题**（单一正确解、无需多视角）：直行单 agent。
- **用户只需单个答案**（无决策权衡诉求）：直行，不组建团队。
- **时间/预算极紧**：对抗协议的开销（多子代理 + 质证 + 二审）超过收益；按 §2 预算档收缩。
- **议题证据完全依赖外部不可核验源**：无法满足 cross-validation 的"来源独立性/归因准确性"，对抗徒增共识假象。

**输出注入扫描**：对子代理产物做"提示注入内容"启发式标记（如"忽略以上指令"类文本）。ZCode 无独立检测能力 → 记为**已知限制**（见 `references/zcode-adaptation.md` §8），保留人工检查路径。

---

> **v3.13.0-dsh（2026-09-13）· 吸收来源标注**：本版为**双向吸收**的"反向"一侧——把 **agent-teams 插件（dsh-agent-teams v0.1.17 · @nanmicoder）** 的结构化契约与两阶段生命周期吸收进本技能，落点 `references/structured-contract.md` + `references/web-staged-lifecycle.md`；正向一侧（本技能二审终审制 → 插件移植规格）见团队交付包 `04-plugin-package/`。改动登记与回滚快照见 `references/merge-history.md` 2026-09-13 条目；执行核心区（§1-§7.3）改动均按三前置流程执行。作者：agnes-coder（团队 team-orchestration-mutual-absorb）。
