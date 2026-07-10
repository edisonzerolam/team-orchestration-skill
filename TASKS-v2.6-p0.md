# P0 阶段可执行任务清单（细化至原子级）

版本: v2.6 P0 (1-2 周)
当前版本锚点: SKILL.md v2.5.0
审计状态: 🔴 已过审（含条件，详见 AUDIT-REPORT.md）

---

## 执行纪律

- 每项完成后必须运行对应测试（`pytest tests/ -k <test_name>`）
- 修改前先读文件，不准盲改
- 每项合并前必须经 @code-reviewer 审查
- 每完成一个子阶段（S1/S2/...）运行一次全量回归测试
- **回滚纪律**: 每子阶段开始时备份被修改文件（`cp file.py file.py.bak`），完成后验证删除

---

## T0: 前置修复（审计发现运行时 Bug + 方案修正，启动 S0 前完成）

### T0.1 拍快照锁定基线
- **命令**: `pytest tests/ -v --junitxml=shared/snapshot-pre-v2.6.xml`
- **验收**: 输出文件存在且所有测试通过
- **回滚**: 无

### T0.2 修复文件名 Bug（B1 — 运行时必崩）
- **文件**: `scripts/expert_matcher.py` L249 + `scripts/path-selector.py` L237
- **改动**: `"task-decomposer.py"` → `"task_decomposer.py"`（中划线改下划线）
- **验收**: `python3 scripts/expert_matcher.py --task "分析某公司基本面"` 不报 ImportError

### T0.3 修复 pi_types 中文→能力映射 Bug（B2 — capability_match 总为 0）
- **文件**: `scripts/expert_matcher.py` L255
- **改动**: 将 `result.get("pi_types", [])` 替换为中文→英文能力映射：
  ```python
  pi_to_abilities = {
      "信息检索型": ["search", "research", "information", "data_collection"],
      "分析判断型": ["analysis", "judgment", "evaluation", "assessment"],
      "创作生成型": ["creation", "generation", "design", "writing"],
      "决策执行型": ["decision", "execution", "implementation"],
  }
  abilities = [kw for pi in result.get("pi_types", []) for kw in pi_to_abilities.get(pi, [])]
  ```
- **验收**: `match()` 传入"分析判断型"时代入英文能力评估，domain_match + capability_match 均 > 0

### T0.4 新增 2 种 subtask type + Phase 编号方案
- **文件**: `scripts/task_decomposer.py`
- **改动**:
  - `PI_TYPES` 增加 `"p5": {"name": "协作讨论型", "keywords": ["讨论","辩论","头脑风暴","研讨"]}, "p6": {"name": "质量验证型", "keywords": ["测试","审查","验证","审核"]}`
  - Phase 编号：Phase 1 调研 → Phase 2.5 验证 → Phase 3 执行 → Phase 3.5 协作讨论
- **验收**: 含"讨论/辩论"等词 → 产出 `collaborative_discussion`；含"测试/审查"等词 → 产出 `quality_verification`

### T0.5 阈值统一 + 兼容性属性（B4 + F3）
- **文件**: `scripts/expert_matcher.py` L46-49 + `scripts/path-selector.py` L30-47
- **改动**: 两处 0.8 → 0.75, 0.5 → 0.45
- **兼容性**: `expert_matcher.py` 保留 `WEIGHTS` 和 `THRESHOLDS` 模块级属性作为从 weight-matrix.json 读取的代理引用，确保 `test_expert_matcher.py` 的现有断言不崩溃
- **验收**: 阈值的两处引用一致；`pytest tests/test_expert_matcher.py -v --no-explore` 全部通过

### T0.6 计数修正（B5 — 29 团非 28 团）
- **改动**: `_index.md` L5: 28→29, 188→(实际验证后更新)；`PLAN.md` 全部 4 处引用；`SKILL.md` L14；`TASKS.md`
- **验收**: 全部 4 个文件的计数统一为 29 团

### T0.7 审计脚本 audit-team-counts.py（F4）
- **文件**: `scripts/audit-team-counts.py`（新建）
- **功能**: 验证 `_index.md`/`SKILL.md`/`PLAN.md`/`shared/teams-index.json` 中的计数与实际文件系统匹配
- **验收**: 运行后无计数偏差报告

