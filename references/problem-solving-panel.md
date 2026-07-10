# 专家小组研讨 — Problem Solving Panel v1.0

> 基于 3 路专家并行分析结果（架构/风控/调研），构建可实施的「故障→专家研讨→方案→执行」管道。

---

## 架构定位

```
现有 escalate 策略（self_heal.py v2.0）：
  escalate → "请联系主理人处理"  ← 断链

增强后（v2.1）：
  escalate → [L0 预设规则] → [L1 单专家] → [L2 多专家研讨] → [L3 人类]
            每一层失败自动降级到下一层
```

### 与现有系统关系

| 组件 | 关系 |
|------|------|
| `self_heal.py` | escalate 策略的升级实现，替代原来的一句话返回 |
| `expert_matcher.py` | 用于组建专家小组（根据故障类型→知识域映射） |
| `cross-validation.md` | Phase 2 讨论结果的交叉验证（强制开启） |
| `self-evolution-protocol.md` | 研讨成果回流到 Loop 2 和 Loop 3 |
| `orchestrator.py` | 调用方，通过 `subprocess` 或直接导入调用 |
| `dependency-management.md` | 调研+研讨的异步依赖顺序控制 |

---

## 四层防御（L0→L1→L2→L3）

```
                              ┌─ L0 预设规则匹配 ──→ 60% 解决，$0
                              │   不匹配 ↓
 escalate 触发 ──→ PanelGuard ─┼─ L1 单专家深度 ───→ 25% 解决，~$0.57
                  (冷却/预算)   │   不解决 ↓
                              └─ L2 多专家研讨 ───→ 10% 解决，~$1.76
                                  不解决 ↓
                              L3 人类 escalate ───→ 5%，~$1.94(含先前消耗)
```

### 总计解决率：95%（可解故障），5% 需要人类介入

### ROI：17.3×（基准假设下）

---

## A. 触发条件与防护（PanelGuard）

### 触发规则矩阵

| 条件 | 行为 | 理由 |
|------|------|------|
| 故障 FT-04/FT-09/FT-10（非可恢复） | **强制触发** | 这些故障 retry/switch 无效，需要根因分析 |
| 故障 FT-07（连续退化） | **强制触发** | 可能影响后续所有任务，需深度诊断 |
| 故障 FT-02/FT-03 重试超限后升级 | **触发** | 重试失败表明存在深层原因 |
| 同团队同故障 <5min 重复 | **直接返回缓存** | 冷却期内结论不变 |
| 本次研讨 tokens > 120K 已使用 | **降级到 L1 单专家** | 预算保护 |
| 今日总研讨 tokens > 500K（全局） | **降级到 L3 人类** | 每日预算上限 |
| 故障 FT-01（AgentHang） | **不触发** | 直接 retry 即可 |

### PanelGuard 类

```python
class PanelGuard:
    def allow(self, team_id, fault_type, fault_key) -> str:
        # 返回值: "proceed" | "use_cache" | "downgrade_l1" | "block_l3"
        # 检查冷却期缓存
        # 检查预算
        # 检查故障类型是否在触发白名单
```

---

## B. 专家小组组建

### 故障类型 → 知识域映射

| 故障码 | 故障名 | 知识域 | 专家建议 | skeptics 建议 |
|--------|--------|--------|---------|-------------|
| FT-04 | Hallucination | NLP/AI_Methodology | 2 位 | 1 位（逻辑/推理方向） |
| FT-07 | Degradation | ML_Engineering/System | 2 位 | 1 位（可靠性方向） |
| FT-09 | DataSourcePoison | Data_Engineering/Security | 2 位 | 1 位（安全方向） |
| FT-10 | ConfigError | DevOps/System | 1 位 | — |

### 小组构成

| 厚度 | 专家数 | 配置 | 场景 |
|------|--------|------|------|
| light | 2 人 | 1 domain expert + 1 general | FT-10, FT-02/03 升级 |
| standard | 3 人 | 2 domain experts + 1 sceptic | FT-04, FT-07 |
| deep | 5 人 | 3 domain + 1 sceptic + 1 host | FT-09 |

**sceptic 角色**：强制包含（仅 light 模式除外），投票权重 ×1.5。

**host 角色**：deep 模式下需要，负责控制讨论秩序和投票流程。

### 匹配逻辑

```python
def form_panel(fault_type: str, thickness: str, dm) -> list[ExpertSlot]:
    domain = FAULT_TO_DOMAIN[fault_type]
    experts = expert_matcher.match(domain, top_k=thickness_config[thickness])
    # 确保包含 sceptic
    # 确保专家之间 source 多样化（防虚假共识）
```

---

## C. 三阶段研讨流程

### Phase 1: 独立调研（并行，每个专家独立）

每个专家收到的调研 prompt：

```
你被邀请作为专家小组的成员，解决以下故障：

故障类型: {fault_type} - {description}
故障上下文: {agent_id}, {error_message}, {signal_chain}
当前会话历史: {recent_3_events}

请完成以下工作：
1. 互联网搜索：搜索 3-5 个相关信息源
2. 本地资产点检：
   - 检查 references/knowledge/ 中的相关知识
   - 检查 repair-records 中类似的修复记录
   - 检查 self-evolution-log 中的学习记录
3. 输出 2-3 个解决方案，每个方案包含：
   - 方案名称
   - 具体步骤
   - 推荐理由
   - 风险与前提条件
   - 实施难度（Easy/Medium/Hard）
4. 在最后对自己方案的置信度评分（0-1）
```

