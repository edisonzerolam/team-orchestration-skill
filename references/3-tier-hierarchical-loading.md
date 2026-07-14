# 三阶层次化加载 + 热/温/冷分级 + Token 预算管理

版本: v2.6 追加设计
审计状态: 待审
关联: `PLAN-v2.6-enhancement.md` P0-6

---

## 一、问题定义

| 问题 | 影响 |
|------|------|
| `load_all_experts()` 全量加载所有团（31团×~300文件I/O） | 每次匹配扫描 5-10MB，实际只用 Top-3 |
| 无热/温/冷区分，冷团占用与热团相同资源 | 冷团 30 天未用但每次匹配仍全量加载 |
| 大团全部 agent .md 加载后执行 | 中等复杂度任务只需要大团中 30% 的 agent |
| 无 Token 预算上限 | 单次匹配+执行可能消耗 150K+ tokens |
| 无执行后 Token 记账 | 无法量化优化效果 |

**优化目标**: 匹配阶段 Token 消耗降低 85%+，执行阶段通过裁剪+分级再降 40-78%

---

## 二、核心架构：三阶层次化加载

```
执行链路原貌:
  task → decomposer → matcher(load_all 31团) → path-selector → orchestrator

三阶优化后:
  task → decomposer ─→ matcher(Tier 1: teams-index.json, ~4KB)
                            ↓ (先粗筛到 Top-10 候选)
                         matcher(Tier 2: plugin.json × Top-10, ~100KB)
                            ↓ (精确评分到 Top-3)
                         path-selector ─→ orchestrator(Tier 3: agent .md × 1团, ~200KB)
                                                        ↓ (延迟到执行前才加载)
                                                     _execute_single()
```

### 各层定义

| 层级 | 数据源 | 大小 | 文件I/O | 加载时机 | 缓存策略 |
|------|--------|------|---------|---------|---------|
| **Tier 1** | `shared/teams-index.json` | ~4KB | 1 次 | 技能启动时预加载 | L1: 永不过期 |
| **Tier 2** | 候选团 `plugin.json` × 5-10 | ~20-100KB | 5-10 次 | 粗筛命中 Top-K 时 | L2: 5min TTL |
| **Tier 3** | 选中团 `agents/*.md` × 1 | ~200KB | ~10 次 | orchestrator 执行前 | L3: 用完即弃 |

### 状态机

```
UNINITIALIZED
  ↓ (技能首次加载)
TIER1_LOADED  ←←←←←←←←←←←←  L1 索引永不过期
  ↓ (match() 被调用，粗筛出 Top-10)
TIER2_LOADED  ←←←←←←←←←←←←  L2 5min TTL，过期后自动重载
  ↓ (path-selector 确认执行路径)
TIER3_READY   ←←←←←←←←←←←←  L3 不缓存，换团时自动释放
  ↓ (orchestrator 开始执行)
EXECUTING
  ↓ (下次 match() 调用)
TIER1_LOADED  (回到起点，Tier 2/3 按需逐出)
```

---

## 三、热/温/冷分级

### 分级定义

| 级别 | 使用时间 | 加载行为 | 匹配优先级 | 缓存 |
|------|---------|---------|-----------|------|
| 🔥 **Hot** | < 7天 | 全路径：Tier 1 → Tier 2 → Tier 3 + scores | 正常 | L1+L2 |
| 🔶 **Warm** | 7-30天 | 只加载 plugin.json，agent .md 按需懒加载 | ε-greedy 探索 | L2 only |
| 🔵 **Cold** | > 30天 | 仅扫描 Tier 1 索引，不加载详情 | 仅当 ε-greedy 或用户指定 | L1 only |

### 自动升降级