### T0.8 统一 expert-scores.json 路径
- **文件**: `scripts/expert_matcher.py` L31 + `scripts/self-evolution/post-task-evolve.py` L12
- **改动**: `SCORES_FILE` 路径统一到 `shared/expert-scores.json`
- **数据迁移**: 如旧文件存在，复制内容到新路径
- **验收**: 两处引用一致

### T0.9 全量回归（T0 护城河）
- **命令**: `pytest tests/ -v --junitxml=shared/snapshot-post-t0.xml`
- **验收**: 与 T0.1 快照 100% 一致（仅阈值测试断言值允许更新）

## S0: 三阶层次化加载基础设施（预计 2-3 天）

**前置依赖**: T0 全部完成
**回滚**: `git checkout -- scripts/expert_matcher.py scripts/migrate-workbuddy.py` → `rm -rf shared/teams-index.json shared/teams-tier.json shared/budget-config.json shared/token-budget.json shared/cache-config.json shared/token-ledger.json` → 全量回归

### S0.1 预生成 teams-index.json

- **文件**: `scripts/migrate-workbuddy.py`（修改）+ `shared/teams-index.json`（新增，自动生成）
- **内容**: `build_teams_index()` 函数 — 遍历 `workbuddy-experts/*/plugin.json` 提取 Tier 1 字段
  - 只读 plugin.json 的 displayName/displayDescription/categoryId/expertType/agent_count
  - 从 description 提取能力关键词（不读 agent .md）
  - 输出到 `shared/teams-index.json`
- **验收**: 运行构建脚本 → 49 个团全部在索引中，总大小 < 10KB
- **回滚**: 删除 shared/teams-index.json，load_all_experts() 自动回退

### S0.2 实现 load_experts_light() — Tier 1

- **文件**: `scripts/expert_matcher.py`（新增函数）
- **改动**:
  - 新增 `load_experts_light()` — 只读 `shared/teams-index.json`
  - 结果写入 L1 缓存（永不过期）
  - `teams-index.json` 不存在时自动抛 Warning 但不 crash
- **验收**: 调用 `load_experts_light()` 返回 49 团轻量索引，无 agent .md 读取

### S0.3 实现 load_experts_detail() — Tier 2

- **文件**: `scripts/expert_matcher.py`（新增函数）
- **改动**:
  - 新增 `load_experts_detail(team_names: list)` — 只读指定团的 plugin.json
  - 结果写入 L2 缓存（5min TTL）
  - 不读 agent .md 文件内容（但获取文件名列表）
- **验收**: `load_experts_detail(["investment-masters-team"])` 返回单团完整 plugin.json 但 0 agent .md 读取

### S0.4 实现 load_agents_lazy() — Tier 3

- **文件**: `scripts/expert_matcher.py`（新增函数）
- **改动**:
  - 新增 `load_agents_lazy(team_name: str)` — 读指定团的 `agents/*.md`
  - 返回 `{agent_id: {description, content_length, token_estimate}}`
  - 用 `errors="replace"` 兜底编码问题
  - 不缓存（L3 用完即弃）
- **验收**: 调用后加载且仅加载 1 个团的所有 agent .md 内容

### S0.5 实现热/温/冷分级

- **文件**: `scripts/expert_matcher.py`（新增 3 个函数）+ `shared/teams-tier.json`（新增）
- **函数**: `is_cold_team()`, `is_warm_team()`, `is_hot_team()`, `_update_team_tier_state()`
- **分级规则**:
  - Hot: `last_used < 7d`
  - Warm: `7d ≤ last_used < 30d`
  - Cold: `last_used ≥ 30d or never used`
- **集成**: `match()` 完成后调用 `_update_team_tier_state(selected_team, "used")`
- **验收**: Cold 团的 match() 调用不触发 Tier 2/3 读取

### S0.6 实现 Token 预算管理

