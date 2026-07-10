# 任务依赖顺序控制方案 — v1.0

> 设计目标：解决互联网调研慢（30s~5min）vs 纯 LLM 任务快（2~10s）的节奏不匹配问题，
> 通过显式依赖声明 + 异步唤醒 + 增量更新，消除下游任务在缺失输入时"空跑"的浪费。

---

## 设计原则

1. **扩展现有字段，不重新造轮子** — 在 `subtask.dependency_ids` 基础上补充契约，不新增顶层结构
2. **最少侵入** — dependency_manager 作为 orchestrator 的中间件层，不改变现有 7 步流程骨架
3. **增量更新而非重做** — 调研结果到达后只修补已完成的 LLM 任务产出，不重新调度
4. **可观测** — 所有依赖状态变化写入 team-brain，health-monitor 可视

---

## A. 依赖声明机制

### A.1 扩展 Subtask Schema

在现有 `subtask.dependency_ids: string[]` 的基础上，新增 `dependency_contracts` 字段，
为每个依赖任务声明需要什么、怎么等：

```json
{
  "subtasks": [
    {
      "id": "ST-001",
      "name": "互联网调研行业数据",
      "type": "information_retrieval",
      "subtype": "async_research",
      "dependency_ids": [],
      "dependency_contracts": [],
      "output_contract": {
        "schema": {
          "type": "object",
          "required": ["market_size", "growth_rate", "competitors"],
          "properties": {
            "market_size": {"type": "number", "unit": "亿"},
            "growth_rate": {"type": "number", "unit": "%"},
            "competitors": {
              "type": "array",
              "items": {"type": "object", "properties": {
                "name": {"type": "string"},
                "market_share": {"type": "number"}
              }}
            }
          }
        },
        "required_fields": ["market_size", "growth_rate"],
        "optional_fields": ["competitors"],
        "fallback_value": {"market_size": "N/A", "growth_rate": "N/A"},
        "partial_delivery": true
      },
      "estimated_duration": "long"
    },
    {
      "id": "ST-002",
      "name": "架构设计",
      "type": "creation_generation",
      "dependency_ids": ["ST-001"],
      "dependency_contracts": [
        {
          "depends_on": "ST-001",
          "requires": {
            "mode": "specific_fields",
            "fields": ["market_size", "growth_rate"],
            "min_confidence": 0.7
          },
          "wait_strategy": "async_notify",
          "on_timeout": "proceed_with_fallback",
          "timeout_seconds": 180,
          "incremental_update": {
            "enabled": true,
            "update_scope": "section",
            "target_sections": ["market_analysis"],
            "update_mode": "patch"
          }
        }
      ]
    }
  ]
}
```

### A.2 新增字段定义

#### subtask[].subtype
在 `type` 枚举基础上，扩展 `subtype` 用于精细化区分：

| subtype | 含义 | 适用 type |
|---------|------|-----------|
| `async_research` | 异步调研 — 不阻塞 main flow | `information_retrieval` |
| `sync_query` | 同步查询 — 阻塞下游 | `information_retrieval` |
| `fast_llm` | 纯 LLM 快速任务 | `analysis_judgment`, `creation_generation` |
| `draft` | 草稿模式 — 先出 v0，等待补丁 | `creation_generation` |

#### subtask[].output_contract
输出契约，声明本任务承诺产出什么：

```
output_contract: {
  schema: { type, required[], properties{} },
  required_fields: string[],      // 下游强依赖的字段
  optional_fields: string[],      // 下游弱依赖的字段
  fallback_value: any,            // 该任务失败时提供的降级值
  partial_delivery: boolean,      // 是否支持分批交付（调研场景关键！）
  delivery_hooks: {               // 交付通知
    on_first_chunk: string[],     // 首批数据到达时通知哪些下游
    on_complete: string[],
    on_error: string[]
  }
}
```

#### subtask[].dependency_contracts[]
为每个依赖声明契约：

```
dependency_contract: {
  depends_on: string,             // 前置任务 ID

  requires: {
    mode: "all_completed"         // 等待全部完成
        | "specific_fields"       // 只等特定字段
        | "min_confidence"        // 等待置信度达标
        | "any_output"            // 只要有输出就行（信号级别）
        | "first_chunk"           // 首批数据到达即可
        | "status_only",          // 只等状态（完成/失败），不等数据
    fields?: string[],            // specific_fields 模式下指定字段
    min_confidence?: number,      // min_confidence 模式下指定阈值
  },

  wait_strategy: "block"          // 阻塞 — 前置不完我不启动
      | "async_notify"            // 异步通知 — 先启动草稿，完成后增量更新
      | "poll"                    // 轮询 — 周期性检查依赖状态
      | "skip_if_missing",        // 跳过 — 前置失败的跳过（不阻塞）

  timeout_seconds: number,        // 最大等待时间

  on_timeout: "fail"              // 超时→任务失败
      | "proceed_with_fallback"   // 超时→用 fallback 值继续
      | "proceed_draft"           // 超时→接受已有草稿
      | "skip",                   // 超时→跳过本任务

  incremental_update?: {          // async_notify 模式下启用
    enabled: boolean,
    update_scope: "full"          // 重做整个产出
        | "section"               // 只更新特定章节/部分
        | "field",                // 只更新特定字段
    target_sections?: string[],   // section 模式下指定目标
    update_mode: "patch"          // 补丁（推荐—最小变更）
        | "replace",              // 直接替换指定 section
    max_patch_rounds: number,     // 最大增量更新轮次
  }
}
```

