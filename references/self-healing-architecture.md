# Self-Healing 自愈架构设计（v1.0）

> Team Orchestration 多 Agent 编排框架的自愈体系设计。
> 替代 `self_heal.py` v1.0.0 的错误分类+重试机制，建设完整的故障检测→诊断→恢复→验证管道。

---

## 架构总览

```
                        ┌──────────────────────────────────────┐
                        │           Orchestrator               │
                        │  (10 步工作流调度器)                   │
                        └──────────┬───────────────────────────┘
                                   │ 委托 Agent
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Self-Healing 管道                              │
│                                                                  │
│   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐      │
│   │Detector │──▶│Diagnoser │──▶│ Healer  │──▶│Verifier │      │
│   │故障检测  │   │故障诊断   │   │故障恢复  │   │故障验证  │      │
│   └───┬─────┘   └──────────┘   └────┬────┘   └────┬────┘      │
│       │                              │              │           │
│       ▼                              ▼              ▼           │
│  信号来源池                     恢复策略库       验证策略库      │
│  · 心跳超时                     · 重试(退避)    · 功能验证      │
│  · 工具异常                     · 降级          · 副作用扫描    │
│  · 输出异常                     · 回滚          · 一致性检查    │
│  · 质量评分低                   · 切换          · 回归检查      │
│  · 超时                         · 熔断                         │
│                                 · 跳过                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              集成层                                               │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ Health-Monitor│  │ Self-Evolution │  │ Repair Records   │   │
│  │ 心跳+存活检测  │  │ Loop 1/2/3    │  │ F2/F3/F4/...    │   │
│  └──────────────┘  └────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## A. 故障分类学

### A1. 故障类型完整定义

| 编号 | 故障类型 | 严重度 | 可恢复性 | 检测信号 | 典型恢复策略 |
|------|---------|--------|---------|---------|-------------|
| FT-01 | **Agent 僵死 (AgentHang)** | L1 | recoverable | 心跳连续 N 次无响应；状态停留在 In Progress 超过 TTL | 强制 Kill → 重调度 |
| FT-02 | **工具调用失败 (ToolFailure)** | L1-L2 | recoverable | 工具返回非零退出码/网络错误/超时；幂等性检查 | 指数退避重试(≤3次) → 切换工具 |
| FT-03 | **输出质量不合格 (OutputQuality)** | L2 | recoverable | 贝叶斯置信度 < 0.6；审核门 FAIL；交叉验证冲突 | 退回重做 → 换 Agent 重做 |
| FT-04 | **语义坍缩/幻觉 (Hallucination)** | L2-L3 | partial | 输出中包含未在来源中出现的声明；来源追溯失败比例 > 30% | 回退到已知正确版本 → 切换模式 |
| FT-05 | **依赖 Agent 故障 (DependencyFail)** | L2 | recoverable | 前置 Agent 状态为 Failed / Hanging；子任务 DAG 中的前驱节点异常 | 等待(带超时) → 跳过 → 降级 |
| FT-06 | **上下文预算溢出 (ContextOOM)** | L3 | recoverable | token 利用率 > 85%；压缩失败率 > 50% | 强制摘要 → 裁剪上下文(到 60%) |
| FT-07 | **连续退化 (Degradation)** | L3-L4 | non-recoverable | expert-score 连续下降 ≥ 3 次；Aβ > 1.5 连续 ≥ 2 次 | 熔断 → 冷却该专家 → 触发 Loop 3 重新校准 |
| FT-08 | **跨 Agent 死锁 (Deadlock)** | L3 | partial | 两个 Agent 相互等待对方输出形成环；无进展循环 ≥ 3 轮 | 超时中断 → 主理人裁决 |
| FT-09 | **数据源污染 (DataSourcePoison)** | L4 | partial | 多个 Agent 使用了同一个有问题的数据源且产出相互验证为假 | 回滚所有依赖该源的结果 → 重调度替代来源 |
| FT-10 | **配置/环境错误 (ConfigError)** | L4 | non-recoverable | Agent 初始化失败；skill 加载错误；依赖缺失 | 上报主理人 → 写入 install-fix 记录 |

### A2. 严重度定义

| 级别 | 含义 | SLO | 自动化程度 |
|------|------|-----|-----------|
| **L1** | 单 Agent 短暂异常，不影响整体 | < 30s | 全自动，无需上报 |
| **L2** | 单 Agent 异常，影响下游 1-2 个节点 | < 2min | 自动恢复，记录日志 |
| **L3** | 多个 Agent 异常或核心 Agent 不可用 | < 5min | 自动降级 + 通知主理人 |
| **L4** | 系统性崩溃，整个工作流不可用 | — | 立即中止 + 上报主理人裁决 |

### A3. 故障类型 → 严重度矩阵（按阶段映射）

| 工作流阶段 | 可能故障 | 默认严重度 | 降级目标 |
|-----------|---------|-----------|---------|
| 目标明确 | Hallucination, ContextOOM | L2 | 回到人工澄清 |
| 任务拆解 | ToolFailure | L1 | 重试脚本 |
| 预验尸 | AgentHang, ConfigError | L2-L4 | 跳过此 Agent |
| 专家匹配 | ToolFailure, ConfigError | L2 | 降级到简单规则匹配 |
| 执行 | AgentHang, ToolFailure, OutputQuality | L1-L3 | 重试/切换/降级 |
| 交叉验证 | DependencyFail, Deadlock | L2-L3 | 自动解决/上报 |
| 审核门 | OutputQuality | L2 | 退回重做 |
| 交付 | — | — | — |
| 反馈进化 | Degradation | L3 | 冷却/Loop 3 |

---

## B. 自愈管道架构（4 阶段）

### B1. 故障检测模块 (Detector)

#### 检测器类型

```
┌────────────────────────────────────────────────────────────────┐
│                      Detector Registry                          │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │HeartbeatWatch │  │ToolCallWatch │  │OutputQuality  │        │
│  │Agent 心跳看门狗 │  │工具调用监控    │  │Watch 输出质量  │        │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤        │
│  │ interval: 5s │  │  捕获:       │  │  检查:       │        │
│  │ timeout: 30s │  │  · 退出码    │  │  · 置信度    │        │
│  │ miss_limit: 3│  │  · 错误输出  │  │  · 声明追溯  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │TimeoutWatch  │  │CircuitBreaker│  │ScoreTrendWatch│        │
│  │超时监控       │  │熔断器状态监控  │  │评分趋势监控    │        │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤        │
│  │ 阶段级超时   │  │ 状态机:     │  │ expert-score │        │
│  │ 全局超时     │  │ CLOSED/OPEN │  │ 下降斜率检测  │        │
│  │ Agent 级超时 │  │ /HALF_OPEN  │  │ 退化检测      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

