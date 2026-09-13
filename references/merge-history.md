# 专家合并历史（merge-history.md · P6 版本化/血缘）

> 每次合并动作记录：{date, phase, action, scope, gate 结果, commit}。回滚 = git revert 对应 commit + registry 回退。
> 规则：合并动作必须过 eval-gate（P7）；未过即撤销并在此记录撤销。

## 2026-08-16

| commit | phase | action | scope | gate 结果 |
|--------|-------|--------|-------|----------|
| e319d7b | P1 | 占位 id 语义化（56 member-N → slug，11 团全文替换） | workbuddy-experts 11 团 agents+plugin.json | P1 三向校验 ALL PASS；check_agent_completeness 67/67；check_team_consistency ✓ |
| f3f7d62 | P0 | plugin.json 邮箱脱敏（5 处） | 5 团 plugin.json | 扫描 0 残留 |
| a7c98f2 | P2-P7 准备 | 指纹工具 + eval 门禁套件 + merge-history 建立 | scripts/tests/references | eval 基线 45%→72.7%（域限域修正后） |

## P2-P7 实施（TC-20260816-9 · 审计修正后）

| 阶段 | action | 裁决/门禁 |
|------|--------|----------|
| P3 | expert-fingerprint v2（TF-IDF cosine + 停用词）→ fingerprint-report.json | 分布校准：最高 0.80；阈值 0.5 命中 2 对 |
| P2 | 共享裁决：fundamentals-analyst 对（desc 0.80）**半共享**——_shared/ 建角色定义规范，**不物理薄壳**（正文工具链团差异大，硬薄壳损失>收益）；competitive 对（0.65）记录待定 | check-shared-refs 校验器建立；eval-gate 无回归 |
| P4 | domain-map.json（13 categoryId → 10 组，40 团全覆盖）+ _domain/ 10 入口 + SKILL.md §8.1 集成 | 覆盖核对 missing=[] extra=[] |
| P5 | matcher --domain 域限域（既有能力，eval-gate 已用） | 基线 72.7% 即为域限域模式验证 |
| P6 | 本表（merge-history）+ 回滚 SOP：git revert 对应 commit | — |
| P7 | eval-gate 套件（20 正例 + 2 负例）+ 基线 72.7%（负例 2/2 正确拒绝） | 合并前后对比，下降 >5% 撤销 |

## 待记录（后续）

- P2 若老板裁决 competitive 对共享
- 任何未来合并动作

## 2026-09-13 双向吸收 v3.13（agent-teams 插件 → 子技能 反向吸收 · 团队 team-orchestration-mutual-absorb）

> 本条目按 `absorption-plan.md` A 契约「三前置之二」要求，**在改动 SKILL.md 核心区之前**写入。