### A.3 依赖边类型增强

现有 `dependency_graph.edges[].type ∈ {blocking, conditional, feedback}` 补充运行时语义：

| 边类型 | 含义 | wait_strategy 默认值 | 异步兼容 |
|--------|------|---------------------|---------|
| `blocking` | 必须等前置完成 | `block` | ❌ |
| `conditional` | 前置输出决定是否执行 | `block` | ❌（需要完整输出做决策） |
| `feedback` | 后序可触发前置修正 | `block` | ❌ |
| ⭐ **NEW** `async_blocking` | 先启动草稿，前置完成后增量更新 | `async_notify` | ✅ |
| ⭐ **NEW** `signal` | 只需前置完成信号，不需数据 | `skip_if_missing` | ✅ |
| ⭐ **NEW** `dataflow` | 只需特定字段到达 | `async_notify` + `specific_fields` | ✅ |

---

## B. 阻断与唤醒机制

### B.1 DependencyManager — 依赖管理器

新增 `scripts/dependency_manager.py`，作为 orchestrator 中间件：

```python
class DependencyManager:
    """
    依赖管理器 — 维护所有子任务的依赖状态机.
    
    职责:
    1. 管理 subtask → state 映射
    2. 阻断依赖未满足的任务
    3. 监听任务完成事件 → 唤醒被阻断任务
    4. 处理超时和依赖失败
    """

    # 任务状态
    STATE_PENDING   = "pending"    # 已注册，未就绪
    STATE_READY     = "ready"      # 所有依赖满足，可调度
    STATE_BLOCKED   = "blocked"    # 有依赖未满足，被阻断
    STATE_RUNNING   = "running"    # 正在执行
    STATE_COMPLETED = "completed"  # 正常完成
    STATE_SKIPPED   = "skipped"    # 被跳过
    STATE_FAILED    = "failed"     # 执行失败
    STATE_DRAFT     = "draft"      # async_notify 模式的草稿状态
    STATE_PATCHED   = "patched"    # 已完成并接收了增量更新

    def __init__(self, subtasks, dependency_graph):
        self.subtasks = {s["id"]: s for s in subtasks}
        self.edges = dependency_graph.get("edges", [])
        self.states = {}           # subtask_id → state
        self.results = {}          # subtask_id → {full_result, chunks[]}
        self.blocked_queue = []    # 被阻断任务的优先级队列
        self.timers = {}           # subtask_id → timeout_info
        self.first_chunk_flags = {}  # subtask_id → first_chunk_delivered
        
        # 初始化状态
        for s in subtasks:
            deps = s.get("dependency_ids", [])
            contracts = {c["depends_on"]: c for c in s.get("dependency_contracts", [])}
            if not deps:
                self.states[s["id"]] = self.STATE_READY
            else:
                # 检查是否所有依赖都已满足
                all_met = all(self._is_dep_met(dep_id, contracts.get(dep_id, {}))
                            for dep_id in deps)
                self.states[s["id"]] = self.STATE_READY if all_met else self.STATE_BLOCKED
    
    def check_blocked(self) -> list[dict]:
        """返回当前可以被唤醒的任务列表"""
        ready = []
        for sid, state in self.states.items():
            if state != self.STATE_BLOCKED:
                continue
            if self._all_deps_met(sid):
                self.states[sid] = self.STATE_READY
                ready.append(self.subtasks[sid])
        return ready
    
    def on_task_completed(self, subtask_id: str, result: dict):
        """任务完成回调 — 核心唤醒入口"""
        self.states[subtask_id] = self.STATE_COMPLETED
        self.results[subtask_id] = {"full_result": result, "chunks": [result]}
        
        # 遍历查找依赖该任务的 blocked 任务
        awakened = []
        for sid, state in self.states.items():
            if state != self.STATE_BLOCKED:
                continue
            deps = self.subtasks[sid].get("dependency_ids", [])
            if subtask_id in deps and self._all_deps_met(sid):
                self.states[sid] = self.STATE_READY
                awakened.append(sid)
        return awakened
    
    def on_first_chunk(self, subtask_id: str, chunk: dict):
        """首批数据到达 — 支持 partial_delivery"""
        if subtask_id not in self.first_chunk_flags:
            self.first_chunk_flags[subtask_id] = True
            if subtask_id not in self.results:
                self.results[subtask_id] = {"full_result": None, "chunks": []}
            self.results[subtask_id]["chunks"].append(chunk)
            
            # 检查所有依赖本任务的 async_notify 下游
            awakened = []
            for sid, state in self.states.items():
                if state != self.STATE_BLOCKED:
                    continue
                contracts = {c["depends_on"]: c for c in 
                           self.subtasks[sid].get("dependency_contracts", [])}
                contract = contracts.get(subtask_id, {})
                if contract.get("requires", {}).get("mode") == "first_chunk":
                    self.states[sid] = self.STATE_READY
                    awakened.append(sid)
            return awakened
        return []
    
    def _all_deps_met(self, subtask_id: str) -> bool:
        """检查一个任务的所有依赖是否满足"""
        deps = self.subtasks[subtask_id].get("dependency_ids", [])
        contracts = {c["depends_on"]: c for c in 
                    self.subtasks[subtask_id].get("dependency_contracts", [])}
        return all(self._is_dep_met(dep_id, contracts.get(dep_id, {})) 
                  for dep_id in deps)
    
    def _is_dep_met(self, dep_id: str, contract: dict) -> bool:
        """检查单个依赖是否满足"""
        dep_state = self.states.get(dep_id)
        # COMPLETED / PATCHED 都算完成（patch 是后补的完成）
        if dep_state in (self.STATE_COMPLETED, self.STATE_PATCHED):
            return True
        if dep_state == self.STATE_FAILED:
            # 看 wait_strategy
            ws = contract.get("wait_strategy", "block")
            if ws in ("skip_if_missing", "async_notify"):
                return True  # 跳过或异步通知模式允许继续
            return False
        if dep_state is None:
            return False
        
        return False
```