#### 检测信号流

```
信号来源           采样频率        输出                       消费方
──────            ────────       ────                       ────
HeartbeatWatch     每 5s          AgentStatus(id, state,      Diagnoser
                                 last_heartbeat, miss_count)
ToolCallWatch      每调用触发       ToolResult(id, exit_code,    Diagnoser
                                 stdout, stderr, duration_ms)
OutputQualityWatch 每交付触发       QualityVerdict(id, score,    Diagnoser
                                 sources[], confidence)
TimeoutWatch       每阶段检查       TimeoutEvent(id, phase,     Diagnoser
                                 elapsed_ms, threshold_ms)
CircuitBreaker     每次恢复动作后    CBState(id, state,          Diagnoser + Healer
                                 failure_count, last_failure)
ScoreTrendWatch    每次 Loop 2 后   TrendReport(expert_id,      Loop 3
                                 slope, consecutive_drops)
```

### B2. 故障诊断模块 (Diagnoser)

#### 诊断流程

```
检测信号到达
    │
    ▼
┌──────────────────────┐
│  信号归一化层          │  ← 将各检测器输出统一为 DiagnosisSignal
│  (Signal Normalizer)  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  关联分析层            │  ← 关联多个信号确认故障存在
│  (Correlation Engine) │     例：心跳缺失 + 工具调用超时 → AgentHang
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  根因定位层            │  ← 5Why 推理得出最可能故障类型
│  (Root Cause Mapper)  │     返回 (fault_type, severity, confidence)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  策略推荐层            │  ← 根据 fault_type + fault_history
│  (Strategy Recommender)│     推荐恢复策略 + 参数
└──────────────────────┘
```

