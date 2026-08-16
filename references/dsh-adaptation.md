# DSH 适配指南（v3.5.0-dsh）

> 本文件说明 `team-orchestration` skill v3.5.0-dsh 在 **DeepSeek Harness（DSH）** 环境下的适配要点。
> 适配依据：2026-08 DSH 运行时机制调研（`dsh-skill-filesystem` / `dsh-skill` / `dsh-tool-skill` 包 README + web profile 实测），前端决策脚本 python 3.12.8 冒烟实测。
> 前版适配见 `references/zcode-adaptation.md`（v3.4.0-zcode）与 `references/opencode-adaptation.md`（v3.2.0-opencode 历史）。
> v3.6（新增，吸收 dsh-agent-teams）：依赖感知任务图 + durable 邮箱 + 成员 persona + 工具级越权防护 + 磁盘即真相 + 归档化删除 + fail-loud 纪律，详见 `references/agent-teams-absorption.md`。

## 0. 核心结论

team-orchestration 以 **DSH Skill 形态安装**（非 DSH plugin）：它是提示词级编排方法论 + 纯 stdlib Python 决策脚本，DSH 已内置其所需的全部运行时原语（并行子代理、跨代理通信、澄清提问、检查点/续审、批量编排、脚本执行），**无需任何 cordis 插件/工具注入**。安装落点 `~/.agents/skills/team-orchestration`（user-agents 根，rank 500）。

**可见性关键修复**：原 frontmatter 的 `disable-model-invocation: true` 是 ZCode 非官方字段，但在 DSH 是**官方字段**——置 true 会把技能从模型目录彻底排除（模型看不到、无法加载）。适配时已**移除该行**，目录 watcher 触发刷新后技能立即进入模型目录（实测生效）。

## 1. 平台差异对照（DSH 实测）

| 维度 | ZCode (v3.4.0-zcode) | DSH (适配后) |
|------|----------------------|--------------|
| skill 发现 | `~/.agents/skills/`（ZCode 消费） | 根扫描按 rank：项目 `.dsh/skills`(100) → 项目 `.agents/skills`(200) → custom(300) → `~/.dsh/skills`(400) → `~/.agents/skills`(500)；**`<name>/SKILL.md` 即装即用、零构建**；watcher 监听变更，frontmatter 修改即触发目录刷新 |
| frontmatter | 仅 name/description/when_to_use/license/metadata 官方 | 必需 `name`(kebab-case)/`description`；可选 `whenToUse`/`metadata`/`disable-model-invocation`/`user-invocable`；其余键开放解析、无害 |
| 子代理拉起 | `task(subagent_type=...)` | `subagent` / `subagent_fork` 工具（**默认后台运行**）；同一消息多次调用即并行（2-6 个）；fork 继承父会话上下文 |
| 子代理模型/权限 | 仅文件 frontmatter 决定 | 默认继承 main 的 provider/model；DSH `workflow` 工具 `agent()` 可按 `provider`/`model` 覆盖 |
| 子代理产物 | task 返回值 + `agent_*/task.output` | 后台子代理完成通知 + 子代理最终消息（`job_output` 可拉取） |
| 后台送达 | 完成通知，禁止轮询 | 同一口径：后台任务完成即通知，**禁止轮询**；子代理结清后结果随通知送达 |
| agent 间通信 | 主环境 SendMessage(to: agentId)，agent 间直连受限 | `send_message`（仅 **depth-1 直接子代理**可发）；更深层仅可 `interrupt_agent`；主理人铁律「禁止成员直连」天然满足 |
| 澄清提问 | — | `ask_user_question`：一次可问多题、带选项（对应 A 阶段 5W2H，模糊追问 ≤2 轮） |
| 检查点/续审 | `checkpoint_manager.py` + 案卷 `resume_from` | 保留文件检查点协议；可叠加 DSH `goal` 工具（持久目标 + 自动续跑轮次）与持久会话 resume |
| 阶段进度 | — | `todo_write` 结构化任务清单（对应质证/一审/终审阶段进度可见化） |
| 视觉识别 | main（deepseek-v4-flash）不可读图，三路不可用 | main 默认 deepseek-v4-flash 仍 text-only（`read_image` 需模型支持）；DSH 模型池含多模态模型（如 kimi-k3 / mimo-v2.5 / glm-5.2），`workflow` 子代理可指定视觉模型 |
| 脚本执行 | bash 工具 `python scripts/...` | `pwsh` 工具 `python scripts/...`（python 3.12.8 实测，纯 stdlib）；TRIAL_BASE 环境变量保留；归档默认工作区根 `deliverables/trial/...` |
| 触发机制 | description 措辞控制 | `disable-model-invocation`（已移除，恢复模型可见）；`user-invocable` 未设（默认双面可见） |

## 2. 脚本调用方式（DSH）

```powershell
# 在 skill 根目录（或任意工作区，脚本内部按相对自身解析路径）经 pwsh 工具执行
python scripts/task-decomposer.py --task "..." --json
python scripts/expert-matcher.py --task "..." --top-k 4 --json
python scripts/dispatch-planner.py --task "..." --top-k 2
python scripts/trial-court-orchestrator.py docket --issue "..." --roles 3 --out ./docket.json
python scripts/trial-court-orchestrator.py init-learning
python scripts/trial-court-orchestrator.py learning-status
python scripts/asset-resolver.py --snapshot
python scripts/cross-validator.py ...
python scripts/checkpoint_manager.py --root <检查点目录> --action save|load|next|plan
python scripts/token_budget.py --limits '{"举证":12000,...}'
```