- **文件**: `scripts/budget-controller.py`（新增）+ `shared/budget-config.json`（新增）+ `shared/token-budget.json`（新增）
- **BudgetController**:
  - `check_budget(team_name, agent_count)` → BudgetVerdict
  - 根据预算使用率自动降级（≥85% → economy）
  - Standby 判定：economy 模式下尾部 agent 只加载元数据
- **验收**: standard 模式下降级阈值按 85% 触发；economy 模式 agent 数 ≤ 5

### S0.7 实现三级缓存配置

- **文件**: `shared/cache-config.json`（新增）
- **内容**: L1(永不过期) / L2(300s TTL) / L3(用完即弃) 三级缓存定义
- **验收**: 配置 JSON 可读，与 expert_matcher.py 中的 `_cache_get/_cache_set` 兼容

### S0.8 实现 Token 记账

- **文件**: `shared/token-ledger.json`（新增）
- **内容**: 全局 Token 账本，记录每次执行的 token 消耗
- **集成**: orchestrator 执行完成后调用 TokenAccount.record()
- **验收**: 执行一个 mock 任务后 token-ledger.json 有记录

### S0.9 测试三阶加载

- **文件**: `tests/test_lazy_loading.py`（新建）
- **测试用例**:
  - `test_tier1_load`: load_experts_light() 返回索引且不触发 disk read of agent .md
  - `test_tier2_load`: load_experts_detail() 只读指定团 plugin.json
  - `test_tier3_load`: load_agents_lazy() 执行后加载 agent .md
  - `test_cold_team_skip`: Cold 团跳过 Tier 2/3
  - `test_tier1_fallback`: teams-index.json 不存在时回退 load_all_experts()
  - `test_budget_downgrade`: 预算 85%+ 时自动降级 economy
- **验收**: `pytest tests/test_lazy_loading.py -v` 全部通过

### S0.10 预验尸：风险覆盖

- 🟢 teams-index.json 不存在 → `load_experts_light()` 回退到 `load_all_experts()`
- 🟢 候选团 plugin.json 不存在 → 跳过该候选，继续下一个
- 🟢 token-budget.json 不存在 → BudgetController 返回无限预算
- 🟢 agent .md GBK 编码 → `errors="replace"` 兜底
- 🟢 L2 缓存过期 → 自动重读 plugin.json
- 🟢 全量回归不破坏现有测试

## S1: 匹配引擎重写（核心改动，预计 3-4 天）

**前置依赖**: T0 全部完成 + S0 全部完成
**回滚**: `git checkout -- scripts/expert_matcher.py` → `rm shared/weight-matrix.json shared/exploration-log.json` → 全量回归验证

### T1.1 设计权重矩阵数据结构
- **文件**: `shared/weight-matrix.json`（新建）
- **内容**: 6 种任务类型 × 4 维度的权重 JSON，含降级回退配置
- **Schema**:
  ```json
  {
    "version": "1.0",
    "task_types": {
      "analysis_judgment": { "domain": 0.35, "capability": 0.25, "performance": 0.25, "load": 0.15 },
      "information_retrieval": { "domain": 0.40, "capability": 0.30, "performance": 0.15, "load": 0.15 },
      "creation_generation": { "domain": 0.25, "capability": 0.40, "performance": 0.20, "load": 0.15 },
      "decision_execution": { "domain": 0.30, "capability": 0.35, "performance": 0.20, "load": 0.15 },
      "collaborative_discussion": { "domain": 0.30, "capability": 0.30, "performance": 0.20, "load": 0.20 },
      "quality_verification": { "domain": 0.25, "capability": 0.30, "performance": 0.30, "load": 0.15 }
    },
    "fallback": { "domain": 0.35, "capability": 0.30, "performance": 0.20, "load": 0.15 }
  }
  ```
- **验收**: JSON schema 验证通过，回退配置可读

### T1.2 重写 expert_matcher.py
- **文件**: `scripts/expert_matcher.py`（重写）
- **改动**:
  - 接受 `--task-type` 参数，`match()` 函数签名保持向后兼容（`task_type=None` 时用 fallback 权重）
  - 根据 task-type 从 weight-matrix.json 加载权重
  - 保留原 domain_match / capability_match / performance_score / current_load 计算
  - 新增: task-type 未知时降级到默认权重(35/30/20/15)
  - 新增: 输出结果含各子维度得分（供调试）
  - 新增: `--no-explore` 参数（测试用，关闭 ε-greedy）
  - 新增: `--force-team TEAM_NAME` 参数（跳过匹配，直接指定执行团队，用于紧急场景或用户显式要求）
  - **必须**: `SCORES_FILE` 路径改为指向 `shared/expert-scores.json`（已由 T0.2 保证）