#### 信号→故障映射规则（示例）

| 信号组合 | 故障类型 | 置信度规则 |
|---------|---------|-----------|
| Heartbeat {miss_count ≥ 3} | AgentHang | 高置信度(>0.9) |
| ToolCall {exit_code ≠ 0} + Heartbeat {miss_count = 0} | ToolFailure | 高置信度(直接观测) |
| QualityVerdict {confidence < 0.6} + {cross_validation_conflict > 0} | OutputQuality | 高置信度(>0.9) |
| ToolCall {exit_code = 0} + QualityVerdict {source_trace_fail_rate > 0.3} | Hallucination | 中等置信度(0.7) |
| Timeout {phase='expert_matching'} + ToolCall {name='expert_matcher.py', exit_code ≠ 0} | ConfigError | 中等置信度(0.75) |
| 多个 Agent 同时 Timeout | DependencyFail | 中等置信度(需核验前置) |
| TrendReport {consecutive_drops ≥ 3} + CBState {state=CLOSED} | Degradation | 高置信度(趋势明确) |
| score_trend + heartbeat OK + tool OK | Degradation | 中等置信度(排除其他) |

#### 诊断输出格式

```python
@dataclass
class DiagnosisResult:
    fault_type: str          # FT-01 ~ FT-10
    severity: int            # L1-L4
    confidence: float        # 0.0-1.0
    agent_id: str
    signal_chain: list[str]  # 哪些信号导致此诊断
    recommended_strategy: str  # retry/degrade/rollback/switch/circuit_break/skip
    params: dict             # 恢复策略参数
    timestamp: str
```

### B3. 故障恢复模块 (Healer)

#### 恢复策略库

| 策略 | 适用故障 | 动作 | 副作用防护 |
|------|---------|------|-----------|
| **retry** | ToolFailure, AgentHang | 重新执行该 Agent（保留 context） | 幂等性检查；max_retries=3 |
| **degrade** | OutputQuality, Hallucination | 降低验证深度(deep→standard→light) 或 降低输出质量要求 | 标注「已降级」到最终产出 |
| **rollback** | DataSourcePoison, Hallucination | 回滚到上一个已知正确版本的输出 | 快照所有中间状态 |
| **switch** | ToolFailure(重试失败), Degradation | 切换到备用 Agent/工具/数据源 | 记录切换原因到日志 |
| **circuit_break** | Degradation, Deadlock | 熔断该 Agent 或该路径 | 写入黑名单(冷却期) |
| **skip** | DependencyFail, OutputQuality(非关键) | 跳过该子任务，视作已完成 | 在最终报告中标记为「已跳过」 |
| **escalate** | ConfigError, 所有 3 次恢复失败 | 上报主理人裁决 | 附带完整诊断链路 |

#### 指数退避策略

```
重试间隔公式:
  delay = base_delay × multiplier^attempt + jitter
  其中:
    base_delay  = 2s (L1) / 5s (L2) / 10s (L3)
    multiplier  = 2 (ToolFailure) / 1.5 (DependencyFail)
    jitter      = random(0, 0.3 × delay)  防惊群

退避表 (base_delay=2s, multiplier=2):
  attempt 1: 2s + jitter
  attempt 2: 4s + jitter
  attempt 3: 8s + jitter
  max: 3 attempts, 超过 → 切换策略
```

#### 熔断器状态机

