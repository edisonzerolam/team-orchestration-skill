# team-orchestration 回归测试工作流（选择性加载模块 · 现行）

> 适用范围：team-orchestration 技能（v3.4.0-zcode）。当有人对该技能做**改进 / 修改 / 调整 / 优化**任一操作后，须执行本回归测试工作流，验证改动未破坏原有功能。
> 模块性质：**选择性加载**，封装于 `references/test-workflow.md`；默认不加载，按需读取。本草案即该模块的源稿。
> 依据：本对话两次真实演练暴露的问题清单 `to-test-module/dialogue-facts.md`（F1-F5）+ 技能现存契约（SKILL.md / cross-validation.md / phase-gates.md / team-setup.md / task-lifecycle.md）+ 既有自动化测试 `tests/run_smoke.py` 与 `tests/test_*.py`。
> **v2 修正记录**：本版依据 team-lead 审阅已落实 3 处必改（A1 触发判据分层、B2 去除 L4 档位并将深度档归入 cross-validation、选择性加载 step-0 自检 + §8 强约束索引）与 4 处建议（fixtures 数据源 / 报告单一路径 / B6 六段式内联 / step0 环境具体值 + 无 git 基线）。

---

## 0. 设计目标与既有测试边界（先认清现状，避免重复）

既有 `tests/` 已覆盖：
- `run_smoke.py`：遍历所有 `test_*.py` 的冒烟运行器，无 pytest 依赖，退出码 0/1。
- `test_file_health.py`：全包 UTF-8 健康扫描（严格解码 / 无 U+FFFD / 无单行超长 / 无 mojibake）。
- `test_references.py` + `check_references.py`：本地引用完整性（references/ scripts/ tests/ 死链检测）。
- `test_task_decomposer.py` / `test_expert_matcher.py` / `test_dispatch_planner.py`：三个**前端脚本**的分层/选专家/派工/A3 交付模板字段断言。
- `test_trial_court.py`：审判庭后端脚本（案卷生成 / 归档 / 自学习初始化 / 二审终审制：一审判决书模板、回灌修订 prompt）冒烟。

**回归模块与既有测试的分工**：
- 既有测试 = **脚本层自动化（白盒、静态、确定性）**，改动后跑 `run_smoke.py` 即有数值结果。
- 本模块 = **编排行为层回归（黑盒、协议、端到端）**，覆盖脚本测试捕获不了的运行时编排语义：五阶段是否照跑（二审终审制：一审裁决→回灌修订→二审终审）、A3 契约是否遵守、TeamCreate 切换任务列表、后台送达契约、终审门禁、归档元数据、视觉路由等。
- 二者互补：本模块把 `run_smoke.py` 作为 step 1 前置检查；脚本测试通过才进入行为级回归。

---

## 1. 测试团队组建

### 1.1 最小测试团队（依据对话参与者派生）

| 角色 | 来源对话原型 | 职责 | 主要产出 |
|------|--------------|------|----------|
| **测试主理人 lead** | team-lead | 主持全流程：立项、拆争点、按章节调度、汇总裁决、给每用例判 PASS/FAIL | `deliverables/to-test-module/regression-report.md` 全量报告 |
| **运行时执行者 runner** | 对话里实际并行 worker | 依指令触发被测功能（跑 SKILL.md 流程 / 脚本 / 后台 worker），记录运行时证据 | 每用例触发记录 + 运行日志 |
| **独立复核者 designated** | 对话里"独立子代理（全新上下文）" | 用全新上下文复核 runner 自报结论，不采信自报；专揪统计误判/造证据（F1/F2 防线） | 独立复核意见（A3 或表格） |
| **报表汇总员 reporter** | 对话里日志/汇总表重写者 | 规范化日志、汇总通过/失败、统计每用例结论，生成可复现报告 | regression-report 汇总、pass 计数 |
| **环境守护者 env-guard** | 对话里"环境守护"意识 | 核对解释器 / 工作区路径 / Git Bash heredoc 陷阱 / 归档落盘 / inbox 目录可写 | env-check.log、环境基线快照 |

### 1.2 按需组建与缩减原则

