# Team Orchestration Skill — 多智能体对抗编排引擎

> **版本**: v3.10.3-dsh（TC-20260816-1 ~ TC-20260816-9 全案迭代）
> **形态**: DSH（DeepSeek Harness）Skill —— 提示词级编排方法论 + 纯 stdlib Python 决策脚本，安装即用、跨客户端适配

多智能体团队编排引擎：对复杂议题组织多视角专家子代理，经**五阶段对抗协议（二审终审制）**——立案 → 并行举证 → 质证 → 一审（回灌修订）→ 二审终审——收敛出高质量结论。40 个专家团队 / 257 个专家人设作为组件池，按任务动态组队，不物理合并。

---

## 核心能力（v3.10.3）

### 1. 五阶段对抗协议（二审终审制）
- **A 立案** → **B 并行举证**（2-6 子代理，A3 单页契约）→ **C 质证**（回灌 ≤2 轮）→ **D 一审**（裁决 + 回灌修订固定 1 轮）→ **E 二审终审**（不回灌，加权投票 believability）
- 规模门 L1-L4 + 降级路径（BATNA）；Effort 分级 token 预算（WARN 80% / BLOCK 100%）
- A3 契约硬键校验（cross-validator --a3）；反盲从义务（自反证/独立证据收敛/主理人不流露倾向）
- 检查点/断点续审（checkpoint_manager + 案卷 resume_from）；提问中转协议（防子代理死锁）

### 2. 依赖感知任务图 + 成员 persona
- 任务状态机（pending→claimed→in_progress→completed|failed|cancelled）+ 依赖门控
- 磁盘即真相、事件仅审计；一主理人一团队；archive-not-delete 归档
- 工具级越权防护（deny 列表：成员不可建团/裁决）；视觉识别路由（外部 OCR 转文本兜底）

### 3. 技能路由（本机 + 多机）
- `asset-resolver.py`：多客户端技能根动态收集（~/.agents/skills、~/.dsh/skills、~/.workbuddy/skills、~/.claude/skills、~/.codex/skills + 项目级）→ 触发词路由（2-gram 中英 + 相关性计分）→ 技能候选注入子代理 prompt（≤5）
- 多机注册表（可选增强）：skill-registry-agent 枚举远程主机技能 → registry 合并（schema 校验防注入）/保鲜检查（7 天）
- SKILL.md §8.2 技能路由表（7 域静态兜底）；敏感技能（disable-model-invocation）自动排除

### 4. 跨客户端首次运行自动适配
- `detect-runtime.py`：环境变量锚 + 目录特征加权判定 DSH / ZCode / OpenCode / Claude Code / Codex / WorkBuddy
- `runtime-adaptation.json` + 各客户端适配文档（dsh/zcode/opencode/claude-code/codex/workbuddy）——装到任何客户端首次触发即自动适配
- **子代理技能面已实测**：DSH 子代理经 available_skills 注入面发现本机技能 + skill 工具按名加载正文（换机即用）

### 5. 专家资产治理（P0-P7 合并方案）
| 阶段 | 内容 |
|------|------|
| P0 | 基线（安全扫描 / 邮箱脱敏 / git 血缘） |
| P1 | 占位 id 语义化（56 member-N → slug，11 团，三向校验） |
| P2 | 共享人设裁决（TF-IDF 指纹 + 人工裁决；_shared 规范层 + 引用校验） |
| P3 | 指纹索引（expert-fingerprint：字符 3-gram TF-IDF cosine + 停用词归一化） |
| P4 | 域归组（domain-map.json：13 categoryId → 10 组，40 团全覆盖）+ _domain 域入口 |
| P5 | 路由治理（expert-matcher --domain 域限域召回） |
| P6 | 生命周期（merge-history 血缘 + git revert 回滚 SOP） |
| P7 | eval 门禁（eval-gate：22 样例基线 72.7%，合并后下降 >5% 即撤销） |

### 6. 决策脚本体系（21 个 .py，纯 stdlib）
- **前端**：task-decomposer（复杂度/派数）/ expert-matcher（团队召回，--domain 限域）/ dispatch-planner（派工+立场推导）/ asset-resolver（技能路由）/ expert-fingerprint（相似度）
- **审判庭后端**：trial-court-orchestrator（案卷/归档/自学习）/ cross-validator（A3 硬键+交叉验证）/ checkpoint_manager / token_budget / concurrency_check / cycle_detector / auto-decider / self_heal / health-monitor / self_learning / check_agent_completeness / check_team_consistency / check-shared-refs / eval-gate / skill-registry-agent / detect-runtime + self-evolution 三件套
- Windows GBK 控制台防护全覆盖（stdout UTF-8 reconfigure）；原子写（tmp+rename）；路径白名单防穿越

### 7. 安全边界
- 敏感技能准入（disable-model-invocation + 准入须知：对外发布/凭据/登录态动作须用户逐项确认）
- 远程注册表 schema 校验（防提示注入）；命令注入面为零（subprocess 全列表传参）
- 案卷隔离（deliverables 不入带 remote 的 git 仓库）

---

## 快速开始

```bash
# 安装（任选其一）
# 1. 拷贝到技能根
cp -r team-orchestration ~/.agents/skills/
# 2. 或直接 clone 本仓库到技能根
git clone https://github.com/edisonzerolam/team-orchestration-skill ~/.agents/skills/team-orchestration

# 首次运行自动适配当前客户端
python scripts/detect-runtime.py

# 立案资产路由（技能候选注入子代理）
python scripts/asset-resolver.py --task "做一次竞品分析"
python scripts/asset-resolver.py --snapshot

# 团队匹配
python scripts/expert-matcher.py --task "审一份劳动合同" --domain legal --top-k 3
```

触发词：组建团队、团队协作、需要团队、build a team、找合伙人、组成专家小组。

## 版本历史
- **v3.10.3**（2026-08-16）：技能路由（双多根+触发词）、跨机器注册表、跨客户端自动适配、专家合并 P0-P7 全案、完整功能测试与代码审计（3 阻断 + 12 严重修复）、安全边界（browser-cdp 下架/邮箱脱敏/案卷隔离）
- **v3.9.0-dsh**：动态派数（TC-20260816-6）、数据来源矩阵、任务级 Skill 封装（skills-pack）
- **v3.5.0-dsh**：DSH 适配基线、加权投票、回退重审契约、检查点续审

## 许可证
MIT（见 LICENSE）。专家人设资产（references/workbuddy-experts/）来源标注见各 plugin.json `_source` 字段。