**成本控制**：
- 调研 URL 数：light=2, standard=3, deep=4
- 调研超时：60s（软限制，超时后仅用本地资产）
- 输出格式：结构化 JSON

### Phase 2: 跨源讨论（串行，≤3 轮）

```
第 1 轮 — 方案展示：
  每个专家展示自己的 2-3 个方案（3 分钟内）

第 2 轮 — sceptic 优先辩论：
  sceptic 对每个方案提出质疑
  方案提出者回应
  其他专家补充

第 3 轮 — 交叉验证 + 投票：
  Layer 1.5 交叉验证开启（来源独立性检查）
  加权投票（domain expert 1.0, sceptic 1.5, host 1.2）
  产出排名
```

**终止条件**（任一满足即止）：
- 所有专家同意某个方案（置信度 ≥ 0.85）
- 讨论轮次达到上限（3 轮）
- 总讨论 token 超过预算（20K）
- 共识收敛检测：连续两轮排名不变

### Phase 3: 方案执行或交付

| 条件 | 行为 |
|------|------|
| 置信度 ≥ 0.85 且风险 < L3 | **自动执行**：调用执行器，标记 auto_generated |
| 置信度 ≥ 0.85 但风险 L3+ | **自动执行 + @reviewer 复审** |
| 置信度 0.50~0.84 | **推荐给用户**：展示方案列表+评分+推荐，让用户选择 |
| 置信度 < 0.50 或无法达成一致 | **L3 人类 escalate**：当前 escalate 行为 |

**效果验证**：
```python
def verify_solution(solution, fault_context):
    # 执行方案
    # 检查故障是否消失（re-run diagnosis）
    # 检查副作用（regression check）
    # 记录结果
```

---

## D. 成本控制

| 控制项 | 上限 | 超限处理 |
|-------|------|---------|
| 每专家调研 URL 数 | light=2, standard=3, deep=4 | 超限仅用本地资产 |
| 讨论轮次 | 3 轮 | 超限自动选当前最优 |
| 每场研讨总 tokens | 120K | 降级到 L1 单专家 |
| 每日总研讨 tokens | 500K | 降级到 L3 人类 |
| 每场研讨总时间 | 180s | 超限取当前进度最佳结果 |
| 同故障冷却期 | 5min | 直接返回缓存结论 |

---

## E. 熔断与故障处理

### 研讨状态机

```
IDLE → PANEL_FORMING → RESEARCH_PHASE → DISCUSSION_PHASE → DECISION_PHASE → COMPLETED
                                                                              ↓
                                                                         FAILED → IDLE (冷却)
```

### 异常场景处理

| 场景 | 处理 |
|------|------|
| 专家匹配失败 | fallback 到单专家（general agent） |
| 调研超时 | 仅用本地资产，标记 `research_incomplete` |
| 讨论不收敛（振荡） | 锁定第 1 轮投票结果，标记 `not_converged` |
| 投票平局 | host/系统加权票决定 |
| 执行失败 | 自动回滚 + 降级到 L3 |
| 缓存过期 | 重新触发完整流程（冷却期已过） |

### 熔断器

```python
class PanelCircuitBreaker:
    # 连续 2 次 PANEL_BROKEN → 冷却 30min
    # 冷却期内所有 escalate 直接走 L3
    # 自动恢复后允许 1 次探测
```

---

## F. 研讨成果沉淀

每场研讨结束后，自动：

1. **记录修复案例**（存入 `shared/team-brain/repair-records/`）：
   ```json
   {
     "case_id": "C-20260708-001",
     "fault_type": "FT-04",
     "symptoms": ["LOW_CONFIDENCE", "HIGH_TRACE_FAIL"],
     "solutions": [...],
     "selected_solution": "...",
     "confidence": 0.85,
     "auto_generated": true,
     "created": "2026-07-08T12:00:00",
     "verdict": "PASS" | "FAIL" | "pending"
   }
   ```

2. **触发 Loop 1**：追加到 `self-evolution-log.md`
3. **触发 Loop 2**：更新 expert-scores（方案被采纳→加分，方案导致新问题→扣分）
4. **触发 Loop 3**：如果同一故障模式出现 3 次以上，生成预设修复规则（L0）

---

## G. 实施路径（3 阶段）

### Phase 0: 改进 escalate 上下文（1 天，0 风险）

**当前**：`"请联系主理人处理"`  
**改为**：输出完整的诊断链路报告（信号链 + 故障码 + 已尝试策略 + 推荐方向）

改动范围：仅修改 `self_heal.py` 中的 escalate 策略返回内容。

### Phase 1: 单专家方案（3-5 天）

- 实现 `problem_solver.py`（仅 L1 部分）
- 只调用 1 个领域专家
- 输出方案列表 + 置信度
- 不自动执行

### Phase 2: 多专家研讨（1-2 周）

- 完整 Phase 1 + 2 + 3
- 3 专家标准流程
- sceptic 角色
- 交叉验证

### Phase 3: 自动执行 + 知识回流（2-4 周）

- 置信度高时自动执行
- CBR 案例库
- L0 预设规则自动生成

---

## 参考

- `scripts/self_heal.py` — 自愈管道入口
- `scripts/problem_solver.py` — 本功能实现
- `references/expert-matching.md` — 专家匹配
- `references/cross-validation.md` — 方案交叉验证
- `references/self-healing-architecture.md` — 自愈架构
- 调研报告（互联网）— 辩论轮次收益递减在第 3 轮
- 风控报告 — ROI 17.3×，安全边际极宽