- **默认 3 人即可跑通全链路**：lead（主理人）+ runner（执行）+ designated（独立复核）。reporter 与 env-guard 可由 lead 兼任（单人小改可缩减）。
- **必须保留独立复核角色**：F1 教训是"worker 自报不可信"。若让执行者自己判自己通过，等于复刻 bug。配不了独立复核者时，lead 至少另起全新上下文抽查最薄弱证据。
- **可缩减**：纯静态小改（仅文档措辞）用 `最小冒烟`（见 §4.3），单 lead 一人跑 run_smoke + 引用检查即可，不组团队。
- **可扩编**：涉及多领域/高争议改动（改了五阶段或 A3 契约），扩到 4-6 人多分支并行；独立复核者单独全新上下文，不与 runner 共享。
- **角色隔离纪律**：禁止 runner 兼任自身用例的 designated；designated 必须全新上下文、看不到 runner 过程，只给结论与证据。

---

## 2. 测试工作流设计（三类维度）

### 2.A 核心功能点测试（对应技能功能分层）

逐条执行 SKILL.md 功能分层：规模门 → 五阶段/直行 → 角色分配 → 合并策略 → 质量门禁 → 归档。

| 编号 | 功能点 | 步骤（谁做） | 判定标准（通过判据） |
|------|--------|--------------|----------------------|
| A1 | **触发条件与规模门** | runner 构造低复杂度（应直行）与高复杂度（应五阶段）两用例；lead 核对分层判定 | 分层判定：**先判触发面**——SKILL.md §1"①>1 子代理 ②main+子代理协作 ③多角度执行"任一满足→走五阶段（二审终审制），都不满足→直行；**再判规模面**——§2 阈值 L1/L2→直行深度、L3+→五阶段深度。冲突仲裁：**若触发面命中的场景同时落在规模面 L1/L2（低复杂但仍多视角），以触发面优先走五阶段**（多视角仍须对抗，深度可按规模面收缩）。 |
| A2 | **五阶段流程（二审终审制）** | runner 走 立案→并行举证→质证→一审(裁决+回灌修订)→二审终审；lead 核对顺序 | 严格 A→B→C→D(一审)→E(二审终审)；无跳阶段（§7 铁律）；一审回灌修订固定 1 轮（含判决书+他方产物）、二审终审不回灌。**回退重审判据（v3.5 · P0-1）**：若某子争点触发裁决偏差回退重审，不破坏阶段顺序——回退仅重做 main 侧独立裁决（**不重新回灌子代理**，不追加质证轮次），完成后仍按 D(一审)→E(二审终审) 顺序推进；同一子争点回退 ≤1 次，重审次数写入案卷 `cross_exam` 字段 |
| A3 | **直行与自动切换** | runner 先直行，中途复杂度升 L3 | 升级触发自动切换，不卡在单 agent |
| A4 | **降级路径** | runner 尝试组团队但无法确认 2+ 差异化视角 | 按 §2 降为单 agent+自我批判，不硬凑团队（无假团队） |
| A5 | **角色分配** | runner 按争点数选 2/3/4-6 角色 | 角色数匹配 §6 表格；专业视角差异化（非重复角色） |
| A6 | **合并策略** | 构造封闭题（投票制）+ 开放题（辩论制） | 封闭题多数采信+少数留痕；开放题 main 综合采信并逐条给理由 |
| A7 | **质量门禁** | 二审终审后 lead 核对 §7 铁律 + §7.1 五章节 + phase-gates G1-G5 | 无代写/跳阶段/直连；可信度=最薄弱证据；意见书章节齐全；一审判决书已作中间产物归档 |
| A8 | **归档** | runner 触发归档，lead 核对落盘 | 产物在 `deliverables/trial/YYYY-MM-DD/<docket_id>/final-verdict.md`（二审终审意见书），docket_id=TC-YYYYMMDD-N；一审判决书在 `03-一审/first-instance-verdict.md`；异步不阻塞 |
| A9 | **二审终审制专项** | runner 走 一审裁决→回灌修订→二审终审 全链 | 一审判决书为中间产物（落盘+流程中展示摘要，不单独交付）；回灌修订固定 1 轮、不因收敛提前；二审终审意见书为终局交付且不再回灌；二审不引入新论点 |