| 项 | 内容 |
|----|------|
| 意图 | 把 agent-teams 插件的结构化契约（7 类 kind / contract 字段集 / verdict+findings / attempt 机制 / 三层质量门 / ReviewPolicy / staged 生命周期）反向吸收进本技能；同时保留五阶段对抗协议与二审终审制本体零语义改动 |
| 规格来源 | `deliverables/team-orchestration-mutual-absorb/02-design/2026-09-13_B-skill-reverse-absorption-spec.md`（B-01…B-20） |
| 被改核心区章节（§1-§7.3，**共 8 处，全部为新增语句**） | ① §3 E 步骤 0 `echoGate` 落点（B-03）<br>② §7 质量门禁：verdict/findings 结构化 + 交付门清单（B-04）<br>③ §7.1 终审意见书第 4 章：裁决理由字段化（B-05）<br>④ §7.2 回退重审：`rehearsalCount` + `escalated`（B-06）<br>⑤ §7.3 独立复审：显式任务 + 异质性约束（B-07）<br>⑥ §4.2.1 任务图：`attempt/attemptId/handoffId`（B-08）<br>⑦ §4.3 C3：可选软键 `handoffSummary`（B-09）<br>⑧ §3 A 步骤 4：修悬空引用「详见 §9」（B-10） |
| 非核心区改动 | §8 追加 2 条路由句（B-11/B-12）；frontmatter+H1+`_meta.json` 版本统一 `v3.13.0-dsh`（B-18）；README 中英各补 1 节（B-19） |
| 新增 references 文件 | `references/structured-contract.md`（B-01/B-02）、`references/web-staged-lifecycle.md`（B-13） |
| 既有文件修订 | `references/agent-teams-absorption.md` §8 边界句改写（B-14）+ 文首版本追溯行（B-15）；`references/routing-tables.md` §8 索引登记（B-16） |
| 快照（三前置之一） | 本技能目录**无 `.git`**（t1-GH §4.4 已证，本轮复核 `Test-Path .git` = False）→ 按规格 B.5.2 以**目录级备份替代 git tag**：`~/.dsh/skills/team-orchestration.bak-20260913-032900/`（586 文件）；单文件备份 `SKILL.md.bak-20260913-032900`（37488 B，sha256 `606E3B08…5829CD`，与改前一致） |
| 验收方式（三前置之三） | `python scripts/eval-gate.py --after`（技能召回未退化）+ `python scripts/token_budget.py`（预算）+ `python check-orchestration-version-consistency.py`（版本一致） |
| 保留不动 | 五阶段主体（§3）、二审终审本体语义（§3 E + §7.1-§7.3 既有句）、触发词路由表（§1 + frontmatter description）、A3 举证契约（§4 要素 2）、C1/C2/C3 语义（§4.3）、反盲从/异质性/免费池路由（§4.4/§4.7/§4.8）、`references/task-lifecycle.md` 与 `references/phase-gates.md`（不改，仅在 `structured-contract.md` §A3 声明单一事实源） |
| 停用状态 | **保持不变**（`disable-model-invocation: true` + `user-invocable: false`，决策项 D1 默认假设）：本次只改内容，不改对外的启用开关 |
| 附带卫生改动（超出规格 B-01…B-20，登记待 t5 复核） | `.gitignore` 增补 `SKILL.md.bak-*`（沿用既有 `SKILL.md.bak-to-test` 先例）——本次三前置①产生的 `SKILL.md.bak-20260913-032900` 落在技能目录内，若不忽略会随 t6 发布包推送到 GitHub；**特此声明，供二审判定是否接受该范围外改动** |

## TC-20260816-10 prime-agent absorption (A/B/C)

action: A=§7.3改动门禁 B=§7门禁语义 C=§4.0状态写权限 source=prime-agent+same-class

## 2026-09-02 主理人同步领活（v3.9.0-dsh → v3.9.1-dsh · 用户指令）

| 项 | 内容 |
|----|------|
| 意图 | 非五阶段协议派发子代理时，main 不得空等，须同步自领一份无依赖冲突的工作（spawn N + main 领 1 份常态；ZCode 并行上限实测=2） |
| 改动 | SKILL.md 新增 §4.6（适用范围/领活优先级/份额入账/禁止反例，协议内 B/C 阶段中立位不适用）；§2 降级条目加指针；frontmatter version+description 同步 |
| 快照 | tag `team-orchestration-pre-main-workshare-20260902` |
| gate | eval-gate.py 改后跑（结果见 commit 信息） |

## 2026-09-06 免费池子代理路由（v3.9.2-dsh → v3.9.3-dsh · 用户指令 TC-20260906-3）