### B.2 阻断与唤醒流程（状态图）

```
┌──────────┐    所有依赖满足    ┌──────────┐    调度器 pick    ┌───────────┐
│ BLOCKED  │ ────────────────▶ │  READY   │ ────────────────▶ │  RUNNING  │
│          │                   │          │                   │           │
│ 被阻断   │   on_task_        │ 就绪     │   开始执行        │ 运行中    │
│          │   completed()     │          │                   │           │
└──────────┘                   └──────────┘                   └─────┬─────┘
      ▲                                                             │
      │                                                     ┌───────┴────────┐
      │                                              ┌──────┤                ├──────┐
      │                                              │      ▼                ▼      │
      │                                         ┌─────────┐           ┌──────────┐  │
      │                                         │COMPLETED│           │  FAILED   │  │
      │                                         │         │           │          │  │
      │   on_timeout = proceed                   └────┬────┘           └──────────┘  │
      │   & 有增量更新 pendng                        │                              │
      │                                              ▼                              │
      │                                         ┌──────────┐                       │
      │                                         │ PATCHED  │                       │
      │      ┌──────────────────────────────────│          │                       │
      │      │   接收到增量更新                  └──────────┘                       │
      │      │                                                                     │
      └──────┴─────────────────────────────────────────────────────────────────────┘
        on_dep_completed() 发现所有依赖满足 → 唤醒
```

### B.3 超时处理

```python
class TimeoutHandler:
    """
    超时处理 — 在 orchestrator 主循环中定期检查
    """
    
    def check_timeouts(self, manager: DependencyManager) -> list[dict]:
        """检查所有 blocked 任务是否超时，返回需要处理的任务"""
        now = time.time()
        expired = []
        for sid, state in manager.states.items():
            if state != DependencyManager.STATE_BLOCKED:
                continue
            subtask = manager.subtasks[sid]
            for contract in subtask.get("dependency_contracts", []):
                timeout = contract.get("timeout_seconds", 0)
                if timeout <= 0:
                    continue
                dep_id = contract["depends_on"]
                dep_state = manager.states.get(dep_id)
                # 如果依赖还是 blocked/running 且超时
                if dep_state in (DependencyManager.STATE_BLOCKED, 
                                 DependencyManager.STATE_RUNNING,
                                 DependencyManager.STATE_PENDING):
                    # 检查启动时间
                    start_time = manager.start_times.get(sid, time.time())
                    elapsed = now - start_time
                    if elapsed > timeout:
                        expired.append((sid, contract))
        return expired
    
    def resolve_timeout(self, sid: str, contract: dict, 
                        manager: DependencyManager) -> str:
        """执行超时策略"""
        action = contract.get("on_timeout", "fail")
        
        if action == "proceed_with_fallback":
            dep_id = contract["depends_on"]
            fallback = manager.subtasks.get(dep_id, {}).get("output_contract", {}).get("fallback_value", {})
            manager.results[dep_id] = {"full_result": fallback, "is_fallback": True}
            manager.states[dep_id] = manager.STATE_COMPLETED  # 伪完成
            manager.states[sid] = manager.STATE_READY
            return "proceed_with_fallback"
        
        elif action == "proceed_draft":
            # 接受草稿状态，标记增量更新待进行
            manager.states[sid] = manager.STATE_READY
            manager.draft_mode[sid] = True
            return "proceed_draft"
        
        elif action == "skip":
            manager.states[sid] = manager.STATE_SKIPPED
            return "skip"
        
        else:  # fail
            manager.states[sid] = manager.STATE_FAILED
            return "fail"
```

### B.4 依赖失败传播矩阵

前置任务状态 | `block` | `async_notify` | `poll` | `skip_if_missing`
---|---|---|---|---
**completed** | ✅ 唤醒 | ✅ 唤醒 + 增量更新待进行 | ✅ 唤醒 | ✅ 唤醒
**failed** | ❌ 永久阻断 → escalate | ⚠️ 用 fallback 值继续 | ❌ 永久阻断 → escalate | ✅ 跳过
**skipped** | ❌ 永久阻断 | ✅ 用 fallback 值 | ❌ 永久阻断 | ✅ 跳过
**超时** | 按 `on_timeout` 策略 | 按 `on_timeout` 策略 | 按 `on_timeout` 策略 | N/A