### 2.B 关键代码路径与边界条件测试

| 编号 | 关键路径 / 边界 | 步骤 | 判定标准 |
|------|----------------|------|---------|
| B1 | **L1 直行 与 L3 五阶段 切换边界** | runner 从子任务≤3 增至 ≥4、或维度由单转多 | 恰在 L1→L3 阈值切换，不早不晚；切换后走对应流程 |
| B2 | **规模门阈值（L1/L2/L3）** | runner 构造复杂度 1/2/3 三档 | **规模门只有 L1 / L2 / L3+，无 L4 档**。按门：L1 直行、L2 可直行、L3+ 五阶段。测试某档时的"验证深度"单独按 `references/cross-validation.md` 的四档（skip/light/standard/deep，映射复杂度 1-4）选取，**勿把 deep 深度档当规模门档位**。注（v3.9 · TC-20260816-6）：`task-decomposer` 的 `L4-深度` 为 cross-validation 深度档标签（非规模门档位），与本判据不冲突 |
| B3 | **降级路径（无法定视角）** | runner 给"无法确认 2+ 差异化视角"输入 | 单 agent+自我批判；不 stub 假角色；降级被显式记录 |
| B4 | **升级路径（L2 跨 ≥3 领域）** | runner 构造 L2 但覆盖 3 领域 | 升为 L3，不留在 L2 直行 |
| B5 | **A3 JSON 完整性** | runner 让每子代理输出，校验器逐字段断言 | 每 A3 含 role/artifacts{conclusions,evidence,risks,actions}/confidence/uncertainties；非空、类型对、无缺键 |
| B6 | **终审七段式** | runner 走 `references/trial-court-protocol.md` §7.2 七段终审；lead 逐段核对 | 判据"七段齐全" = 一段 案卷信息 / 二段 争点回顾 / 三段 质证与一审修订记录 / 四段 逐条裁决 / 五段 终局结论 / 六段 存疑遗留 / 七段 资产使用评价；七段齐全、顺序对、段四逐条裁决含理由、段三记录质证轮数+回灌修订轮、段七记录资产使用；禁止引入新论点（定位：trial-court-protocol.md §7.1） |
| B7 | **并行 worker spawn 上限/收敛** | 同时 spawn 2-6 子代理 | 数量在区间；全部被 TaskCreate 登记；并发产出且质证不缺件 |

### 2.C 与团队成员 / 工具的集成点测试

| 编号 | 集成点 | 步骤 | 判定标准 |
|------|--------|------|---------|
| C1 | **TeamCreate 切换任务列表** | runner 建团队，观察任务列表 | TeamCreate 后任务列表切到团队目录；原列表被隔离（不混）；可切回 |
| C2 | **后台送达契约（ZCode）** | spawn 后台 worker（`background: true` / `run_in_background`），结束时回传 A3 | 判完成**以 task 返回值 / 完成通知为准**（ZCode 无 inbox 文件机制），不看实时消息流；prompt 末尾注明"返回结构化 A3 JSON 结果" |
| C3 | **TaskOutput 看门狗** | 设 5 分钟超时（建议），超时主动 TaskOutput 拉取 | 不无限等消息流；超时兜底能取到产物；无假停滞 |
| C4 | **run_smoke.py** | runner 在 env-guard 核对后执行 | `python tests/run_smoke.py` 退出 0，全 PASS，无 LOAD-FAIL |
| C5 | **引用完整性 + 文件健康 + 乱码检出** | runner 执行 test_references / test_file_health；对 references/ 做 mojibake 标记扫描 | check_references 无死链（退出 0）；test_file_health 全包 UTF-8 健康。**乱码检出用例（v3.5 · P0-2 先修门禁）**：显式扫描 references/ 下 mojibake 标记——① 出现 `鈫?` / `鈥?` / `鈹?` / `鈿?` 等 UTF-8→GB18030 错位字符（密度异常）即 FAIL；② 半角 `?` 替字密度异常（连续段落丢失字尾，参照 task-lifecycle/communication 曾乱码的 `?` 全表）即 FAIL；③ 该断言存在即可检出——确保以后乱码文件会被回归检出（F5 教训延伸） |
| C6 | **MCP / 连接器 / 技能资产注入** | 立案阶段选取可用资产并注入子代理 prompt | 资产真实注入（出现在 A3 的 tools/actions）；可调用；失败有兜底说明 |
| C7 | **视觉路由（ZCode 统一口径）** | 含图像子代理场景 | **三路运行时不可用 + 外部 OCR 通道兜底**（v3.5 统一口径，与 SKILL.md §4.1、zcode-adaptation.md §4 一致）：① main 直读失败（Media omitted，text-only）；② mini-vision 子代理类型运行时不可调用；③ 子代理继承 main 的 text-only 模型 → 视觉任务走外部 OCR 转文本喂子代理；不硬调不存在的模型/类型 |

