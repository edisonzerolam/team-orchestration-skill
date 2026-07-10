# Team Orchestration v2.6 P0 方案 · 专家审计综合报告（v2）

审计日期: 2026-07-10
审计小组: @reviewer(质量门控) + @code-reviewer(代码质量) + @debug-expert(执行可行性)

---

## 总体裁决

| 审计员 | 裁决 | P0 阻塞数 |
|--------|------|----------|
| @reviewer | 🟡 CONDITIONAL | 3 项 |
| @code-reviewer | 🔴 FAIL | 7 项（含 2 个现有运行时 bug） |
| @debug-expert | 🔴 FAIL | 5 项 |
| **综合** | **🔴 FAIL** | **15 项修复（8 项计入 T0 前置）** |

---

## 🔴 强制修复清单（分两类）

### A 类：现有代码中的运行时 Bug（与 v2.6 方案无关，T0 前置修复）

| ID | 问题 | 文件·行号 | 严重度 | 修复 |
|----|------|----------|-------|------|
| B1 | 文件名 `task-decomposer.py`(中划线) 实际是 `task_decomposer.py`(下划线) → import 报错 | expert_matcher.py:249 / path-selector.py:237 | **🔴 P0 运行时必崩** | 改为下划线 |
| B2 | `pi_types` 中文名被当 `task_abilities` 传 capability_match() → 总是返回 0 | expert_matcher.py:255 | **🔴 P0 capability 匹配永远是 0** | 增加中文→英文能力映射 |
| B3 | `orchestrator.py` import 了 `match_experts` 但从未调用 → 核心链路断裂 | orchestrator.py:31-33 | 🔴 P0 架构断裂 | 新增 `team_builder.py` 封装匹配→裁剪→执行链路 |
| B4 | path-selector.py 阈值 0.8/0.5 未同步 → 匹配引擎和路径选择器判定不一致 | path-selector.py:30-47 | 🔴 P0 | 同步为 0.75/0.45 |
| B5 | 实际已有 29 团（含 openspec-doc-team），所有文档写 28 团 → 计数基准偏移 | _index.md + PLAN + TASKS + SKILL.md | 🔴 P0 验收全偏移 | 修正为 29 + 18 + 3 = 50 |

### B 类：v2.6 方案新增问题

| ID | 问题 | 严重度 | 修复 |
|----|------|--------|------|
| F1 | orchestrator 架构不符：方案说 build_team()，实际无此方法 | P0 | 拆出 team_builder.py 模块 |
| F2 | 285 独立专家=570+新文件，git checkout 无法回滚 untracked 文件 | P0 | migrate-workbuddy.py 增加 `--undo` + manifest.json |
| F3 | 现有测试绑定被移除的模块常量（WEIGHTS/THRESHOLDS） | P0 | 保留兼容性代理属性 |
| F4 | 三处独立计数无自动化校验 | P0 | 新增 audit-team-counts.py |
| F5 | 端到端验证依赖手工执行 | P0 | 改为自动化 test_e2e_pipeline.py |
| F6 | 285 独立专家 group_id 自动分配缺失 | P0 | T2.0 增加基于关键词的自动分组 |
| F7 | 空间估算低估（~3KB→实际 6-10KB/人，总计 ~2.3MB） | P0 | Tier 1 索引 agent_names 只记 count 不展开 |
| F8 | migration 脚本无撤销机制，无 manifest | P0 | 用 manifest.json 追踪创建的文件 |
| F9 | path-selector.py 的 `--force-team` 参数未实现 | P1 | T1.2 增加实现 |

---

## 🟡 强烈建议

| ID | 建议 | 来源 |
|----|------|------|
| S1 | S2 拆分: S2a(18+3团, 2天) + S2b(285独立专家, 3-5天并行S3) | debug-expert |
| S2 | 权重矩阵 PLAN ↔ weight-matrix.json 同步约束 | reviewer |
| S3 | 3-tier-hierarchical-loading.md 补充 task_type 参与粗筛说明 | reviewer |
| S4 | test_expert_matcher.py 增加 @pytest.mark.slow 标记 | debug-expert |
| S5 | 增加 prompts 质量门（格式/编码/过时检测） | debug-expert |
| S6 | token-ledger 写入点明确：在 team_builder 执行前后 | debug-expert |

---

## 修正后实施顺序

```
T0 (前置修复): B1 → B2 → B4 → B5 → F4 audit脚本
  ↓
S0 (三阶加载): F7 Tier 1 索引优化 → S3 文档补充
  ↓
S1 (匹配引擎): B3 team_builder.py → B4 阈值统一 → F9 --force-team
  ↓并行
S2a (18+3团): F2 manifest + --undo → F6 group_id 自动分配 → F8 撤销机制
  ↓
S2b (285独立专家) ← 与 S3 并行
  ↓并行
S3 (模板裁剪): F1 拆出 team_builder → S1 依赖标注
  ↓
S4 (评分卡): S6 写入点
  ↓
S5 (集成测试): F5 e2e 自动化 → S4 pytest.mark.slow → 全量回归
```