---

## C. 异步调研模式（Async Research）

### C.1 核心流程

```
时间线:
┌──────────────────────────────────────────────────────┐
│                                                       │
│  ST-001: 互联网调研 (async_research)                   │
│  ├── 启动调研 Agent (非阻塞)                            │
│  └── 预计耗时 30s~5min ...                              │
│                                                       │
│  ST-002: 架构设计  ←── async_notify 依赖 ST-001        │
│  ├── [t=0s] 启动 → 产出 v0 草稿（含 TBD 标记）          │
│  │            → 状态: DRAFT                            │
│  ├── [t=45s] ST-001 首批数据到达                         │
│  │            → 增量更新 ST-002 的 market_analysis 章节  │
│  │            → 状态: PATCHED                           │
│  ├── [t=120s] ST-001 完整报告到达                       │
│  │            → 全量增量更新 ST-002                      │
│  │            → 状态: COMPLETED                         │
│  └── 交付                                               │
│                                                       │
│  ST-003: 风险分析                                      │
│  ├── [t=0s] 等待 ST-001 + ST-002 都完成                │
│  │   wait_strategy = block                              │
│  └── [t=125s] 两者都完成 → 启动                          │
└──────────────────────────────────────────────────────┘
```

### C.2 增量更新机制

```python
class IncrementalUpdater:
    """
    增量更新器 — 在调研结果到达后，修改已完成的 LLM 任务产出。
    核心原则：patch 而非 replace，最小变更。
    """
    
    def patch_output(self, 
                     original_output: dict | str,
                     new_data: dict,
                     contract: dict) -> dict | str:
        """根据 contract 执行增量更新"""
        scope = contract.get("incremental_update", {}).get("update_scope", "section")
        mode = contract.get("incremental_update", {}).get("update_mode", "patch")
        
        # 结构化输出（dict）
        if isinstance(original_output, dict):
            if scope == "field":
                return self._patch_fields(original_output, new_data, mode)
            elif scope == "section":
                return self._patch_section(original_output, new_data, mode)
            else:  # full
                return self._replace_full(original_output, new_data, mode)
        
        # 文本输出（markdown 报告）
        elif isinstance(original_output, str):
            if scope == "section":
                return self._patch_markdown_section(original_output, new_data)
            else:
                return original_output + "\n\n## 增量更新\n" + str(new_data)
        
        return original_output
    
    def _patch_fields(self, original: dict, new_data: dict, mode: str) -> dict:
        """字段级别补丁 — 只更新 TBD 或标记为待补充的字段"""
        result = dict(original)
        for key, value in new_data.items():
            if mode == "patch":
                # 只更新值为 TBD/None/占位符 的字段
                if original.get(key) in ("TBD", "N/A", None, "待补充", "待调研"):
                    result[key] = value
            elif mode == "replace":
                result[key] = value
        return result
    
    def _patch_section(self, original: dict, new_data: dict, mode: str) -> dict:
        """章节级别补丁 — 更新特定子结构"""
        result = dict(original)
        target_sections = new_data.get("_target_sections", [])
        for section in target_sections:
            if section in new_data:
                value = new_data[section]
                if mode == "patch" and isinstance(value, dict) and isinstance(result.get(section), dict):
                    result[section].update(value)
                else:
                    result[section] = value
        return result
    
    def _patch_markdown_section(self, original: str, new_data: dict) -> str:
        """Markdown 章节补丁 — 查找 ## 标题定位替换"""
        import re
        result = original
        for section_title, new_content in new_data.items():
            # 找到对应章节并替换
            pattern = rf"(## {section_title}.*?\n)(.*?)(?=\n## |\Z)"
            replacement = rf"\1{new_content}\n"
            if re.search(pattern, result, re.DOTALL):
                result = re.sub(pattern, replacement, result, flags=re.DOTALL)
            else:
                # 章节不存在，追加
                result += f"\n## {section_title}\n{new_content}\n"
        return result
```

### C.3 DRAFT 状态的草稿标记

当 LLM 任务以 `async_notify` 模式启动时，需要在 prompt 中注入草稿标记：

```
🎯 对齐锚点 (草稿模式)
全局目标: {global_objective}
本任务: {description}

⚠️ 本任务的依赖数据正在收集中，请按以下约束执行：
1. 需要依赖数据的部分先用「TBD: 待 {依赖任务名} 完成后补充」标记
2. 基于已有的经验和常识先出草稿骨架
3. 在输出末尾附加: [DRAFT_SECTIONS]
   需要增量更新的章节列表:
   - section_1: 市场分析
   - section_2: 竞争格局
   [/DRAFT_SECTIONS]
4. 无需依赖数据部分正常完成
```

草稿产出示例：
```json
{
  "architecture": "采用微服务架构，分为 API 网关、业务服务层、数据层",
  "market_analysis": "TBD: 待 ST-001 互联网调研完成后补充市场数据",
  "tech_stack": "Python FastAPI + PostgreSQL + Redis",
  "_draft_sections": ["market_analysis"],
  "_requires_patch": true,
  "_patch_contract": {
    "target": "market_analysis",
    "new_data_source": "ST-001"
  }
}
```

---

## D. 与现有系统集成

### D.1 与 orchestrator.py 集成