```
       连续恢复成功 N 次
  ┌──────────────────────────┐
  │                          │
  ▼                          │
┌────────┐    失败次数≥阈值    ┌────────┐
│ CLOSED │──────────────────▶│  OPEN  │
│ (正常)  │                  │ (熔断)  │
└────────┘                   └────────┘
  ▲                               │
  │         超时冷却完成            │
  │  ┌───────────────────────┐    │
  │  │                       │    │
  │  ▼                       │    │
  │ ┌──────────┐  尝试恢复(1次) │    │
  │ │HALF_OPEN │◀──────────────┘    │
  │ │ (半开)   │────────────────────┘
  │ └──────────┘  再次失败
  │
  └───────────────────────────────────┘
         冷却期过半时自动进入 HALF_OPEN

参数:
  failure_threshold = 3  (连续失败次数触发 OPEN)
  cooldown_period   = 60s (OPEN→HALF_OPEN)
  success_threshold = 2  (连续成功次数 HALF_OPEN→CLOSED)
```

#### 恢复策略选择决策树

```
DiagnosisResult 到达
    │
    ▼
┌──────────────────────────────────────────┐
│ severity == L4 ?                         │
│   → escalate (上报主理人)                  │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ fault_type in [Degradation, Deadlock] ?  │
│   → circuit_break                        │
│     尝试次数 ≥ 3 ? → escalate            │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ fault_type == AgentHang ?                │
│   → kill_agent → switch(retry)           │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ fault_type in [ToolFailure, Timeout] ?   │
│   → retry (指数退避)                      │
│     重试 3 次失败 → switch               │
│     switch 失败 → degrade                │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ fault_type in [OutputQuality,            │
│              Hallucination] ?            │
│   → retry_with_modified_prompt           │
│     重试失败 → switch_agent              │
│     switch 失败 → degrade → 标注         │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ fault_type == DependencyFail ?           │
│   → wait_for_dependency (带超时)           │
│     超时 → skip (标记跳过)                │
└──────────────────────────────────────────┘
```

### B4. 故障验证模块 (Verifier)

#### 验证策略库

| 验证策略 | 适用场景 | 检查项 | 通过标准 |
|---------|---------|-------|---------|
| **功能复查** | ToolFailure 恢复后 | 工具输出完整、格式正确 | 输出 schema 校验通过 |
| **质量审查** | OutputQuality 恢复后 | 贝叶斯置信度 ≥ 0.7；来源追溯率 ≥ 80% | 各项均达标 |
| **副作用扫描** | degrade/switch/rollback 后 | 检查下游 Agent 是否出现新异常 | 下游不在同一路径上出错 |
| **一致性检查** | Hallucination 恢复后 | 新的声明是否能被至少 2 个独立来源验证 | 三角测量通过 |
| **回归检查** | 任何恢复后 | 恢复前已知正确的断言是否仍然成立 | 回归覆盖率 ≥ 90% |

#### 验证流程

```
恢复动作完成
    │
    ▼
┌──────────────────────────┐
│ 选验证策略 (按恢复策略映射)  │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│ 执行验证 (独立子过程)       │  ← 避免验证和恢复耦合
│  · 不重用恢复用的 context  │
│  · 温度 ≤ 0.2             │
└──────────┬───────────────┘
           ▼
    ┌──────┴──────┐
    ▼              ▼
┌────────┐   ┌──────────────┐
│PASS    │   │ FAIL          │
│  ─▶ 交付  │   │  ─▶ 返回 Diagnoser│
└────────┘   │    重新诊断    │
             │    最多 2 轮   │
             └──────┬───────┘
                    ▼ 第 2 轮仍 FAIL
              ┌──────────────┐
              │ escalate     │
              │ (上报主理人)   │
              └──────────────┘
```

#### 验证输出格式

```python
@dataclass
class VerificationResult:
    verifier_id: str
    verdict: Literal["PASS", "FAIL", "CONDITIONAL"]
    recovery_action: str           # 对应的恢复动作 ID
    checks_passed: list[str]       # 通过的检查项列表
    checks_failed: list[str]       # 未通过的检查项列表
    side_effects: list[str]        # 检测到的副作用
    regressions: list[str]         # 回归问题
    confidence: float              # 验证本身的置信度
    timestamp: str
```

---

