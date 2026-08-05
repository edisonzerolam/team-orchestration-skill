# OpenCode 适配指南（v3.2.0-opencode）

> 本文件说明 `team-orchestration` skill v3.2.0 在 **OpenCode** 环境下的适配要点。
> 源版本来自 `C:\Users\林昌\Desktop\team-orchestration-skill`（v3.2.0，WorkBuddy 适配版），已针对 OpenCode 二次适配。

## 0. 核心结论

v3.2.0 已导入并完成 OpenCode 适配。所有 Python 脚本可直接通过 bash 工具运行，子代理通过 `task(subagent_type=...)` 拉起。脚本本身**无 WorkBuddy 依赖**（grep 确认无 `~/.workbuddy` 引用），仅 SKILL.md 的 4 处平台说明已替换。

## 1. 平台差异对照

| 维度 | WorkBuddy (原版) | OpenCode (适配后) |
|------|-----------------|-------------------|
| Python 运行时 | 托管 Python | bash 工具调用系统 Python（`python scripts/...`） |
| 子代理拉起 | Agent 子智能体 / background worker | `task(subagent_type="general")`，同一消息多调用即并行 |
| 子代理产物 | `teams/<team>/inboxes/<lead>.json` 收件箱 | `task` 调用返回值（同步） |
| 视觉识别 | main 切换 mimo-v2.5 / `~/.workbuddy/models.json` | main 直读；或 `task(subagent_type="mini-vision")` |
| skill 路径 | `~/.workbuddy/skills/` | `~/.config/opencode/skills/` |
| 归档路径 | `deliverables/trial/`（Workspace） | `skill 内 deliverables/trial/`（TRIAL_BASE 已改） |
| 触发机制 | `disable-model-invocation: true`（user-invoked） | skill 工具手动加载（opencode 无此字段，无害保留） |

## 2. 脚本调用方式

```powershell
# 在 skill 根目录下通过 bash 工具执行
python scripts/task-decomposer.py --task "..." --json
python scripts/expert-matcher.py --task "..." --top-k 4 --json
python scripts/dispatch-planner.py --task "..." --top-k 2
python scripts/trial-court-orchestrator.py docket --issue "..." --roles 3 --out ./docket.json
python scripts/trial-court-orchestrator.py init-learning
python scripts/trial-court-orchestrator.py learning-status
python scripts/asset-resolver.py --snapshot
python scripts/cross-validator.py ...
```

> 所有脚本路径为相对 skill 根目录。`trial-court-orchestrator.py` 已含 Windows GBK 编码兼容（stdout/stderr reconfigure utf-8）。

## 3. 子代理映射

| 原 WorkBuddy 概念 | OpenCode 等价物 |
|------------------|----------------|
| Agent 子智能体（general-purpose） | `task(subagent_type="general")` |
| 专用子代理 | `task(subagent_type="debug-expert" / "code-reviewer" / "researcher-mimo" ...)` |
| 视觉子代理（mimo-v2.5） | `task(subagent_type="mini-vision")`（返回结构化 JSON） |
| 后台 worker + 收件箱 | 无此机制；`task` 同步返回，产物即返回值 |
| SendMessage 回传契约 | prompt 末尾注明"返回结构化 A3 JSON 结果" |

三阶段对抗流程在 OpenCode 下：
```
A 立案(main 内存) ──► B 举证(同一消息多个 task 调用并行) ──► C 质证(再次 task 回灌) + 终审(main 裁断)
```

## 4. 视觉识别路由（OpenCode）

1. **main 直读**：当前模型支持视觉时用 Read 工具直接读图（AGENTS.md「图片委托规则」）。
2. **mini-vision 子代理**：`task({ subagent_type: "mini-vision", prompt: "请分析以下图片，返回结构化 JSON：{file:<图片路径>}" })`。
3. 子代理处理：将视觉结论以文本喂给子代理，避免子代理模型不支持图片。
4. 冲突裁决：以 main 直读观察为准。

## 5. 路径变更

| 原路径 (WorkBuddy) | 当前路径 (OpenCode) |
|--------------------|-------------------|
| `deliverables/trial/`（Workspace 级） | `skill 根/deliverables/trial/`（`trial-court-orchestrator.py` TRIAL_BASE 已改） |
| `references/learning-data/` | 不变 |
| `references/workbuddy-experts/` | 不变（39 团队 199 agents） |

## 6. 快速验证

```powershell
python scripts/task-decomposer.py --task "测试任务" --json
python scripts/expert-matcher.py --task "帮我分析宁德时代" --top-k 3 --json
python scripts/trial-court-orchestrator.py docket --issue "测试" --roles 3 --out $env:TEMP\verify-docket.json
python scripts/trial-court-orchestrator.py init-learning
python scripts/dispatch-planner.py --task "测试" --domains 08-FinanceInvestment --json
```

## 7. 测试与回归门禁

- 修改本 skill 逻辑/契约/脚本前**必先读** `references/test-workflow.md`（回归门禁）。
- 测试目录 `tests/`（9 个文件）覆盖脚本冒烟测试。

## 8. 已知差异（勿误判为 bug）

- `disable-model-invocation: true` 为 WorkBuddy 字段，OpenCode 忽略，无害保留。
- SKILL.md §8 表格中 `~/.workbuddy/models.json` 已移除；模型核对改为「检查 task 工具可用子代理类型」。
- v2.5 时代的 `shared/`、`archive/` 目录已被 v3.2.0 结构替代（备份在 `%TEMP%\opencode\team-orch-v2.5-backup`）。