修改 `_step4_6_execute()` 方法，引入 DependencyManager 中间件：

```python
# orchestrator.py — 新增方法

from scripts.dependency_manager import DependencyManager, IncrementalUpdater, TimeoutHandler

class NexusOrchestrator:
    def __init__(self):
        # ... 原有初始化 ...
        self.dep_manager = None
        self.incremental_updater = IncrementalUpdater()
        self.timeout_handler = TimeoutHandler()
    
    def run(self, task: str) -> dict:
        intent = self._step0_intent(task)
        
        # ... 原有 trivial/ambiguous 处理 ...
        
        decomposition = self._step1_decompose(task)
        
        # ★ NEW: 初始化依赖管理器
        self.dep_manager = DependencyManager(
            decomposition.get("subtasks", []),
            decomposition.get("dependency_graph", {"edges": []})
        )
        
        matches = self._step2_match(decomposition)
        path = self._step3_select(matches, decomposition)
        return self._step4_6_execute(path, decomposition)
    
    def _step4_6_execute(self, path: dict, decomposition: dict) -> dict:
        agent_type = path.get("agent_type", "researcher-ds")
        # ... 原有 acquire_batch ...
        
        try:
            return self._dependency_aware_dispatch(decomposition)
        finally:
            # ... 原有 release ...
    
    def _dependency_aware_dispatch(self, decomposition: dict) -> dict:
        """
        依赖感知的调度 — 替换原有的串行 _dispatch_all。
        
        主循环:
        1. 从 dep_manager 获取 READY 任务
        2. 并行派发 READY 任务
        3. 监听完成事件 → 更新 dep_manager → 唤醒新的 READY 任务
        4. 处理超时
        5. 处理增量更新
        """
        dm = self.dep_manager
        results = {}
        all_subtasks = set(dm.subtasks.keys())
        completed = set()
        pending_incremental = []  # [(task_id, dep_id), ...]
        
        # 主调度循环
        while len(completed) < len(all_subtasks):
            # 1. 超时检查
            expired = self.timeout_handler.check_timeouts(dm)
            for sid, contract in expired:
                action = self.timeout_handler.resolve_timeout(sid, contract, dm)
                self._log_timeout(sid, action)
            
            # 2. 获取可执行任务
            ready_tasks = dm.check_blocked()
            
            # 3. 并行派发
            for task_spec in ready_tasks:
                # 检查是否是 async_notify → 草稿模式
                sid = task_spec["id"]
                has_async = any(c.get("wait_strategy") == "async_notify" 
                              for c in task_spec.get("dependency_contracts", []))
                
                if has_async and not self._all_blocking_deps_done(sid, dm):
                    # 草稿模式
                    prompt = self._build_draft_prompt(task_spec, dm)
                    output_text = self._execute_agent(prompt)
                    dm.states[sid] = dm.STATE_DRAFT
                    dm.results[sid] = {"full_result": output_text, "is_draft": True}
                    
                    # 记录需要增量更新的依赖
                    for c in task_spec.get("dependency_contracts", []):
                        if c.get("wait_strategy") == "async_notify":
                            pending_incremental.append((sid, c["depends_on"], c))
                else:
                    # 正常执行
                    prompt = self._build_aligned_prompt(task_spec)
                    output_text = self._execute_agent(prompt)
                    result = self._verify(output_text, task_spec)
                    dm.on_task_completed(sid, result)
                    results[sid] = result
                    completed.add(sid)
            
            # 4. 处理增量更新（调研完成触发的）
            new_patches = self._process_pending_incremental(dm, pending_incremental, results)
            for sid in new_patches:
                completed.add(sid)
            
            # 5. 检查是否所有任务都完成/失败/跳过
            done_states = {dm.STATE_COMPLETED, dm.STATE_FAILED, dm.STATE_SKIPPED, dm.STATE_PATCHED}
            if all(dm.states[s] in done_states for s in all_subtasks):
                break
            
            # 6. 无可执行任务 && 无进展 → 等待（短 sleep）
            if not ready_tasks and not pending_incremental:
                time.sleep(0.5)
        
        return self._collect_results(results, dm)
    
    # ── 数据手递手的核心方法 ──────────────────────────────────────────────
    # ⚠️ 关键设计约束：
    # 下游任务的 prompt 必须包含上游调研产出的结构化数据（不仅是一条"已完成"信号）
    # 否则调研做了但下游用不上，等于白做。
    
    def _build_aligned_prompt(self, task_spec: dict, dm: DependencyManager) -> str:
        """
        构建下游任务的完整执行 prompt。
        
        核心职责：将上游依赖的产出注入到下游的上下文中，
        确保「调研结果 → 内部研讨」的数据链路闭环。
        """
        prompt_parts = [
            f"## 任务: {task_spec.get('description', '')}",
            f"**任务 ID:** {task_spec['id']}",
        ]
        
        # ★ 关键：注入上游依赖的产出
        deps = task_spec.get("dependency_ids", [])
        contracts = {c["depends_on"]: c for c in task_spec.get("dependency_contracts", [])}
        
        if deps:
            prompt_parts.append("\n## 上游调研数据（依赖任务产出）\n")
            for dep_id in deps:
                dep_result = dm.results.get(dep_id, {})
                full = dep_result.get("full_result", {})
                chunks = dep_result.get("chunks", [])
                is_fallback = dep_result.get("is_fallback", False)
                
                if is_fallback:
                    prompt_parts.append(f"> ⚠️ 依赖任务 `{dep_id}` 超时，使用 fallback 数据\n")
                
                contract = contracts.get(dep_id, {})
                mode = contract.get("requires", {}).get("mode", "all_completed")
                
                if mode == "specific_fields":
                    fields = contract.get("requires", {}).get("fields", [])
                    if isinstance(full, dict):
                        excerpt = {k: full.get(k, "N/A") for k in fields}
                        prompt_parts.append(f"**来自 `{dep_id}`（指定字段）:**\n```json\n{json.dumps(excerpt, ensure_ascii=False, indent=2)}\n```\n")
                    else:
                        prompt_parts.append(f"**来自 `{dep_id}`:**\n{full}\n")
                elif mode == "first_chunk":
                    first = chunks[0] if chunks else full
                    prompt_parts.append(f"**来自 `{dep_id}`（首批数据）:**\n{first}\n")
                else:
                    prompt_parts.append(f"**来自 `{dep_id}`（完整产出）:**\n{full}\n")
        
        # ★ 注入任务自身的 meta 信息
        prompt_parts.append(f"""
## 执行约束
- 验收标准: {task_spec.get('acceptance_criteria', 'N/A')}
- 输出格式: {task_spec.get('output_format', '标准报告')}
- 上游数据已由 DependencyManager 注入上方，有 TBD 标记的字段需在增量更新中补充
""")
        
        return "\n".join(prompt_parts)
    
    def _build_draft_prompt(self, task_spec: dict, dm: DependencyManager) -> str:
        """
        构建草稿模式的执行 prompt。
        
        与 _build_aligned_prompt 的差异：
        1. 已有的上游数据正常注入
        2. 尚未到达的数据用 TBD 标记
        3. 在输出末标注需要增量更新的章节
        """
        base = self._build_aligned_prompt(task_spec, dm)
        
        # 识别哪些依赖尚未完成
        draft_notice = "\n## ⚠️ 草稿模式 — 部分数据尚未到达\n"
        for contract in task_spec.get("dependency_contracts", []):
            dep_id = contract["depends_on"]
            dep_state = dm.states.get(dep_id)
            if dep_state != dm.STATE_COMPLETED and dep_state != dm.STATE_PATCHED:
                draft_notice += f"- `{dep_id}`: 正在收集中（预计 {contract.get('timeout_seconds', 120)}s）\n"
        
        draft_notice += """
执行约束（草稿规则）：
1. 已有数据 → 正常使用（见上方「上游调研数据」）
2. 缺失数据 → 用「TBD: 待 {依赖任务} 完成后补充」标记
3. 在输出末尾附加 \[DRAFT_SECTIONS\] 列出需要增量更新的章节
4. 填充 TBD 以外部分正常完成
"""
        return base + draft_notice
    
    def _collect_results(self, results: dict, dm: DependencyManager) -> dict:
        """
        收集所有子任务的最终产出，合并为完整输出。
        
        确保调研产出通过 structured_context 透传给下游，
        最终用户看到的完整报告中包含调研数据。
        """
        # 构建结构化上下文：每个子任务的产出按 dependency 顺序组织
        ordered = []
        visited = set()
        
        def visit(sid):
            if sid in visited:
                return
            visited.add(sid)
            for dep_id in dm.subtasks.get(sid, {}).get("dependency_ids", []):
                visit(dep_id)
            result = results.get(sid) or dm.results.get(sid, {}).get("full_result", {})
            ordered.append({"task_id": sid, "output": result})
        
        for sid in dm.subtasks:
            visit(sid)
        
        return {
            "status": "completed",
            "outputs": ordered,
            "structured_context": {sid: dm.results.get(sid, {}).get("full_result", {})
                                  for sid in dm.subtasks},
            "patch_history": self._collect_patch_history(dm),
        }
    
    def _collect_patch_history(self, dm: DependencyManager) -> list:
        """收集所有增量更新的历史"""
        history = []
        for sid, data in dm.results.items():
            if data.get("was_patched"):
                history.append({
                    "task_id": sid,
                    "patched_at": data.get("patched_at", "unknown"),
                    "patch_source": "incremental_update",
                })
        return history
    
    def _process_pending_incremental(self, dm, pending, results) -> list[str]:
        """处理待进行的增量更新"""
        patched = []
        still_pending = []
        for sid, dep_id, contract in pending:
            dep_state = dm.states.get(dep_id)
            if dep_state == dm.STATE_COMPLETED:
                # 依赖完成 → 执行增量更新
                dep_result = dm.results.get(dep_id, {}).get("full_result", {})
                draft_output = dm.results.get(sid, {}).get("full_result", "")
                
                updated = self.incremental_updater.patch_output(
                    draft_output, dep_result, contract
                )
                
                dm.results[sid] = {"full_result": updated, "is_draft": False, "was_patched": True}
                dm.states[sid] = dm.STATE_PATCHED
                results[sid] = {"status": "PATCHED", "output": updated}
                patched.append(sid)
            elif dep_state in (dm.STATE_FAILED, dm.STATE_SKIPPED):
                # 依赖失败 → 跳过增量更新，接受草稿
                draft = dm.results.get(sid, {}).get("full_result", "")
                dm.states[sid] = dm.STATE_COMPLETED
                results[sid] = {"status": "PASS_DRAFT", "output": draft}
                patched.append(sid)
            else:
                still_pending.append((sid, dep_id, contract))
        
        pending[:] = still_pending
        return patched
```