## C. 与现有系统的集成

### C1. 与 health-monitor.py 联动

```
Health-Monitor (现状)                  Self-Healing (新增)
─────────────────                    ────────────────
· 心跳检测 (5s 间隔)                    ┌─→ Detector.HeartbeatWatch
· Agent 存活/僵死/失败状态判断            │   复用 health-monitor 的心跳数据
· 状态转换事件推送                       │
                                       │
状态变更事件 (EventBus)                 │
  AgentHang(found_new) ────────────────┼─→ Diagnoser (作为检测信号之一)
  AgentAlive(restored) ────────────────┤
  AgentFailed(fatal) ─────────────────┤
                                       │
Health-Monitor 新增接口:                  │
  register_watchdog(agent_id, cb) ─────┘
  get_agent_status(agent_id) → State
```

### C2. 与 Self-Evolution Protocol (Loop 1/2/3) 联动

```
Self-Healing 管道                   三环自进化协议
─────────────────                   ──────────────

Detector 输出                          Loop 1 (执行层, 秒级)
  · 每次检测信号 ──────────────────────▶ · 追加 to self-evolution-log.md
  · 检测频率、准确率、误报率统计            · LoopGain Aβ 增益监控
                                         · 上下文预算更新

Diagnoser 输出                          Loop 2 (策略层, 分钟级)
  · 每次诊断结论 ──────────────────────▶ · 更新 expert-scores.json
  · 故障类型的分布统计                     · 退化检测 (consecutive_drops ≥ 3)
  · 各 Agent 的故障频率                    · 收敛速度记录
                                         · 恢复策略效果评估

Healer 输出                             Loop 3 (元学习层, 小时/天级)
  · 恢复效果 (成功/失败) ──────────────▶ · 新增恢复策略模式到 knowledge 文件
  · 降级操作记录                          · 更新 expert_matcher 权重
  · 熔断器历史                            · 世界模型刷新
  · 切换后的 Agent 表现对比
```

#### 双向数据流

```
Self-Healing → Evolution:
  · 每次恢复成功/失败 → LoopGain 更新
  · 每类故障的频率变化 → 退化检测输入
  · 恢复策略效果 → Polyak 平均的一部分
  · 熔断事件 → Loop 3 元学习素材

Evolution → Self-Healing:
  · Loop 2 更新的 expert-score → 影响 Degradation 判断阈值
  · Loop 3 新增的恢复策略 → Healer 策略库扩展
  · 世界模型中的 Agent 能力变化 → Diagnoser 的置信度校准
  · 用户纠正模式 → 影响信号→故障映射规则的优先级
```

### C3. 与 Orchestrator Repair Records 集成

```
Orchestrator 修复记录 (F2/F3/F4/F5/F6/F10/F11)
  ────────────────────────────────────────────
  · 每条修复记录 = 一个已知的故障→恢复映射
  · 自愈管道的 Diagnoser 首先查询修复记录

集成方式:
  1. 修复记录 → 预置规则
     orchestrator 中所有 F* 记录在启动时被载入
     Diagnoser 的策略推荐层优先匹配已知修复模式

  2. 新故障 → 新修复记录
     Healer 成功恢复一个未知类型的故障后 →
     自动生成新的修复记录 (F12, F13, ...) →
     写入 orchestrator 的修复记录库

  3. 修复记录效果追踪
     每次通过修复记录恢复的故障 →
     记录恢复成功/失败率 →
     低成功率(≤60%)的修复记录标记为 stale →
     由 Loop 3 决定是否更新或废弃

修复记录结构 (与现有兼容):
  repair_record = {
      "id": "F12",
      "fault_type": "ToolFailure",
      "signal_pattern": "exit_code=1 AND cmd=~expert_matcher",
      "strategy": "retry",
      "params": {"max_retries": 3, "base_delay_s": 2, "multiplier": 2},
      "effectiveness": 0.85,    # 成功/总尝试
      "last_used": "2026-07-08T16:00:00Z",
      "stale": False
  }
```

---

## D. 失效模式分析

