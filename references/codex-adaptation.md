# OpenAI Codex 适配指南（v1.0 · TC-20260816-7/8）

> 本文件说明 `team-orchestration` skill 在 **OpenAI Codex** 环境下的适配要点。
> 检测：`scripts/detect-runtime.py` 判定 `codex` 后自动加载本文件（见 `references/runtime-adaptation.json`）。

## 0. 安装形态

- 技能以目录拷贝 + AGENTS.md 引用形态安装：把 team-orchestration 放入 `~/.codex/skills/` 或项目目录；Codex 以 AGENTS.md 为上下文锚点，SKILL.md 按需引用
- 技能根：`~/.codex/skills/`——asset-resolver 多客户端根已覆盖（source=codex）

## 1. 平台差异对照

| 维度 | Codex | team-orchestration 适配 |
|------|-------|------------------------|
| 子代理拉起 | 内置 subagent 机制（可并行） | B 阶段并行举证：并行 subagent |
| 子代理技能 | 子代理上下文独立；技能经 AGENTS.md/CLAUDE.md 引用链可见 | 子代理 prompt 注入技能候选清单（§4-3） |
| 通信 | 无跨 agent 消息（产物经文件） | 质证回灌：main 汇总后重派子代理 |
| 澄清提问 | 交互式确认（CLI） | 5W2H 追问 ≤2 轮；子代理 questions 软键中转 |
| 检查点 | 无内置 | `scripts/checkpoint_manager.py` + 案卷 resume_from |
| 脚本执行 | bash | `python scripts/...` |
| 视觉 | 多模态模型或外部 OCR | 外部 OCR 转文本兜底 |
| 磁盘真相 | 工作区文件系统 | 案卷落盘 `deliverables/trial/...`；TRIAL_BASE 覆盖 |

## 2. 已知差异

- Codex 子代理工具面与 main 可能不同（以实际注入为准）：技能候选注入 prompt 即"preloaded"语义
- 无 `send_message`：质证轮次 = main 汇总 → 重派子代理（携带他方摘要）
- 输出 A3 JSON 需显式要求（Codex 倾向自然语言输出）；C3 schema 校验（cross-validator --a3）为强制门

## 3. 验证

- `python scripts/detect-runtime.py` 应判定 `codex`
- `python scripts/asset-resolver.py --task "<任务>"` 应召回 `~/.codex/skills/` 技能（source=codex）