### D.2 与 self_heal.py 集成

新增故障类型 FT-11（DependencyTimeout）并扩展 FT-05（DependencyFail）：

```python
# self_heal.py — 新增

FAULT_TYPES = {
    # ... 原有 FT-01~FT-10 ...
    
    "FT-11": {
        "name": "DependencyTimeout",
        "severity": 2,
        "recoverable": True,
        "desc": "依赖任务超时 — 依赖管理器报告某个前置任务超时"
    },
    "FT-12": {
        "name": "IncrementalPatchFailure",
        "severity": 2,
        "recoverable": True,
        "desc": "增量更新失败 — patch 应用到草稿时发生冲突或格式不匹配"
    },
}

# ⭐ NEW: 扩展 FT-05 DependencyFail 的恢复策略
# 当诊断出 FT-05 时，新增逻辑：
def _dependency_fail_heal(self, diagnosis, dm):
    """
    DependencyFail 增强恢复逻辑
    
    决策树:
    1. 能否降级? → dep.output_contract.fallback_value 有值? → 用 fallback
    2. 是否可以 skip? → wait_strategy == skip_if_missing? → 跳过
    3. 是否在草稿模式? → 接受草稿 (accept_draft)
    4. 都不可行 → escalate
    """
    agent_id = diagnosis.agent_id  # 这里实际上是 subtask_id
    subtask = dm.subtasks.get(agent_id, {})
    
    for contract in subtask.get("dependency_contracts", []):
        dep_id = contract["depends_on"]
        ws = contract.get("wait_strategy", "block")
        
        if ws == "skip_if_missing":
            return HealResult(action="skip", target=agent_id, ...)
        
        if contract.get("on_timeout") == "proceed_with_fallback":
            return HealResult(action="degrade", target=agent_id,
                details={"mode": "use_fallback", "fallback_source": dep_id}, ...)
        
        # 有 incrememental_update → 接受已有草稿
        if contract.get("incremental_update", {}).get("enabled"):
            return HealResult(action="degrade", target=agent_id,
                details={"mode": "accept_draft", "note": "依赖失败，接受草稿"}, ...)
    
    # 都不满足 → escalate
    return HealResult(action="escalate", target="human", ...)
```