### D1. Team Orchestration 特有失效模式

| 编号 | 失效模式 | 触发条件 | 当前处理方式 | 自愈后处理方式 |
|------|---------|---------|------------|--------------|
| FM-01 | **Agent 无限循环 (Infinite Loop)** | Subagent 在 Pre-task Discussion 或 In Progress 状态中无进展重复输出 ≥ 3 轮相同内容 | 无检测机制，用户最终卡住 | Detector.TimeoutWatch 检测到无产量时间 > 阈值 → Diagnoser 判定为 Deadlock → Healer 中断 → switch Agent |
| FM-02 | **交叉验证假冲突 (False Conflict)** | 两个 Agent 给出看似矛盾实则可兼容的分析，因表述方式不同被误判为冲突 > 3 次 | 交叉验证 Layer 1.5 无冲突消解，直接标记失败 | Diagnoser 关联分析发现冲突双方来源独立但结论相近 → 降验证深度到 light → 标注「假冲突」到日志 |
| FM-03 | **审核门 3 轮无效 (Review Looping)** | @reviewer 连续 3 轮给出 🔴FAIL，但修复方向与实际偏差 | 第 3 轮输出争议报告交给用户，浪费时间 | Detector 检测到同一任务 3 轮审核 FAIL → Diagnoser 检查各轮反馈是否实质性不同 → Healer.escalate 提前触发，附带恢复建议和根因分析 |
| FM-04 | **专家匹配错误 (Mis-Match)** | expert_matcher.py 选出领域不匹配的 Agent，导致输出质量持续低 | 无自动检测，只走用户反馈 Loop 2 | Detector.ScoreTrendWatch 检测该 Agent 在本次任务中专家评分骤降 → Diagnoser 对比匹配权重与当前任务需求 → Healer.switch 到候选 Agent #2 |
| FM-05 | **上下文污染 (Context Leak)** | 前一个 Agent 的输出污染后一个 Agent 的推理；表现为输出中包含无关来源引用 | 无检测 | Detector.OutputQualityWatch 中新增 source_trace: 检查输出中的所有引用是否都属于当前任务的 source_pool → Diagnoser 根据污染比例分配故障类型 → Healer.rollback 到无污染状态 + 重新隔离执行 |

### D2. 失效模式自愈路径汇总

```
失效模式         默认路径                     回退路径                    最终路径
─────────       ────────                    ────────                   ────────
FM-01 Infinite  中断 → switch Agent          switch 失败 → degrade       → escalate
Loop                                          任务复杂度降级
FM-02 False     降验证深度 → 标注             标注被驳回 → 全量验证       → escalate
Conflict
FM-03 Review    提前 escalate (第 2 轮)       主理人不可用 →              → 记录到
Looping                                        输出当前最佳+争议点         evolution-log
FM-04 Mis-Match switch Agent #2              #2 也失败 → degrade        → 触发 Loop 3
                                              到通用 Agent               更新匹配算法
FM-05 Context   rollback → 隔离执行           rollback 失败 →            → 标记任务
Leak                                           switch 到新 context       为高风险
```

### D3. 自愈效果度量指标

| 指标 | 计算方式 | 目标值 | 采集时间 |
|------|---------|-------|---------|
| **故障检测率 (FDR)** | 正确检测故障数 / 总故障数 | ≥ 95% | 每次检测 |
| **故障误报率 (FAR)** | 误报数 / 总报警数 | ≤ 5% | 每次检测 |
| **平均恢复时间 (MTTR)** | 从故障发生到恢复的总时间均值 | L1 < 30s, L2 < 2min | 每次恢复 |
| **恢复成功率 (RSR)** | 恢复成功数 / 总恢复次数 | ≥ 85% | 每次恢复 |
| **熔断准确率 (CBA)** | 正确熔断 / 总熔断次数 | ≥ 90% | 每次熔断 |
| **降级影响率 (DIR)** | 降级后产出标记数 / 总产出数 | ≤ 15% | 每次降级 |
| **自愈覆盖率 (SHC)** | 自动恢复故障 / 总故障数 | ≥ 80% | 每次任务完成 |