- **验收**: `python3 scripts/expert_matcher.py --task-type analysis_judgment --json` 输出正确

### T1.3 实现 ε-greedy 冷启动
- **文件**: `scripts/expert_matcher.py`（同上）
- **改动**:
  - 新增 `exploration_control()` 函数
  - performance_score = 0 的专家进入探索池
  - ε = 0.15，衰减至 0.02 封底
  - 新专家基准分 = 同类专家历史均值 × 0.8
- **验收**: 新专家在 5 次调用内 score 趋近正常水平

### T1.4 新增探索日志
- **文件**: `shared/exploration-log.json`（新建）
- **数据结构**:
  ```json
  {
    "experts": {
      "expert-name": {
        "exploration_count": 3,
        "status": "exploring",
        "entries": [
          { "timestamp": "2026-07-10T12:00:00Z", "task_type": "analysis_judgment", "result": "success" }
        ]
      }
    }
  }
  ```
- **规则**: 同一 expert exploration_count >= 5 → status 自动转为 "graduated"（转正）
- **验收**: 探索记录可查询、可聚合、满 5 次自动转正

### T1.5 更新匹配设计文档
- **文件**: `references/expert-matching.md`
- **改动**: 更新评分公式、权重矩阵说明、冷启动策略
- **验收**: 文档与代码一致

### T1.6 更新 orchestrator.py 调用链
- **文件**: `scripts/orchestrator.py`
- **改动**: `match_experts(domains, abilities)` → `match_experts(domains, abilities, task_type=...)`
- **验收**: 集成测试通过

### T1.7 更新 path-selector.py 调用链
- **文件**: `scripts/path-selector.py`
- **改动**: `em.match(domains, top_k=3)` → `em.match(domains, task_type=..., top_k=3)`
- **验收**: 集成测试通过

### T1.8 确保现有测试兼容性
- **文件**: `tests/test_expert_matcher.py`（现有 + 追加）
- **测试用例**:
  - **现有用例保持**: 确认 169 行现有测试在 `--no-explore` 模式下全部通过
  - 6 种 task-type 各至少 1 个用例（含新 2 种）
  - 冷启动新专家探索概率验证（`--no-explore` 外部环境）
  - 未知 task-type 降级验证
  - 跨领域匹配验证
  - 阈值回退测试: 传入 v2.5 旧参数，确认输出退化可控
  - S2 后追加: 49 个团完整性校验（`pytest.mark.skipif` 动态）
- **验收**: `pytest tests/test_expert_matcher.py -v --no-explore` 全部通过

---

## S2: 专家池扩展（预计 3-4 天，含自动化脚本压缩至 2 天）

**前置依赖**: S1 完成（能力提取接口稳定）
**回滚**: `rm -rf references/workbuddy-experts/{game-development,industry-consulting,tencent-ecosystem}` + 删除其他 18 个移植团目录 → `git checkout -- references/workbuddy-experts/_index.md SKILL.md` → 全量回归

### T2.0 自动化移植脚本（审计建议，先做这个再手动移植）
- **文件**: `scripts/migrate-workbuddy.py`（新建）
- **功能**:
  - `build_team_index()`: 从 `workbuddy-experts/*/plugin.json` 提取 Tier 1 索引（用于 S0）
  - `import_team(source, target)`: 复制团目录到 skill
  - `import_single_agent(source, target)`: 复制独立专家（自动推断 group_id）
  - `build_manifest()`: 生成 `shared/manifest-post-s2.json` 记录所有新文件路径
  - `--undo`: 从 manifest.json 读取文件列表并删除