**熔断器联动**：如果某个调研 Agent 连续 3 次超时，熔断器 OPEN，不再调度该 Agent 做调研，
而是直接使用 fallback 值。调研 Agent 的熔断独立于其他 Agent。

### D.3 与 task-decomposition-v2.3.md 的 DAG 集成

在拆解阶段（步骤 6-7）生成 v2.3 schema 时，增加依赖契约的自动推断规则：

| 子任务对 | 自动推断的依赖契约 |
|---------|------------------|
| (调研, 分析) | `wait_strategy: async_notify`, `requires.mode: first_chunk` |
| (分析, 生成) | `wait_strategy: block`, `requires.mode: all_completed` |
| (调研, 架构) | `wait_strategy: async_notify`, `requires.mode: specific_fields` |
| (验证, 任意) | `wait_strategy: block`, `requires.mode: all_completed` |
| (协调, 任意) | `wait_strategy: skip_if_missing` |

在 task_decomposer.py 中新增规则：

```python
# task_decomposer.py — 新增依赖契约推断

def infer_dependency_contracts(subtasks, edges):
    """根据子任务类型和边类型自动推断依赖契约"""
    for edge in edges:
        from_sub = next(s for s in subtasks if s["id"] == edge["from"])
        to_sub = next(s for s in subtasks if s["id"] == edge["to"])
        
        # 找到对应的 contract 或创建一个
        contracts = to_sub.setdefault("dependency_contracts", [])
        existing = next((c for c in contracts if c["depends_on"] == edge["from"]), None)
        if existing:
            continue
        
        contract = {"depends_on": edge["from"]}
        
        # 推断 requires
        from_type = from_sub.get("subtype", from_sub.get("type", ""))
        to_type = to_sub.get("subtype", to_sub.get("type", ""))
        
        if from_type in ("async_research",) and to_type in ("creation_generation", "analysis_judgment"):
            contract["requires"] = {"mode": "first_chunk"}
            contract["wait_strategy"] = "async_notify"
            # 推断需要哪些字段
            needed_fields = _intersect_fields(from_sub, to_sub)
            if needed_fields:
                contract["requires"] = {"mode": "specific_fields", "fields": needed_fields}
            contract["incremental_update"] = {
                "enabled": True,
                "update_scope": "section",
                "update_mode": "patch"
            }
        elif edge.get("type") == "blocking":
            contract["requires"] = {"mode": "all_completed"}
            contract["wait_strategy"] = "block"
        elif edge.get("type") == "conditional":
            contract["requires"] = {"mode": "all_completed"}
            contract["wait_strategy"] = "block"
        else:
            contract["requires"] = {"mode": "all_completed"}
            contract["wait_strategy"] = "block"
        
        # 设置超时（来自 effort_estimate）
        from_effort = from_sub.get("effort_estimate", {})
        if from_effort.get("level") in ("XL", "L"):
            contract["timeout_seconds"] = 300  # 5min
        elif from_effort.get("level") == "M":
            contract["timeout_seconds"] = 120  # 2min
        else:
            contract["timeout_seconds"] = 60   # 1min
        
        contract["on_timeout"] = "proceed_draft" if "async_notify" in contract.get("wait_strategy", "") else "fail"
        
        contracts.append(contract)
```

