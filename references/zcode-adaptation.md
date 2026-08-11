# ZCode 适配指南（v3.4.0-zcode）

> 本文件说明 `team-orchestration` skill v3.4.0 在 **ZCode**（OpenCode 系）环境下的适配要点。
> 适配依据：2026-08-09 四子代理并行调研（A3 举证）+ 1 轮质证（终审意见书 TC-20260809-001，归档于工作区 `deliverables/trial/2026-08-09/TC-20260809-01/final-verdict.md`）；v3.4.0 起走**二审终审制**（一审裁决 → 回灌修订 1 轮 → 二审终审不回灌）。
> 前版适配见 `references/opencode-adaptation.md`（v3.2.0-opencode，历史参考）。

## 0. 核心结论

v3.4.0 已导入并完成 ZCode 适配（2026-08-09）。所有 Python 脚本可直接通过 bash 工具运行（实测 python 3.12.8，expert-matcher / cross-validator 运行 OK）。子代理通过 `task(subagent_type=...)` 拉起，用户级子智能体定义于 **`~/.zcode/agents/*.md`（90 个：51 迁移 + 8 新增 + 31 专家池转化，TC-20260809-002 修正：非 `~/.config/opencode/agents/`）**。SKILL.md 平台说明已替换为 ZCode 实测口径。审判庭为二审终审制五阶段：立案→举证→质证→一审(裁决+回灌修订 1 轮)→二审终审（不回灌），一审判决书为中间产物（03-一审/），终审意见书为二审终局交付。

## 1. 平台差异对照（ZCode 实测）

| 维度 | WorkBuddy (v3.3.0 原版) | ZCode (适配后·实测) |
|------|-------------------------|---------------------|
| 用户级子智能体 | WorkBuddy 专家中心 | `~/.zcode/agents/*.md`（TC-20260809-002 修正；frontmatter 白名单：name/description 必填 + model/thoughtLevel/color/permissionMode/maxTurns/tools/disallowedTools/skills/background/injectAgentsMd/mcpServers；mode/temperature/permission 不被读取） |
| 子代理拉起 | Agent 子智能体 / background worker | `task(subagent_type="<文件名去.md>")`；同一消息多次调用即并行 |
| 子代理模型/权限 | 调用期可指定 | **仅文件 frontmatter 决定**（model/permission），调用期不可覆盖（证据：types.gen.d.ts L838-884） |
| 子代理产物 | `teams/<team>/inboxes/<lead>.json` 收件箱 | `task` 返回值 + `agent_*/task.output` 产物文件；TaskOutput 取回 |
| 后台执行 | background worker + SendMessage 回传 | `task` 工具 `background: true` / Agent 工具 `run_in_background: true` + `task_id` 续接；完成时通知，**禁止轮询** |
| agent 间通信 | SendMessage(recipient=team-lead) | 主环境 SendMessage(to: agentId) 可用（agent 间直连受限，子代理仅 prompt 进/结果出） |
| 视觉识别 | main 切 mimo-v2.5 / `~/.workbuddy/models.json` | **main（deepseek-v4-flash）不可读图** → 一律 `task(subagent_type="mini-vision")` 委托（AGENTS.md P0 规则） |
| skill 路径 | `~/.workbuddy/skills/` | `~/.agents/skills/`（ZCode 用户级技能目录，发现顺序 ②；`.config/opencode/skills` 非 ZCode 消费） |
| 归档路径 | `deliverables/trial/`（Workspace） | **工作区根** `deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（TRIAL_BASE 支持环境变量） |
| 触发机制 | `disable-model-invocation: true`（user-invoked） | 非官方字段（ZCode 官方仅 name/description/when_to_use/license/metadata），保留但**不可依赖**；用 description 措辞控制触发 |
| 后台收件箱/看门狗 | inbox 文件 + TaskCreate 登记 | 无 inbox；产物=task 返回值；超时用 TaskOutput 拉取 |

## 2. 脚本调用方式

```bash
# 在 skill 根目录下通过 bash 工具执行（python 3.12.8 实测可用）
python scripts/task-decomposer.py --task "..." --json
python scripts/expert-matcher.py --task "..." --top-k 4 --json
python scripts/dispatch-planner.py --task "..." --top-k 2
python scripts/trial-court-orchestrator.py docket --issue "..." --roles 3 --out ./docket.json
python scripts/trial-court-orchestrator.py init-learning
python scripts/trial-court-orchestrator.py learning-status
python scripts/asset-resolver.py --snapshot
python scripts/cross-validator.py ...
python scripts/check_team_consistency.py   # v3.3.0 新增校验脚本
python scripts/check_agent_completeness.py # v3.3.0 新增校验脚本
```

> 脚本路径相对 skill 根目录。Windows 下 stdout/stderr 已做 GBK→UTF-8 兼容（reconfigure）。

## 3. 子代理映射（ZCode）

| 原 WorkBuddy 概念 | ZCode 等价物（实测） |
|------------------|---------------------|
| Agent 子智能体（general-purpose） | `task(subagent_type="general-purpose")` 或用户级 agent 名 |
| 专用子代理（人设库） | `task(subagent_type="debug-expert" / "code-reviewer" / "campaign-planner" ...)` — 90 个用户级 agent 任意可用（TC-20260809-002 修正：51 迁移 + 8 新增 + 31 专家池转化；工具 schema 为会话级快照，**新增/迁移后需新会话生效**） |
| 视觉子代理（mimo-v2.5） | `task(subagent_type="mini-vision")`（frontmatter 已配 model: OPENCODE-CHAT/mimo-v2.5，运行时 provider 注册表存在该模型，modalities 含 image） |
| 后台 worker + 收件箱 | `task(..., background: true)` 或 Agent 工具 `run_in_background: true`；产物=task 返回值；`task_id` 续接同一子会话 |
| SendMessage 回传契约 | 子代理 prompt 末尾写明「返回结构化 A3 JSON 结果」；主环境可 SendMessage(to: agentId) 与已 spawn agent 通信 |

二审终审制对抗流程在 ZCode 下：
```
A 立案(main 内存) ──► B 举证(同一消息多次 task 调用并行) ──► C 质证(再次 task 回灌，最多 2 轮)
    ──► D 一审(main 裁决 → 判决书+他方产物 task 回灌修订 1 轮) ──► E 二审终审(main 裁断，不回灌)