---

## 3. 模块化集成（选择性加载）

### 3.1 step-0 触发自检清单（固化于模块顶部，必读）

> 由于 SKILL.md §8 只是声明性索引（加一行 main 不会主动读），**本模块必须在自己顶部固化一段显式 step-0 自检清单**，作为实际触发门禁（替代"假想的自动加载"）：

```
step-0 触发自检（在读取本文件后立刻执行）：
  改动命中【逻辑/契约/脚本/.json】→ 强制先读本文件并按 §5 全量回归
    命中面：SKILL.md 触发/规模门/五阶段/A3 契约/角色分配/合并策略/门禁/归档
            references/trial-court*、cross-validation、phase-gates、team-setup、task-lifecycle
            scripts/*.py、config.yaml、models.json、_meta.json
  仅改文档格式/措辞（不动逻辑/契约/字段）→ 最小冒烟
    （跑 tests/run_smoke.py + tests/check_references.py）
  无改动 / 不影响本技能 → 不加载，走正常主流程
```

### 3.2 封装形态

- 本模块作为 **`references/test-workflow.md`** 独立文件存在，完整承载 §2/§4/§5/§6 全部内容，并以 §3.1 的 step-0 自检清单开头。
- `SKILL.md` **只在 §8 参考索引表加一行**，且"用途"栏**加粗写强约束**：`| references/test-workflow.md | **改本技能逻辑/契约/脚本前必先读，作为回归门禁** |`——让该索引行成为强约束而非普通索引项。
- **不写入 SKILL.md 主流程**：五阶段、A3 契约、规模门等正文一律不动，避免测试逻辑污染生产主流程。
- 同样不进入触发段、规模门、质量门禁等任何执行逻辑引用。

### 3.3 加载方式（关键）

> **加载方式**：本模块**默认不加载**。加载由 §3.1 step-0 自检清单驱动，**而非**依赖 §8 索引自动拉取（索引只是提示入口）。仅当自检判定"改动命中逻辑/契约/脚本/.json"时，main 读取 `references/test-workflow.md`，按其 §2/§5 组织一次回归测试。

- 自检为 `强制回归` → lead 读取本文件 → 按 §5 执行步骤序列 → 产出验收清单。
- 自检为 `最小冒烟` → 仅跑 run_smoke + 引用检查。
- 自检为 `不加载` → 不读取，走正常主流程。
- 副作用为零：不读它不影响任何正常编排行为。

### 3.4 为何选择性加载（不塞进主流程）

1. **解耦**：测试工作流运行开销高（组独立复核、跑端到端），常驻会拖慢每次正常编排。
2. **可维护**：测试模块独立演进，不牵连生产五阶段版本。
3. **防互相污染**：主流程若被测试逻辑引用，改生产代码会误触断言，产生假阴/假阳。

---

## 4. 触发时机

### 4.1 触发总入口：复用 §3.1 step-0 自检清单

正式触发判定统一走 §3.1 的 step-0 自检：先看改动命中面，再落到下三级处理（强制回归 / 最小冒烟 / 不加载）。下表给出命中面的具体识别依据。