### D.3.5 增量更新完的最终合并

增量更新完成后，`_process_pending_incremental` 还要通知**依赖该任务的后续下游**：

```python
def _process_pending_incremental(self, dm, pending, results) -> list[str]:
    """处理待进行的增量更新"""
    patched = []
    still_pending = []
    for sid, dep_id, contract in pending:
        dep_state = dm.states.get(dep_id)
        if dep_state == dm.STATE_COMPLETED:
            dep_result = dm.results.get(dep_id, {}).get("full_result", {})
            draft_output = dm.results.get(sid, {}).get("full_result", "")
            
            updated = self.incremental_updater.patch_output(
                draft_output, dep_result, contract
            )
            
            dm.results[sid] = {"full_result": updated, "is_draft": False, "was_patched": True}
            dm.states[sid] = dm.STATE_PATCHED
            results[sid] = {"status": "PATCHED", "output": updated}
            patched.append(sid)
            
            # ★ 补丁完成 → 通知依赖本任务的下游（而非 dep_id 的下游）
            awakened = dm.on_task_completed(dep_id, updated)  # dep_id 的研究任务已完成
            # sid（被 patch 的任务）也标记完成，唤醒依赖它的下游
            awakened += dm.on_task_completed(sid, updated)
```

### D.4 健康监控集成

在 `health-monitor.py` 中新增依赖状态检查：

```python
# health-monitor.py — 新增

def check_dependency_health(team_id: str) -> dict:
    """
    检查团队的依赖健康状态
    
    输出:
    - blocked_count: 被阻断的任务数
    - avg_block_time: 平均阻断时间
    - longest_chain: 最长依赖链长度
    - deadlock_detected: 是否检测到循环依赖
    - stalled_deps: 长时间未推进的依赖
    """
    team_status = load_team_status(team_id)
    if not team_status:
        return {"error": "team_not_found"}
    
    dep_state = team_status.get("dependency_state", {})
    subtasks = dep_state.get("subtasks", [])
    states = dep_state.get("states", {})
    start_times = dep_state.get("start_times", {})
    
    now = datetime.now(timezone.utc)
    blocked = [s for s in subtasks if states.get(s) == "blocked"]
    
    return {
        "team_id": team_id,
        "total": len(subtasks),
        "blocked": blocked,
        "blocked_count": len(blocked),
        "stalled": [
            {"subtask": s, "blocked_seconds": (now - start_times.get(s, now)).total_seconds()}
            for s in blocked
            if (now - start_times.get(s, now)).total_seconds() > 120
        ],
    }
```

---

## E. 文件变更清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `scripts/dependency_manager.py` | **新增** | 依赖管理器 — DependencyManager, IncrementalUpdater, TimeoutHandler |
| `scripts/orchestrator.py` | **修改** | _dependency_aware_dispatch 替换 _dispatch_all；集成 DependencyManager |
| `scripts/self_heal.py` | **修改** | 新增 FT-11, FT-12；扩展 FT-05 恢复逻辑 |
| `scripts/health-monitor.py` | **修改** | 新增 check_dependency_health() |
| `scripts/task_decomposer.py` | **修改** | 新增 infer_dependency_contracts() |
| `references/task-decomposition-v2.3.md` | **修改** | subtask schema 增加 subtype/dependency_contracts/output_contract |
| `references/self-healing-architecture.md` | **修改** | 新增 FT-11, FT-12 到故障分类表 |

---

## F. 边界情况与防护

### F.1 循环依赖检测

在初始化 DependencyManager 时做拓扑排序检查：

```python
def detect_cycles(subtasks, edges):
    """检测依赖图中是否有环"""
    graph = {s["id"]: [] for s in subtasks}
    for e in edges:
        graph.setdefault(e["from"], []).append(e["to"])
    
    # DFS 检测环
    visited = set()
    rec_stack = set()
    
    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            if dfs(node):
                return True, node
    return False, None
```

### F.2 增量更新冲突

如果原任务已经被下游消费（如交付给用户），再打补丁需要标记版本：

```python
class VersionedOutput:
    """支持版本追踪的产出包装器"""
    def __init__(self, output, version=1):
        self.output = output
        self.version = version
        self.patch_history = []
        self.consumed_by = set()  # 哪些下游已消费
    
    def apply_patch(self, patch, new_data):
        self.patch_history.append({
            "version": self.version,
            "patch": patch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_snapshot": copy.deepcopy(new_data)
        })
        self.version += 1
```

### F.3 调研任务连续失败 → 最终降级

当调研 Agent 连续 3 次超时或失败时，熔断器 OPEN，后续任务自动使用 fallback 值。
同时记录到 `evolution-log`，触发 Loop 3 的元学习。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| v1.0 | 2026-07-09 | AI Architect | 初始完整设计 |
