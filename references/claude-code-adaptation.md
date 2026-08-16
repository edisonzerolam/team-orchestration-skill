# Claude Code 适配指南（v1.0 · TC-20260816-7/8）

> 本文件说明 `team-orchestration` skill 在 **Claude Code** 环境下的适配要点。
> 检测：`scripts/detect-runtime.py` 判定 `claude-code` 后自动加载本文件（见 `references/runtime-adaptation.json`）。

## 0. 安装形态

- 技能以 **CLAUDE.md 引用 + 目录拷贝** 形态安装：把 team-orchestration 目录放入 `~/.claude/skills/` 或项目 `.claude/skills/`；Claude Code 的 skills 机制（`#!` 头）与 CLAUDE.md 均支持按需引用
- 技能根：`~/.claude/skills/`（用户级）与 `<项目>/.claude/skills/`（项目级）——asset-resolver 多客户端根已覆盖

## 1. 平台差异对照

| 维度 | Claude Code | team-orchestration 适配 |
|------|-------------|------------------------|
| 子代理拉起 | `Task` 工具（子代理，可并行多条） | B 阶段并行举证：同一消息多条 Task |
| 子代理技能 | 官方称子代理不继承 skills；实测可经 filesystem 发现项目技能 | 子代理 prompt 注入技能候选清单（§4-3）；候选外不调用 |
| 通信 | 无跨 agent 消息（产物经文件/返回值） | 质证回灌：main 汇总后重派 Task 或 fork 新子代理；无 send_message 等价物 |
| 澄清提问 | `AskUserQuestion` 工具 | 5W2H 追问 ≤2 轮；子代理 questions 软键由 main 中转 |
| 检查点 | 无内置 | `scripts/checkpoint_manager.py` + 案卷 resume_from（文件级，跨会话） |
| 脚本执行 | bash | `python scripts/...`（python3 需可用） |
| 视觉 | 多模态模型或外部 OCR | 外部 OCR 转文本兜底（与 DSH 同口径） |
| 磁盘真相 | 工作区文件系统 | 案卷落盘 `deliverables/trial/...`；TRIAL_BASE 环境变量可覆盖 |

## 2. 已知差异

- Claude Code 的 skills 以 `SKILL.md` 为单文件格式，正文引用外部文件需相对路径；本技能目录完整拷贝后相对引用不变
- 无 `send_message`：质证轮次通过"main 汇总 → 重派 Task（携带他方摘要）"实现，注意子代理上下文不延续（每次 Task 独立）
- `ask_user_question` 等价物为 AskUserQuestion；子代理禁止提问（防死锁，同 DSH 口径）

## 3. 验证

- `python scripts/detect-runtime.py` 应判定 `claude-code`
- `python scripts/asset-resolver.py --task "<任务>"` 应召回 `~/.claude/skills/` 技能（source=claude）