---

## E. 实现建议

### E1. 文件结构

```
self-healing/
├── __init__.py
├── self_heal.py              # v2.0.0 — 完全重写
│   ├── class Detector         # 故障检测
│   ├── class Diagnoser        # 故障诊断
│   ├── class Healer           # 故障恢复
│   ├── class Verifier         # 故障验证
│   ├── class CircuitBreaker   # 熔断器状态机
│   └── class SelfHealPipeline # 管道编排
├── strategies.py              # 恢复策略库
├── signals.py                 # 信号定义和归一化
├── integration.py             # health-monitor/evolution/orchestrator 集成
├── metrics.py                 # 自愈指标采集
└── repair_records.json        # 修复记录持久化
```

### E2. 管道编排伪码

```
class SelfHealPipeline:
    def run(self, task_ctx):
        loop:
            # 阶段 1: 聚合所有检测器信号
            signals = Detector.collect_all(task_ctx)

            if not signals:
                break  # 无故障

            # 阶段 2: 诊断
            diagnosis = Diagnoser.diagnose(signals, task_ctx.history)

            # 阶段 3: 恢复
            result = Healer.heal(diagnosis, task_ctx)

            # 阶段 4: 验证
            verification = Verifier.verify(result, task_ctx)

            if verification.verdict == "PASS":
                # 更新修复记录 + evolution
                TaskRecorder.record_success(diagnosis, result)
                EvolutionFeeder.feedback_success(diagnosis)
                break
            elif retries < max_retries:
                retries += 1
                continue
            else:
                # escalate
                VerdictRecorder.record_failure(diagnosis, result)
                escalate_to_user(diagnosis, result, verification)
                break
```

### E3. 升级路线

| 版本 | 新增内容 | 时间估计 |
|------|---------|---------|
| v2.0.0 | 完整 4 阶段管道 + 10 种故障分类 + 7 种恢复策略 | 基础实现 |
| v2.1.0 | 熔断器状态机 + 指数退避 + 修复记录集成 | 增量 1 |
| v2.2.0 | Evolution Loop 1/2/3 双向集成 + 自愈指标 | 增量 2 |
| v2.3.0 | 基于历史数据的恢复策略优化 (RL-based strategy selection) | 优化版本 |

---

## F. ASCII 状态图：一次完整自愈周期

```
Normal Execution
    │
    ├── HeartbeatWatch: last beat = 27s ago (> threshold=30s)
    │
    ▼
┌─────────────────────┐
│ Detector            │  输出: Signal(type=HEARTBEAT_MISS,
│  生成检测信号        │        agent_id="risk-manager", miss_count=4)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Diagnoser           │  输出: Diagnosis(
│  关联: 心跳缺失+最近  │        fault_type="AgentHang",
│  工具调用未返回       │        severity=L2,
│  → AgentHang         │        confidence=0.92,
│                      │        strategy="switch")
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Healer              │  输出: HealResult(
│  step 1: kill agent │        action="switch",
│  step 2: switch_to  │        target="risk-manager-备用",
│  "risk-manager-备用" │        elapsed_ms=4500)
│  step 3: 复制 context│
│  step 4: 重新调度     │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Verifier            │  输出: Verification(
│  检查 1: 新 Agent    │        verdict="PASS",
│   输出是否完整         │        checks=["functionality:OK",
│  检查 2: 是否引入     │                "side_effect:found_none",
│   新错误             │                "regression:OK"],
│  检查 3: 回归检查     │        confidence=0.95)
└─────────┬───────────┘
          │ PASS
          ▼
┌─────────────────────┐
│ Evolution Feeder    │  Loop 1: append to evolution-log
│  通知三环进化         │  Loop 2: update expert-scores (risk-manager)
│                      │  Loop 3: record switch pattern
└─────────────────────┘
          │
          ▼
    Resume Normal Execution
```

---

**修订历史**

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| v1.0 | 2026-07-09 | AI Architect | 初始完整设计 |