```

## 4. 视觉识别路由（ZCode·实测修正 2026-08-09 三路验证 + TC-20260809-002 路径修复）

> **实测修正（2026-08-09 运行时验证）**：视觉路由在旧目录布局下**不可用**（三路全灭）：
> 1. **main 直读**：✗ 失败 — `[Media omitted from provider request because the selected model does not support image input.]`（deepseek-v4-flash text-only）
> 2. **`task(subagent_type="mini-vision")`**：✗ 不存在 — `Agent type 'mini-vision' not found. Available agents: general-purpose, Explore`。当时根因推断为"ZCode harness 只暴露两种内置 subagent 类型"
> 3. **general-purpose 子代理读图**：✗ 失败 — 子代理继承 main 的 text-only 模型，同样报 `Media omitted`。
>
> **根因修正（TC-20260809-002，反编译 app.asar 实证）**：失败原因是 **agent 定义目录错位**——ZCode 用户级 agents 解析 `~/.zcode/agents/`（resolveUserSubagentRoot），而 51 个文件误放 `~/.config/opencode/agents/`。已迁移至 `~/.zcode/agents/` 并补 name 字段后，mini-vision 已正确注册。另：`~/.zcode/v2/config.json` 运行时模型池**含视觉模型**（OPENCODE-CHAT/kimi-k3、OPENCODE-CHAT/mimo-v2.5、OPENCODE/minimax-m3 等 modalities.input 含 image），"模型池无任何视觉模型"的旧结论不成立。
> **生效条件**：工具 schema 为会话级快照，mini-vision 需新会话后调用；其 frontmatter model `OPENCODE-CHAT/mimo-v2.5` 在 provider 注册表（db3cb211-...）存在。

- **可行路径（按优先级，TC-20260809-002 修正）**：
  1. **注册用户级 agents（已落地）**：把 mini-vision 等 agent 定义放入 `~/.zcode/agents/*.md`（补 name 字段），新会话后 `task(subagent_type="mini-vision")` 可用；Settings → Subagents 可查看管理（zcode-guide: zcode-configuration-guide L14 已确认该入口）。
  2. **main 切视觉模型**：运行时模型池含视觉模型（kimi-k3 / mimo-v2.5 / minimax-m3），切换后 main 可直读图片。
  3. **外部 OCR/视觉通道**：图片经外部 OCR 转文本再喂子代理（不依赖模型视觉的兜底）。
- **若视觉信息与文字冲突**：以直接观察/主证据为准，裁决注明依据。
- **视觉任务兜底约定**：子代理 prompt 不传图片路径，只传「图片的文本化内容」；无法文本化时向用户说明并请求外部 OCR 结果。

## 5. 路径变更

| 原路径 (WorkBuddy) | 当前路径 (ZCode) |
|--------------------|------------------|
| `deliverables/trial/`（Workspace 级） | **工作区根** `deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（如 `C:\Users\林昌\.zcode\workspace\default\deliverables\trial\...`） |
| `~/.workbuddy/models.json` | 无等价文件；模型能力在 `~/.zcode/v2/config.json`（provider 注册 + modalities）与 agent frontmatter（model 字段） |
| `~/.workbuddy/skills/` | `~/.agents/skills/`（用户级技能目录） |
| `references/learning-data/` | 不变 |
| `references/workbuddy-experts/` | 不变（39 团队 199 agents 人设库） |

**TRIAL_BASE 环境变量**：`scripts/trial-court-orchestrator.py` 支持 `TRIAL_BASE` 环境变量覆盖归档根（缺省 = 当前工作目录下 `deliverables/trial/`），工作区运行时无需额外配置。

## 6. 快速验证

```bash
python scripts/task-decomposer.py --task "测试任务" --json
python scripts/expert-matcher.py --task "帮我分析宁德时代" --top-k 3 --json
python scripts/trial-court-orchestrator.py docket --issue "测试" --roles 3 --out %TEMP%\verify-docket.json
python scripts/cross-validator.py --input - <<< '{"role":"t","artifacts":{"conclusions":[],"evidence":[],"risks":[],"actions":[]},"confidence":0.5,"uncertainties":[]}'
python tests/run_smoke.py
python tests/check_references.py
```

## 7. 测试与回归门禁

- 修改本 skill 逻辑/契约/脚本前**必先读** `references/test-workflow.md`（回归门禁）。
- ZCode 化判据（test-workflow.md 已更新）：C2（后台送达）以 task 返回值为准、C7（视觉路由）以「main 不读图、委托 mini-vision」为准、R4（看门狗）以 TaskOutput 超时拉取为准。
- 测试目录 `tests/` 覆盖脚本冒烟（`run_smoke.py` 无 pytest 依赖）。

## 8. 已知差异（勿误判为 bug）

- `disable-model-invocation: true` 非 ZCode 官方字段（官方仅 name/description/when_to_use/license/metadata），ZCode 是否消费未证实 → **保留但不可依赖**；触发控制靠 description 前置触发词（≤1024 字符，前 250 字符含触发词）。
- 本机技能单源目录：`~/.agents/skills/team-orchestration`（v3.4.0-zcode）。`~/.config/opencode/skills/team-orchestration` 为 v3.2.0 旧拷贝（OpenCode 工具使用），`~/.workbuddy/skills/` 为更早版本——**改动以 .agents/skills 为唯一事实源**。
- 用户级子智能体定义于 `~/.zcode/agents/*.md`（TC-20260809-002 修正）；frontmatter 白名单不含 mode/temperature/permission（被忽略），新增 agent 用 name/description + tools/disallowedTools/permissionMode 控制行为与权限。
- `~/.workbuddy/models.json` 仍存在（WorkBuddy 侧），ZCode 不消费；视觉模型核对看 `~/.config/opencode/agents/mini-vision.md` 的 frontmatter。
- 归档根三方路径曾不一致（TRIAL_BASE=用户根 vs skill 内 vs 工作区）——已统一为「工作区 deliverables/trial/」（TRIAL_BASE 环境变量化，v3.3.0-zcode 修正）。