| 触发事件 | 动作 |
|---------|------|
| 团队被匹配并执行完成 | → **Hot**，重置 `last_used_at` |
| 每日巡检：`last_used_at > 7d` | → **Warm** |
| 每日巡检：`last_used_at > 30d` | → **Cold** |
| Warm 团在 ε-greedy 探索中命中 | → **Hot** |
| Hot 团连续 3 次匹配但未被选中 | → **Warm**（自动衰减） |
| 显式 `--refresh-cache` 或用户指定 | 临时升级到 Hot 一次 |

### 数据结构

```json
// shared/teams-tier.json
{
  "_meta": {
    "updated_at": "2026-07-10T10:00:00Z",
    "schema_version": 1
  },
  "investment-masters-team": {
    "state": "cold",
    "last_used": null,
    "use_count_since_reset": 0,
    "match_hit_rate": 0.0
  },
  "chatlaw-team": {
    "state": "warm",
    "last_used": "2026-07-10T09:45:00Z",
    "use_count_since_reset": 3,
    "match_hit_rate": 0.45
  }
}
```

---

## 四、Token 预算管理

### 三级预算模式

```json
// shared/budget-config.json
{
  "modes": {
    "turbo":   { "per_team_budget": 150000, "agent_md_mode": "full",         "max_agents": 12, "match_top_k": 5 },
    "standard":{ "per_team_budget": 120000, "agent_md_mode": "full",         "max_agents": 8,  "match_top_k": 3 },
    "economy": { "per_team_budget": 60000,  "agent_md_mode": "standby_meta", "max_agents": 5,  "match_top_k": 2 }
  },
  "default_mode": "standard",
  "auto_downgrade_threshold": 0.85,
  "daily_global_budget": 500000
}
```

### BudgetController 核心逻辑

```python
class BudgetController:
    def check_budget(self, team_name, agent_count):
        """返回 BudgetVerdict: {allowed, mode, max_agents, agent_load_policy}"""
        ratio = self._calc_usage_ratio(team_name)
        if ratio >= 0.85:
            return {"allowed": True, "mode": "economy",
                    "agent_load_policy": "standby"}  # 尾部 agent 只加载元数据
        elif ratio >= 0.60:
            return {"allowed": True, "mode": self.mode,
                    "agent_load_policy": "standby_for_tail"}  # 后 30% agent 元数据
        else:
            return {"allowed": True, "mode": self.mode,
                    "agent_load_policy": "full"}
```

### Standby Agent 机制

- **Active**: 完整加载 agent.md，参与执行
- **Standby**: 只加载 agent 角色摘要（~200 tokens vs 2000-5000 tokens），仅提供 backup

```
完整 agent.md (2000-5000 tokens) → Standby 元数据 (~200 tokens)
节省: 90-96% Token/agent
```

---

## 五、缓存逐出策略

| 级别 | 内容 | TTL | 逐出策略 |
|------|------|-----|---------|
| L1 | teams-index.json | 永不过期 | 仅当新增/删除团时手动 `--rebuild-index` |
| L2 | plugin.json × N | 300s | TTL 过期 → 重读；`--refresh-cache` → 全清 |
| L3 | agent .md | 0 | 每次使用后释放，不缓存 |
| L0（新增） | Tier 状态 / Budget 裁决 | 600s | 用于热/温/冷分级判断，减少重复 I/O |

`--refresh-cache` 命令：清除全部 L2 缓存，强制重新加载 plugin.json。L1 索引不变。

---

## 六、Token 记账

### 执行链路 Token 记录

每个子任务执行前后记录 token 增量，汇总到 `shared/token-ledger.json`:

```json
{
  "global_usage_today": 245000,
  "global_usage_date": "2026-07-10",
  "teams": {
    "investment-masters-team": {
      "sessions": [
        {"ts": "2026-07-10T10:00:00Z", "cost": 12345, "agent_count": 8, "mode": "standard"}
      ],
      "agent_loading_ratio": 0.36
    }
  }
}
```

在 `shared/expert-scores.json` 中扩展 token_cost 字段:
```json
{
  "token_cost": {
    "last": 12345,
    "average": 11800,
    "history": [12345, 10800, 13500],
    "per_agent": {"trader-agent": 3500, "analyst-agent": 4200},
    "per_phase": {"research": 5000, "analysis": 3000, "generation": 2000}
  }
}
```