| 操作类型 | 例子 | 触发词 / 判断 | 归属处理 |
|----------|------|---------------|----------|
| **改进 / 增强** | 新增某阶段能力、优化质量门禁、扩充合并策略 | 用户/lead 说"改进""增强""提升""优化技能" | 强制回归 |
| **修改 / 调整** | 改五阶段顺序、调规模门阈值、改 A3 字段、改角色分配 | "改""调整""变更""编辑""重构" 结合技能文件 | 强制回归 |
| **Bug 修复** | 修复 F1-F5 任一 | 明确"修 bug""修复""解决回归问题" | 强制回归 |
| **文件级触发** | 技能目录 .md（自有逻辑）/ .py / .json（config.yaml、_meta.json）被改 | 检测到 `~/.agents/skills/team-orchestration/**` 变更 | 强制回归 |
| **git 触发** | git diff 检测新旧差异 | `git diff` 有实质输出指向技能内容 | 强制回归（无 watcher 时由人工比对 git diff 生效） |
| **文档格式微调** | 仅排版/措辞，不动逻辑/契约/字段 | 无逻辑/契约/字段改动 | 最小冒烟 |

### 4.2 人工判定准则（diff / 变更检测）

- `git -C ~/.agents/skills/team-orchestration status` 与 `git diff` 核对改动面（ZCode 安装目录通常非 git 仓库，桌面源目录 team-orchestration 为 git 仓库，可作基线）。
- 改动命中 SKILL.md / 自有逻辑 .md（trial-court*、cross-validation、phase-gates、team-setup 等）/ scripts/*.py / config.yaml / models.json → **强制回归**。
- **无 git 时的基线留存**：**技能目录当前非 git 管理**（v3.5 实测 `git rev-parse` 非仓库）——改动前**必须**按 §5.1 step-0 先备份受影响 reference 文件到指定备份目录 + 记录各文件 mtime 前后快照，确保可回滚基线不丢失（桌面源目录若为 git 仓库可作补充基线）。
- 无法判断是否触碰逻辑 → **保守触发**（宁跑勿漏，按强制回归处理）。

### 4.3 非触发情形（可跳过，但建议最小冒烟）

- **仅文档格式微调**（排版、加空行、措辞但不动逻辑/契约/字段）→ 定级 `最小冒烟`（§3.1），可跳全量回归。
- **仅新增实验性注释**、README 措辞、纯说明性变更 → 最小冒烟。
- **对 _index.md 展示字段**（含新增团队除外）→ 参照 team-setup.md 仍建议最小冒烟。
- **任何非触发情形仍建议最小冒烟**：`python tests/run_smoke.py` + `python tests/check_references.py`，确保未引入死链或编码损坏（F5 教训）。

---

## 5. 执行与验证

### 5.1 执行步骤序列（自下而上）

```
step 0  环境守护 env-check：核对解释器 / 工作区绝对路径 / 产物收集机制 / Git Bash heredoc 陷阱 / 无 git 时基线留存
       [ZCode 2026-08-09 实测基线，若换机以实测为准]：
         - 受管 Python        : python 3.12.8（系统 PATH 可直接 `python`）
         - 工作区路径          : C:\Users\林昌\.zcode\workspace\default（产物用工作区绝对路径，勿写 Git Bash /tmp）
         - scripts/*.py 存在性 : 断言 scripts/task-decomposer.py / expert-matcher.py / dispatch-planner.py
                              / trial-court-orchestrator.py / asset-resolver.py / cross-validator.py
                              / check_team_consistency.py / check_agent_completeness.py 均存在（新增校验脚本纳入）
                              / token_budget.py / checkpoint_manager.py / self_heal.py / auto-decider.py
                              / cycle_detector.py 均存在（v3.5 · P0-3 激活资产纳入）
         - tests/run_smoke.py 可运行: 直接执行 `python tests/run_smoke.py` 返回 exit 0
         - 子代理机制：task(subagent_type=...)（ZCode 无 inbox/TeamCreate，判据见 C2/R4）
       无 git 基线：若技能非 git 管理，改动前先备份受影响 reference 文件到 `<工作区>/deliverables/to-test-module/backup/`
                  + 记录各文件 mtime 前后快照（env-guard 负责）
step 1  基线自动化：runner 跑 python tests/run_smoke.py 与 python tests/check_references.py
（对应 §2 用例 C4、C5）
step 2  就绪后，lead 按触发面选定 §2 适用的 A/B/C 用例集
step 3  A 类核心功能点：runner 逐条触发 A1-A8，designated 全新上下文复核
step 4  B 类边界条件：runner 构造边界输入跑 B1-B7（重点 L1/L3 切换与规模门阈值）
step 5  C 类集成点：runner 按 C1-C7 触发（重点 TeamCreate / inbox 看门狗 / models 路由）
step 6  reporter 规范化日志，逐用例归 PASS/FAIL，汇总 pass 计数
step 7  lead 出 regression-report.md（固定路径 §5.5），附验收清单结论与通过/失败处理
```

### 5.2 每类用例预期输出标准（pass 判据）

- **A 类**：步骤序列正确、产物章节/字段齐全、无铁律违反 → PASS；任一铁律违反（代写/跳阶段/直连）即 FAIL。A1 额外校验：触发面与规模面分层判定正确、冲突仲裁按触发面优先。
- **B 类**：阈值处行为与 §1/§2 明文一致；降级/升级被显式记录 → PASS；阈值错或硬凑团队即 FAIL。B2 额外校验：不把 cross-validation 的 deep 深度档误当规模门 L4 档。

### R8 动态派数机制（v3.9 · TC-20260816-6）
- **测什么**：`task-decomposer --concurrency N` 的 `suggested_subagents` 取值符合终审公式（L1→0 / L2→1 直行信号 / L3+ clamp(base+bonus, 2, min(并发, 档位))）；L4-深度为深度档标签不破规模门。
- **怎么触发**：跑取值表断言（test_task_decomposer 已含 L×D 表 + --concurrency 上界 + rationale 字段）；构造 L1/L2 直行与 L3+ 并行两组用例核对 SKILL.md §3A 步骤 3 的推荐值读取；构造质证追加场景核对 §3-C 追加触发 + C(N,q) BLOCK 复检。
- **期望通过表现**：L1 建议 0（直行）、L2 建议 1（直行信号）、L3×D3=6（封顶）；--concurrency 4 截断到 4；rationale 含截断原因；追加派数后 C(N,q) 不超 BLOCK。
- **C 类**：task 返回值齐全（以返回值为准）、看门狗不假停滞、run_smoke 退出 0、引用无死链、视觉路由正确（**三路运行时不可用 → 外部 OCR 转文本喂子代理**，v3.5 统一口径）→ PASS；依赖消息流/自动通知即 FAIL。
- **F 系回归（R1-R5）**：见 §6 各自期望通过表现单独判定。

### 5.3 通过 / 失败处理逻辑

**通过**：全部 PASS → reporter 出报告 → lead 签字验收 → 回归结束，改动可进入使用。

**失败定位（红-绿循环 / 最小复现）**：
1. 先建紧的红循环：把最直接暴露症状的用例单独跑，确认稳定重现（变红）。
2. 逐个改因子（最小复现：最小输入 / 单路径 / 单字段），找到使断言转绿的改动。
3. 治本而非绕过门禁；禁止 --no-verify 式跳过。

**回滚协议**：
- **技能目录当前非 git 管理**（v3.5 实测，§4.2）。回归破坏且无法时限内修复 → 用 step0 备份目录恢复（`<工作区>/deliverables/to-test-module/backup/`）或 mtime 快照回滚；桌面源目录若为 git 仓库可补充用 `git -C <源目录> checkout -- <受损文件>` / revert 到改动前 commit。
- 回滚前确认无未保存交付；回滚后重跑 step1 基线 + 相关 F 系用例确认恢复绿。
- 破坏性/共享操作（force push、reset）须 lead 确认，不擅自执行。

**上报**：
- 失败用例、红绿证据、最小复现、回滚动作与结果一律由 reporter/lead 写入 regression-report.md（§5.5 路径）并回传 team-lead。
- 若 F1-F5 复发，标记对应 R 编号并附回归是否引入证据。

### 5.4 验收清单（checklist）

```
□ step0 环境守护检查通过（解释器=3.13 / 路径 / inbox / heredoc / 脚本存在性 / run_smoke 可运行）
□ step0 无 git 时基线备份 + mtime 快照已记录（若适用）
□ step1 run_smoke.py 退出码 0，全部 PASS
□ step1 check_references.py 退出码 0，无死链
□ test_file_health 全包 UTF-8 健康
□ 覆盖面：至少 1 个 A 功能点 + 1 个 B 边界 + 1 个 C 集成点 + 全部 R 系用例
□ 独立复核人 designated 以全新上下文全程参与，非执行者自证
□ 全部 R1-R5 通过 / 或已记录失败与红绿证据
□ regression-report.md 已产出（固定路径 §5.5），含 pass 计数、失败定位、回滚记录（若有）
□ lead 签字验收
```

### 5.5 回归报告唯一路径（固定单一）

> **回归报告固定路径**：`<工作区>/deliverables/to-test-module/regression-report.md`（本模块验收产物集中落这一个位置，不再二选一）。

- 该文件为每次回归的单一事实源，供 team-lead 与后续模块读取。
- 可选考虑纳入 git 管理，便于追踪历史与对比历次回归结论。

---

## 6. 真实回归用例（强约束）

R1-R5 直接把《dialogue-facts.md》的 F1-F5 转为可执行回归用例；R6-R7 为两次演练提炼的正向编排成功断言。

### 6.0 测试 fixtures 数据源（R1/R2/R3/T07/T10/T06 依赖的确定载体）

> 下列为回归统计判定所需的**确定测试数据**，回归执行者按此**独立构造复算脚本（不读原实现）**，确保可重复。

| 用例 | 数据 | 构造方式 |
|------|------|----------|
| T07 / R2（布隆过滤器二项 Z 检验） | `m=8000, k=5, n=1000, seed=42`；理论 `p_fp=(1-e^{-kn/m})^k ≈ 0.0217`；`σ=sqrt(p_fp*(1-p_fp)/n) ≈ 0.0046`；观测假阳性数 `X=36` → `p_hat=0.036`；`Z=(p_hat-p_fp)/σ ≈ 3.11` | 独立复算脚本：按 m/k/n/seed 重建位数组、插 n 项、测另 n 项计数 X=36，再按上式算 p_hat/σ/Z；不读原 t07 实现 |
| T10（蒙特卡洛 σ 口径） | `N=1e6, reps=5, seed=42`；`sigma_single≈0.00164`（单次实验 std）；`sigma_mean=sigma_single / sqrt(5) ≈ 0.00073`（5 次均值 std） | 独立脚本跑 5 次各 1e6 点，分别按 `4*sqrt(p(1-p)/N)` 与 `sigma_single/sqrt(reps)` 算两口径；不读原 t10 实现 |
| R3 / T06（题面冲突） | 题面给"理论最大≈3.85"，实际函数 `f(x)=x·sin(10πx)+2` 在 x∈[0,1] 上最大值 `≈2.850595 @ x≈0.8512` | 独立脚本对 x∈[0,1] 做 ≥1e6 点扫描得最大值，与题面 3.85 对比判冲突；不读原 t06 实现 |

### R1〔F1〕独立验证层不可缺失——worker 自报不可信
- **测什么**：编排必须内建独立复算/复核层，不采信自报"通过"。
- **怎么触发**：构造 runner 声称"数值通过"但实为统计自报的任务（T07 场景，数据见 §6.0）。观察是否自动引入独立验证层。
- **期望通过表现**：终审必须有独立复核者全新上下文复算；自报被复核而非照抄；冲突时以独立复算为准并在报告标偏离。

### R2〔F2〕统计判定须有严格口径——禁止宽区间掩盖偏离
- **测什么**：置信区间/σ 判定须有严格口径与断言，不得用宽区间包住显著偏离。
- **怎么触发**：复跑 T07 二项 Z 检验（数据与公式见 §6.0）：p_fp、σ、Z 均按严格口径独立计算。
- **期望通过表现**：Z=3.11>1.96 判"显著偏离"，而非 "落在 [0.2x,2x] 通过"；口径写报告；自定宽区间判 FAIL。

### R3〔F3〕与题面/规格冲突须显式上报——不得静默藏入源码注释
- **测什么**：worker 发现题面/规格错误，须在显著位置显式上报（日志顶部/冲突标记），不写进源码注释。
- **怎么触发**：构造题面理论值有误场景（T06：题面≈3.85 vs 独立扫描实际≈2.850595，数据见 §6.0）。
- **期望通过表现**：冲突出现在汇总/日志顶部显著位置并附独立证据；即便判断正确也不凑题面篡改；仅源码注释标注无显式上报 → FAIL。

### R4〔F4〕后台送达以 task 返回值为准——实时流不可靠，须设看门狗
- **测什么**：判后台 worker 完成以 **task 返回值 / 完成通知**（ZCode 无 inbox 文件）为准，而非实时消息流；设超时看门狗。
- **怎么触发**：spawn 后台 worker 并模拟消息流未弹出（掩盖实时事件）。
- **期望通过表现**：即使无消息流，仍以 task 返回值 / TaskOutput 看门狗确认收齐全部产物并继续质证；无假停滞；超时兜底正常。

### R5〔F5〕日志含可复现元数据——路径+命令+SHA-256
- **测什么**：产物落盘含元数据（代码路径 + 运行命令 + SHA-256 + exit），可复现。
- **怎么触发**：检查任意任务交付（对照两次演练 src/ + manifests/hashes.txt + team_process.log）。
- **期望通过表现**：每产物含源码绝对路径（工作区绝对路径）、运行命令（受管解释器 3.13 路径）、SHA-256、exit=0、关键结论；缺任一 → FAIL。另：脚本用 Python `open(..., encoding='utf-8')` 直写中文避免 Write 工具 3 字节 UTF-8 打散；heredoc 写工作区绝对路径，不写 Git Bash /tmp。**编码强制（v3.8 · TC-20260816-4）**：所有写入必须显式 UTF-8（无 BOM）——Python 裸 `write_text`/`open()` 在本机（locale=cp936）默认写 GBK；PowerShell 裸 `Set-Content`（默认 GBK）/`Out-File`（默认 UTF-16LE）同理；必须显式 `encoding="utf-8"` / `-Encoding UTF8`（PS5.1 的 UTF8 带 BOM，如需无 BOM 用 `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`）。产出物以 `tests/test_file_health.py`（全包 UTF-8 strict 扫描）为回归防线。

### R6〔正向 1：TeamCreate 切换任务列表 + 并行后台 worker 可并发解题〕
- **测什么**：TeamCreate 后任务列表切到团队目录、原列表被隔离；并行 spawn 后台 worker（Agent + run_in_background）可同时解多任务。
- **怎么触发**：复跑演练 team-test/batch2 的"3 worker 并行解 10 题"流程。
- **期望通过表现**：任务列表正确切换；多后台 worker 并行 spawn 且各自产出到应落盘位置；最终汇总 10/10 结果。

### R7〔正向 2：独立复核能揪出误判 + 规范化日志可复现〕
- **测什么**：独立子代理（全新上下文）复核能揪自报背后的统计误判（T07 Z=3.11 / T10 σ 口径）；规范化日志重写后含路径+命令可复现；8/10 一致、T07 显著偏离、T10 口径修正。
- **怎么触发**：对团队产物跑含独立复核的终审，并用规范化规则重写日志。
- **期望通过表现**：独立复核发现并纠正 ≥1 处统计误判；重写日志含代码路径 + SHA-256 + 运行命令 + exit；8/10 与原自报一致、T07 判显著偏离、T10 判口径修正；汇总表"通过"源于独立复核而非复制自报。

---

## 附录：模块文件落盘建议

- 草案定稿 → 写入技能 `references/test-workflow.md`（选择性加载模块实体，顶部含 §3.1 step-0 自检清单）。
- `SKILL.md` §8 追加一行（见 §3.2，用途栏加粗写"作为回归门禁"），不进入主流程。
- 回归结果报告固定落 `<工作区>/deliverables/to-test-module/regression-report.md`（§5.5，单一事实源，可选纳入 git）。