- **自动分组**: 基于 description 关键词分配 group_id：
  - 含 "游戏/策划/Unity/Unreal/美术/程序" → game-development
  - 含 "行业分析/咨询/战略/市场" → industry-consulting
  - 含 "腾讯/微信/云/企业微信/小程序" → tencent-ecosystem
  - 其余 → ungrouped
- **验收**: 对任意源目录运行 `--undo` → 删除创建的文件；`build_manifest()` 输出 manifest.json 含全部新文件路径

### T2.1 移植 18 个待移植专家团
- **方式**: 先用 T2.0 脚本批量生成，再人工审核修正
- **源**: `C:\Users\林昌\WorkBuddy\2026-07-10-04-14-17\experts-download\plugins\` 各目录
- **目标**: `references/workbuddy-experts/{name}/` 每个团一个目录
- **格式**: 每个团包含 `_index.md`（团描述）+ 各 Agent `.md` 文件
- **验收**: 18 个团全部移植，目录结构标准化，无团 categoryId 为空

### T2.1b 移植 285 个独立专家（全部归集到 skill）
- **方式**: 用 T2.0 脚本的 `import_single_agent()` 模式，自动分组 + 自动创建单 Agent 目录
- **源**: `C:\Users\林昌\WorkBuddy\2026-07-10-04-14-17\exported-experts\` 各 expert 目录的 agent prompt
- **目标**: `references/workbuddy-experts/{expert-name}/` 每个独立专家一个单 Agent 目录
- **格式**: 每个独立专家目录包含 `plugin.json`（单 agent 配置）+ `agents/expert.md`（prompt）
- **归档**:
  - `groups/README.md` 更新分组映射
  - `shared/manifest-post-s2.json` 记录所有 570+ 新文件路径
- **验收**: 285 个独立专家全部移植，所有 prompt 文件可读，group_id 非空
- **设计文档**: `references/expert-files-organization.md`

### T2.1c 生成 groups/README.md
- **文件**: `references/workbuddy-experts/groups/README.md`（新建）
- **内容**: 虚拟团→独立专家的映射表（game-development/industry-consulting/tencent-ecosystem/ungrouped）
- **验收**: 映射表与 T2.2-2.4 的虚拟团角色分配一致

### T2.2 创建 game-development 虚拟团
- **来源**: 游戏空间领域独立专家（25 人）
- **文件**: `references/workbuddy-experts/game-development/_index.md`
- **角色**: 策划 4 人 / 美术 4 人 / 程序 5 人 / QA 3 人 / 运营 3 人
- **验收**: plugin.json 格式正确，可被 expert_matcher 识别

### T2.3 创建 industry-consulting 虚拟团
- **来源**: 行业顾问领域独立专家（17 人）
- **文件**: `references/workbuddy-experts/industry-consulting/_index.md`
- **角色**: 分析师 5 人 / 顾问 5 人 / 报告撰写 4 人
- **验收**: 同上

### T2.4 创建 tencent-ecosystem 虚拟团
- **来源**: 腾讯专区独立专家（34 人）+ 现有 RUM 团
- **文件**: `references/workbuddy-experts/tencent-ecosystem/_index.md`
- **角色**: 云架构 6 人 / 营销 5 人 / 合规 4 人 / 技术 6 人
- **验收**: 同上

### T2.5 更新专家池索引
- **文件**: `references/workbuddy-experts/_index.md`
- **改动**: 新增 21 个团（18 移植 + 3 虚拟），更新总计数
- **验收**: 索引总计数 = 29 + 21 = 50（29 已有团 + 18 移植团 + 3 虚拟团）

### T2.6 更新 SKILL.md 头部
- **文件**: `SKILL.md`（第 14 行）
- **改动**: "可用专家池：49 个 WorkBuddy 专家团 + 6 个 subagent"
- **验收**: 数字正确

### T2.7 测试新团匹配
- **文件**: `tests/test_expert_matcher.py`（追加）
- **测试**: 匹配 3 个新虚拟团的触发词时返回正确结果
- **新增**: 遍历所有 49 个团，验证每个团 categoryId 非空、agent_count > 0
- **验收**: 匹配 3 个新团的触发词时返回正确结果；49 个团全部通过完整性校验

---

## S3: 模板动态裁剪（2-3 天）

**前置依赖**: S1 能力提取接口已稳定 + T1.8 测试通过
**回滚**: `rm scripts/template-cropper.py shared/cropping-config.json references/team-templates/dynamic-cropping.md` → `git checkout -- scripts/orchestrator.py` → 全量回归

### T3.1 设计裁剪规则文档
- **文件**: `references/team-templates/dynamic-cropping.md`（新建）
- **内容**:
  - 子任务类型 → 所需角色映射表
  - 大团默认裁剪比例
  - 20% 弹性容量预留规则（弹性是人数还是角色数的 20% → 按人数）
  - 运行时增补触发条件
- **验收**: 文档完整可执行

### T3.2 实现 template-cropper.py
- **文件**: `scripts/template-cropper.py`（新建）
- **功能**:
  - 输入: 团队名 + 子任务列表 + 复杂度
  - 输出: 裁剪后的角色列表（含 20% 弹性槽位）
  - 裁剪不足 3 人时自动不裁剪
- **验收**: 对 investment-masters 裁剪至 6-10 人

### T3.3 配置 6 个大团裁剪规则
- **文件**: `shared/cropping-config.json`（新建）
- **Schema**:
  ```json
  {
    "investment-masters": {
      "base_size": 8,
      "elastic_ratio": 0.2,
      "min_size": 3,
      "role_priority": ["analyst", "strategist", "risk_manager"]
    },
    ...
  }
  ```
- **验收**: 每团裁剪后 ≥ 3 人且保留核心角色

### T3.4 新增 team_builder.py 模块（B3/F1 修复）
- **说明**: 当前 `orchestrator.py` 只是 DAG 执行器，无 `build_team()` 方法。匹配+裁剪的编排不应放在 orchestrator 中
- **文件**: `scripts/team_builder.py`（新建）
- **功能**:
  - `build_team(task, task_type)`: 封装 match_experts → template-cropper → 输出裁剪后的 team
  - `TeamBuildResult = {agents, token_estimate, mode}` 
  - 供 SKILL.md 工作流和 orchestrator 调用
- **集成**: `scripts/orchestrator.py` 的 `run()` 在 `_step1_decompose` 后调用 `team_builder.build_team()`
- **验收**: 端到端流程中：task → decomposer → team_builder(match→crop) → orchestrator(execute)

### T3.5 测试裁剪 + team_builder
- **文件**: `tests/test_template_cropper.py`（新建）+ `tests/test_team_builder.py`（新建）
- **测试用例**:
  - test_crop_large_team: 大团裁剪至合理大小
  - test_crop_small_team: 小团(≤3人)不裁剪
  - test_crop_elastic: 弹性槽位在需要时可被填充
  - test_build_team: team_builder 匹配→裁剪链路完整
- **验收**: 全部通过

---

## S4: 专家评分卡 v1（2-3 天）

**前置依赖**: T0.2 路径统一已完成
**回滚**: `git checkout -- shared/expert-scores.json scripts/self-evolution/post-task-evolve.py` → `rm scripts/score-collector.py` → 全量回归

### T4.1 扩展评分卡 schema
- **文件**: `shared/expert-scores.json`
- **改动**: 新增字段 task_completion(0-10) / delivery_quality(0-10) / response_time(0-10) / user_feedback(0-10) / collaboration(0-10)
- **路径确认**: `SCORES_FILE` 统一指向 `shared/expert-scores.json`（T0.2 已保证）
- **验收**: schema 向后兼容

### T4.2 实现 score-collector.py
- **文件**: `scripts/score-collector.py`（新建）
- **功能**:
  - 采集 reviewer 评分 → delivery_quality
  - 采集完成时间 → response_time
  - 采集用户反馈 → user_feedback
  - 采集队友评估 → collaboration
  - 聚合计算综合分
- **验收**: 能读取虚拟数据并正确计算

### T4.3 集成评分触发
- **触发时机**: 子任务完成时（非全链路完成），由 orchestrator 在 phase 回调中触发
- **文件**: `scripts/self-evolution/post-task-evolve.py`
- **改动**: 子任务完成后自动调用 score-collector 采集评分
- **验收**: 完成模拟子任务后评分被正确记录到 `shared/expert-scores.json`

### T4.4 测试评分卡
- **文件**: `tests/test_score_collector.py`（新建）
- **测试用例**:
  - 全维度正常采集
  - 部分维度缺失（如无用户反馈）
  - 聚合计算正确性
  - 冷启动默认值
- **验收**: 全部通过

---

## S5: 模板索引更新与集成测试（1-2 天）

**前置依赖**: S1-S4 全部完成
**回滚**: `git checkout -- references/team-templates/index.md` → 全量回归验证（回滚后只剩 15 个旧模板）

### T5.1 更新模板索引
- **文件**: `references/team-templates/index.md`
- **新增 3 个模板**:
  - `game-development`: 游戏开发全流程
  - `industry-consulting`: 行业咨询分析
  - `tencent-ecosystem`: 腾讯生态集成
- **验收**: 格式与现有模板一致

### T5.2 全量回归测试
- **命令**: `pytest tests/ -v --no-explore`
- **验证**: 现有用例零退化 + 新用例全部通过；慢测试（334 文件扫描）用 `@pytest.mark.slow` 标记
- **验收**: 回归通过率 100%

### T5.3 自动化端到端集成测试（F5 修复）
- **文件**: `tests/test_e2e_pipeline.py`（新建）
- **测试场景**（mock 数据）:
  - 标准路径: task → decomposer → match → crop → execute → score
  - Cold 团路径: match 时只扫描 Tier 1
  - Token 降级路径: 预算 85%+ 自动切 economy
  - 回退路径: teams-index.json 不存在→回退 load_all_experts()
- **验收**: `pytest tests/test_e2e_pipeline.py -v --no-explore` 全部通过

---

## 文件变更汇总

| 操作 | 文件 | 所属阶段 |
|------|------|---------|
| **新建** | `shared/weight-matrix.json` | S1 |
| **新建** | `shared/exploration-log.json` | S1 |
| **新建** | `shared/cropping-config.json` | S3 |
| **新建** | `shared/teams-index.json` | S0 |
| **新建** | `shared/teams-tier.json` | S0 |
| **新建** | `shared/budget-config.json` | S0 |
| **新建** | `shared/token-budget.json` | S0 |
| **新建** | `shared/cache-config.json` | S0 |
| **新建** | `shared/token-ledger.json` | S0 |
| **新建** | `shared/manifest-post-s2.json` | S2 |
| **新建** | `scripts/budget-controller.py` | S0 |
| **新建** | `scripts/template-cropper.py` | S3 |
| **新建** | `scripts/team_builder.py` | S3 |
| **新建** | `scripts/score-collector.py` | S4 |
| **新建** | `scripts/migrate-workbuddy.py` | S2 |
| **新建** | `scripts/audit-team-counts.py` | T0 |
| **新建** | `references/team-templates/dynamic-cropping.md` | S3 |
| **新建** | `references/expert-files-organization.md` | T0 |
| **新建** | `groups/README.md` (在 workbuddy-experts 内) | S2 |
| **新建** | `tests/test_lazy_loading.py` | S0 |
| **新建** | `tests/test_expert_matcher.py` | S1 |
| **新建** | `tests/test_template_cropper.py` | S3 |
| **新建** | `tests/test_team_builder.py` | S3 |
| **新建** | `tests/test_score_collector.py` | S4 |
| **新建** | `tests/test_e2e_pipeline.py` | S5 |
| **重写** | `scripts/expert_matcher.py` | S1 |
| **修改** | `references/expert-matching.md` | S1 |
| **修改** | `references/workbuddy-experts/_index.md` | S2 |
| **修改** | `SKILL.md` | S2 |
| **修改** | `scripts/orchestrator.py` | S3 |
| **修改** | `shared/expert-scores.json` | S4 |
| **修改** | `scripts/self-evolution/post-task-evolve.py` | S4 |
| **修改** | `references/team-templates/index.md` | S5 |
| **修改** | 18 个团引用 + 3 个虚拟团 | S2 |
| **修改** | 285 个独立专家导入（脚本生成目录） | S2 |