---

## 七、集成路径（与现有代码的关系）

```
现有链路:
  match(domains, abilities) → load_all_experts() → 全量评分 → top-k

新链路:
  match(domains, abilities)
    → 1. load_experts_light()  ← 只读 teams-index.json (Tier 1)
    → 2. 粗筛到 Top-10 候选    ← 轻量评分
    → 3. load_experts_detail(candidates)  ← 只读候选团的 plugin.json (Tier 2)
    → 4. 精确评分到 Top-3
    → 5. orchestrator 执行前 → load_agents_lazy(team) (Tier 3)

向后兼容:
  - load_all_experts() 保留不删（标记 deprecated）
  - teams-index.json 不存在时自动回退到 load_all_experts()
  - match() 返回值结构不变（不影响 path-selector、测试用例）
```

---

## 八、关键数据结构汇总

### shared/teams-index.json（Tier 1 索引）

每团 ~150 字节，49 团 ≈ 7KB：
```json
{
  "investment-masters-team": {
    "name": "investment-masters-team",
    "display_zh": "投资大师专家团",
    "description_zh": "13位投资大师+6位分析师并行分析...",
    "category_id": "08-FinanceInvestment",
    "expert_type": "team",
    "lead_name": "贺知衡",
    "agent_count": 22,
    "agent_names": ["hedge-fund-lead", "oracle-of-omaha", ...],
    "capabilities": ["AI Hedge Fund orchestrator", "investment analysis", ...]
  },
  ...
}
```

### shared/token-budget.json（Token 预算配置）

```json
{
  "investment-masters-team": {
    "total_tokens": 38200,
    "agent_count": 22,
    "estimated_tokens_per_agent": 1736
  },
  "chatlaw-team": {
    "total_tokens": 14500,
    "agent_count": 6,
    "estimated_tokens_per_agent": 2417
  }
}
```

---

## 九、文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **新增** | `shared/teams-index.json` | Tier 1 索引（脚本生成，~7KB） |
| **新增** | `shared/teams-tier.json` | 热/温/冷分级状态 |
| **新增** | `shared/budget-config.json` | 三级预算配置 |
| **新增** | `shared/token-budget.json` | 各团预估 Token 消耗 |
| **新增** | `shared/cache-config.json` | 三级缓存配置 |
| **新增** | `shared/token-ledger.json` | 全局 Token 账本 |
| **新增** | `scripts/budget-controller.py` | BudgetController 类 |
| **修改** | `scripts/expert_matcher.py` | 三阶加载 + 分级判断 |
| **修改** | `scripts/path-selector.py` | Token 预估 + 预算降级 |
| **修改** | `scripts/orchestrator.py` | Tier 3 懒加载 + TokenAccount |
| **修改** | `scripts/migrate-workbuddy.py` | 集成 build_teams_index() |
| **修改** | `shared/expert-scores.json` | 扩展 token_cost 字段 |
| **修改** | `SKILL.md` | 新增分级说明 |
| **修改** | `shared/expert-scores.json` | 扩展 token_cost 字段 |

---

## 十、验收标准

1. **Tier 1**: `load_experts_light()` 仅读 1 个文件，返回 49 团轻量索引
2. **Tier 2**: `load_experts_detail()` 只读指定团 plugin.json，不读 agent .md
3. **Tier 3**: `load_agents_lazy()` 在 orchestrator 执行前才加载 agent .md
4. **分级**: Cold 团匹配时 Zero agent .md 读取
5. **降级**: 预算超过 85% 时自动切换到 economy 模式
6. **Standby**: Standby agent 元数据 ≤ 200 tokens
7. **向后兼容**: teams-index.json 缺失时自动回退 load_all_experts()
8. **全量回归**: `pytest tests/ -v` 全部通过（三阶加载不破坏现有测试）