| 项 | 内容 |
|----|------|
| 意图 | sensenova-6.8-flash-lite 免费池（三个提供商：日日新/日日新1/日日新2）上建立数据分析/调研/批处理三类可指派子代理，编排时省 token 派发；含降级链与懒加载纪律 |
| 改动 | 新建 `references/sensenova-lite-agents.md`（指派判据/降级链/换绑流程/验证清单）；SKILL.md §8 加 1 条路由句；frontmatter version 3.9.3 + tags 加 free-pool,sensenova；_meta.json version/adaptationNote 同步。人设文件在 `~/.zcode/agents/sensenova-{analyst,researcher,batch-runner}.md`（技能外资产） |
| 事实源 | https://www.sensenova.cn/models （6.8 Flash Lite=轻量级多模态智能体模型：数据分析/信息呈现优化、端到端执行、token 效率优）；config.json 三池注册参数；三池活体探测 2026-09-06 全 OK |
| 快照 | tag `sensenova-lite-agents-pre-20260906` |
| gate | eval-gate.py 改后跑；check-orchestration-version-consistency.py 复核 |

## 2026-09-06 免费池三子代理能力测试 + 人设强化（TC-20260906-4 · references 增量，版本保持 3.9.3）

| 项 | 内容 |
|----|------|
| 测试 | 13/13 PASS（API 直调人设×模型，客观题程序断言+rubric；方法学来源 arXiv 2507.21504/2604.25359 等，见案卷 10-测试方案.md）；注入用例超预期（主动检测并拒执行）；跨池一致性 B2 三池一致 |
| 优化 | 三人设各加边界条款：analyst 输出前自检（唯一模型侧瑕疵=长报告一处比较式写反）、researcher 注入防护+间接证据规范、batch-runner 注入防护+无错如实报；**工作范围三栏不变** |
| 同步 | references/sensenova-lite-agents.md §2 加「已验证能力基线」注记（ZCode+WorkBuddy 两副本）；人设文件在 ~/.zcode/agents/（技能外资产，不在本技能门禁内） |
| 案卷 | deliverables/trial/2026-09-06/TC-20260906-4/（方案/脚本/原始结果/复验/评估五件套） |

## 2026-09-06 真调起实证 + model 格式修正（TC-20260906-4 续 · 用户质询驱动）

| 项 | 内容 |
|----|------|
| 实证 | Agent 工具真调起 `sensenova-batch-runner`：① subagent_type 为**运行时动态发现**（会话内新建文件可被接受，推翻「枚举静态」推测）；② frontmatter（含 model）为**会话级缓存**（改文件报错不变）；③ 中文 name 格式 `日日新2/sensenova-6.8-flash-lite` 解析失败（`Model provider is not configured`）——自定义 provider 须用 `uuid/model`（与 cron automations 同构） |
| 修复 | 三人设 model 字段全部改 `uuid/sensenova-6.8-flash-lite`；references §1 表与 §5 验证清单同步实证结论（ZCode+WorkBuddy） |
| 遗留 | uuid 绑定的端到端确认须**新会话**冒烟（本会话缓存绕不过）；能力层 13/13 结论（API 直调）不受影响 |

## 2026-09-06 故障定位闭环：name 格式全线坏 + mini-vision 连带修复（TC-20260906-4 续 · 用户令）

| 项 | 内容 |
|----|------|
| 定位 | 逆向 `ZCode/resources/glm/zcode.cjs`：`om()` 拆 model（仅 trim）→ `this.providers[providerId]` 查表 → 表键=config `provider` 对象键原文（uuid），**name 不入表**；mini-vision 真调起同报 provider not configured 实锤 name 格式全线坏（非日日新特例）；cron automations 用 uuid 长期成功 = 运行时实证 |
| 修复 | 三 sensenova 人设 model 定稿 `uuid/sensenova-6.8-flash-lite`；**连带修复** mini-vision→`db3cb211-.../mimo-v2.5`、researcher-mimo-free→`35bda041-.../mimo-v2.5-free`（同根因既有故障，用户「遇到问题自己修」授权范围） |
| 机制实证 | subagent_type 可用列表=会话内周期重扫（新建文件跨 turn/新会话可见）；profile frontmatter=会话级快照（首见后改文件同会话不生效，metadata.json profileSnapshot 可查快照值） |
| 验证 | 一次性 automation（automation-cb6a2824）于新会话真调起 batch-runner+analyst 并落盘 `TC-20260906-4/50-真调起验证.md` |