> 脚本为**决策参考、非主流程必须**（SKILL.md §9：main 可跳过直接思考）。Windows 下已做 GBK→UTF-8 兼容。
> 注意：DSH 会自动上下文压缩（~80% 阈值），跨轮/跨阶段产物务必落盘（案卷目录），不依赖会话历史留痕。

## 3. 子代理映射（DSH）

| 原概念 | DSH 等价物（实测） |
|--------|-------------------|
| 举证阶段并行子代理 | 同一消息并行 `subagent`（后台默认）；每个 prompt 按 §4 四要素 + A3 JSON 契约 |
| 需要父会话上下文的子代理 | `subagent_fork`（继承已完成轮次上下文，适合质证回灌修订场景） |
| 续接已 spawn 子代理 | 子代理 id + `send_message`（同一会话继续） |
| 质证回灌 | 汇总 B 产物 → `send_message` 回灌各子代理（或 fork 新上下文复核）→ 逐条质证 |
| 后台送达契约/看门狗 | 后台子代理完成即通知；`job_output` 读取结果；**禁止轮询**；绝不因"通知未弹"停在等待态 |
| 大规模 fan-out 自动化 | `workflow` 工具（JS 脚本编排 agent/pipeline/parallel/phase）——可选增强：把 B 阶段并行举证写成 workflow 脚本自动跑 |
| 成员直连 | 受限：`send_message` 仅 depth-1；更深层仅 interrupt——与「禁止成员直连」铁律一致 |

二审终审制对抗流程在 DSH 下不变：A 立案(main 内存) → B 举证(并行 subagent) → C 质证(send_message 回灌 ≤2 轮) → D 一审(main 裁决 → 回灌修订固定 1 轮) → E 二审终审(main 裁断，不回灌)。

## 4. 视觉识别路由（DSH）

与 ZCode 同口径的起点：main 默认 `deepseek-v4-flash` 为 text-only。DSH 下按顺序尝试：

1. **main 直读**：若当前模型支持图像输入（`read_image` 工具可用）→ main 直读即可。
2. **视觉模型子代理**：`workflow` 工具 `agent(prompt, { provider, model })` 可指定多模态模型（settings.yaml 模型池含 kimi-k3 / mimo-v2.5 / glm-5.2 等）；`subagent` 默认继承 main 模型，需视觉时优先走此路径。
3. **外部 OCR/视觉通道转文本**：唯一稳定兜底——图片先转结构化文本再喂子代理（与 ZCode 结论一致）。

**兜底约定**（沿用）：子代理 prompt 不传图片路径，只传「图片的文本化内容」；无法文本化时向用户说明；视觉信息与文字冲突时以直接观察/主证据为准。

## 5. 检查点/断点续审（DSH）

- 文件级检查点（`checkpoint_manager.py` + 案卷 `resume_from`）**原样保留**，跨会话恢复逻辑不变（新会话读 `00-立案/案卷信息.json` → 展示进度 → 从断点继续，不重复 5W2H）。
- **DSH 增强（可选叠加）**：`create_goal`/`update_goal` 把"完成一个案卷"登记为持久目标（含 max_goal_rounds 自动续跑）；`todo_write` 维护阶段清单；DSH 会话本身持久化（`~/.dsh/sessions`），`--resume` 可续同一会话。
- 中断恢复：DSH 侧优先用 goal 工具续跑，文件案卷仍是事实来源（跨运行时通用）。

## 6. 安装落点与可见性（DSH skill 机制）

| 落点 | rank | 说明 |
|------|------|------|
| `~/.agents/skills/team-orchestration`（**现行**） | 500 | 用户级共享技能根，与其余 136 技能同源，已就位 |
| `~/.dsh/skills/team-orchestration` | 400 | DSH 专属用户根，优先级更高；需要时迁移即可（watcher 自动发现） |
| `<项目>/.dsh/skills/` | 100 | 项目级覆盖（按需，一般不需要） |

- **可见性**：frontmatter 移除 `disable-model-invocation` 后，watcher 使目录在**当前会话内**刷新（追加替换目录，实测生效）；重启会话亦可见。
- **更新流程**：Desktop 为源（source of truth），改完拷贝到 `~/.agents/skills/team-orchestration`；DSH 不读 `.skill-lock.json`（那是 agents CLI 的 github 技能锁），目录级拷贝即可。
- **回归门禁**：改本技能逻辑/契约/脚本前仍须先读 `references/test-workflow.md`（§3.1/§4 触发守则），与 ZCode 口径一致。

## 7. 已知差异/限制

- **子代理深度**：DSH web profile 子代理默认 maxDepth=3；审判庭协议只需 main→worker（depth-1），不受影响。
- **上下文压缩**：DSH 约 80% 阈值自动压缩历史——跨轮产物必须落盘案卷，勿依赖对话历史。
- **模型继承**：`subagent` 默认继承 main 模型（当前 text-only）；视觉/强推理任务按 §4 走模型覆盖或外部通道。
- **`version`/`tags` frontmatter 键**：DSH 开放解析、不消费，保留无害。
- **`plugin.json`**：`references/workbuddy-experts/*/plugin.json` 是 WorkBuddy 专家市场元数据，与 DSH 插件无关，勿混淆。
