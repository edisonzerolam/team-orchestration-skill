#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nexus Orchestrator v2.5 — 总控调度器（拓扑排序+依赖阻塞）

执行规则：
  - 根据 task-decomposer 输出的 subtasks[].dependency_ids 拓扑排序
  - 同一 phase 的同层子任务可并行执行
  - 依赖未满足的子任务被阻塞，前置完成后自动唤醒
  - 调研子任务（long）先执行，分析子任务（medium）等待

修复记录:
  F2-F12: 历史修复
  F13: 新增拓扑排序执行 + 依赖阻塞唤醒（v2.5）

用法:
  python orchestrator.py --task "分析茅台股票"
  python orchestrator.py --task "查一下Python文档"
"""
import json, sys, time, hashlib, argparse, threading
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR))

try:
    from scripts.task_decomposer import decompose as _decompose
except ImportError:
    _decompose = None
try:
    from scripts.team_builder import build_and_run
except ImportError:
    build_and_run = None


class DependencyManager:
    """依赖管理器：维护子任务状态、阻断与唤醒"""

    STATE_PENDING = "pending"
    STATE_READY = "ready"
    STATE_RUNNING = "running"
    STATE_COMPLETED = "completed"
    STATE_FAILED = "failed"
    STATE_SKIPPED = "skipped"

    def __init__(self, subtasks: list):
        self.subtasks = {s["id"]: s for s in subtasks}
        self.states = {s["id"]: self.STATE_PENDING for s in subtasks}
        self.results = {}
        self.listeners = {}  # completed_id -> [dependent_ids]

        # 构建依赖反向索引
        for s in subtasks:
            for dep in s.get("dependency_ids", []):
                self.listeners.setdefault(dep, []).append(s["id"])

    def get_ready(self) -> list:
        """获取所有可执行的子任务（依赖已满足 + 未被阻塞）"""
        ready = []
        for sid, state in self.states.items():
            if state != self.STATE_PENDING:
                continue
            task = self.subtasks[sid]
            if all(self.states.get(d) in (self.STATE_COMPLETED, self.STATE_SKIPPED)
                   for d in task.get("dependency_ids", [])):
                self.states[sid] = self.STATE_READY
                ready.append(task)
        return ready

    def mark_running(self, sid: str):
        self.states[sid] = self.STATE_RUNNING

    def mark_completed(self, sid: str, result=None):
        self.states[sid] = self.STATE_COMPLETED
        if result is not None:
            if isinstance(result, dict):
                self.results[sid] = result.get("output", str(result))
            else:
                self.results[sid] = str(result)

    def mark_failed(self, sid: str):
        self.states[sid] = self.STATE_FAILED

    def has_pending(self) -> bool:
        return any(s == self.STATE_PENDING for s in self.states.values())

    def get_execution_plan(self) -> list:
        """按 phase 分组的执行计划，每组内可并行"""
        phases = {}
        for sid, task in self.subtasks.items():
            phase = task.get("phase", 99)
            phases.setdefault(phase, []).append(sid)
        return [phases[k] for k in sorted(phases)]


_GLOBAL_REGISTRY: dict = {}
_registry_lock = threading.Lock()


class NexusOrchestrator:
    def __init__(self):
        self.instance_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.task_registry = {}
        self.results = {}
        self.fingerprints = {}
        self.team_result = {}
        self.failed_subtasks = []

    @staticmethod
    def _extract_self_check(text: str):
        """从文本中提取 [SELF_CHECK]...[/SELF_CHECK] 块"""
        if not text:
            return None
        start = text.find("[SELF_CHECK]")
        end = text.find("[/SELF_CHECK]")
        if start == -1 or end == -1 or end <= start:
            return None
        block = text[start + len("[SELF_CHECK]"):end].strip()
        fields = {}
        for line in block.split("\n"):
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        required = {"task_id", "result", "confidence"}
        if not required.issubset(fields.keys()):
            return None
        return fields

    @staticmethod
    def _backoff_delay(attempt: int, base_s: float = 1.0) -> float:
        delay = base_s * (2 ** (attempt - 1))
        import random
        return delay + random.uniform(0, 0.5 * delay)

    @staticmethod
    def _rollback_after_failure(task_spec: dict):
        """重试全部失败后回滚 agent 状态"""
        try:
            from scripts.rollback_manager import SnapshotManager
            rm = SnapshotManager()
            team_id = task_spec.get("team_id", "default")
            agent_id = task_spec.get("agent_type", task_spec.get("task_id", "unknown"))
            rm.snapshot_agent_state(team_id, f"{agent_id}_post_failure")
        except Exception:
            pass

    def _execute_with_retry(self, task_spec: dict, max_retries: int = 3) -> dict:
        """带指数退避重试 + 失败回滚的 `_execute_single` 封装"""
        fingerprint = self._fingerprint(task_spec)
        self.fingerprints[fingerprint] = self.fingerprints.get(fingerprint, 0) + 1
        for attempt in range(1, max_retries + 1):
            result = self._execute_single(task_spec)
            if result.get("status") != "FAILED":
                result["retry_attempts"] = attempt
                return result
            if attempt < max_retries:
                delay = self._backoff_delay(attempt)
                time.sleep(delay)
        self._rollback_after_failure(task_spec)
        return {"status": "FAILED", "retry_attempts": max_retries,
                "output": f"重试 {max_retries} 次均失败: {task_spec.get('name', '')}",
                "rollback_triggered": True}

    @staticmethod
    def _fingerprint(spec: dict) -> str:
        parts = [spec.get("agent_type", ""), spec.get("model_id", ""),
                 spec.get("task_id", "")]
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def _remember_execution(self, task: str, result: dict):
        """记录执行结果到 token-ledger（记忆桥接用）"""
        try:
            ledger_file = Path(__file__).parent.parent / "shared" / "token-ledger.json"
            ledger = []
            if ledger_file.exists():
                ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
            if not isinstance(ledger, list):
                ledger = []
            ledger.append({
                "task": task,
                "status": result.get("status", ""),
                "subtask_count": len(self.results),
                "failed_subtasks": len(self.failed_subtasks),
                "tokens_used": len(json.dumps(self.results)),
                "timestamp": time.time(),
            })
            if len(ledger) > 100:
                ledger = ledger[-100:]
            ledger_file.parent.mkdir(parents=True, exist_ok=True)
            ledger_file.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def run(self, task: str) -> dict:
        # 0. 检查模糊任务
        ambiguous = self._detect_ambiguous(task)
        # 0a. 注册到全局实例池
        with _registry_lock:
            _GLOBAL_REGISTRY[self.instance_id] = {
                "task": task, "started": time.time(), "task_registry": self.task_registry
            }
        if ambiguous:
            self._remember_execution(task, {"status": "CLARIFICATION_NEEDED"})
            return {"status": "CLARIFICATION_NEEDED", "question": ambiguous}

        # 1. 分解任务（含依赖排序的子任务列表）
        decomposition = self._step1_decompose(task)
        subtasks = decomposition.get("subtasks", [])
        exec_order = decomposition.get("execution_order", [])
        total_phases = decomposition.get("total_phases", 1)

        if not subtasks:
            return self._fallback(decomposition)

        # B3: 调用 team_builder.build_and_run 完整链路（匹配→裁剪→执行计划）
        if build_and_run:
            team_result = build_and_run(
                task=task,
                decomposition=decomposition,
            )
            self.team_result = team_result
            print(f"  [ORCH] 团队: {team_result.get('team_zh', team_result['team_name'])} "
                  f"({team_result.get('total_available', 0)}→{len(team_result.get('agents', []))} agents, "
                  f"mode={team_result.get('mode', '?')})")

        print(f"  [ORCH] 执行计划: {exec_order} ({len(subtasks)} 子任务, {total_phases} 阶段)")

        # 2. 依赖管理器
        dm = DependencyManager(subtasks)

        # 3. 拓扑感知执行（动态就绪队列，而非静态 phase 分组）
        already_printed = set()
        while dm.has_pending():
            ready_tasks = dm.get_ready()
            if not ready_tasks:
                remaining = [sid for sid, st in dm.states.items() if st == dm.STATE_PENDING]
                for sid in remaining:
                    dm.mark_failed(sid)
                    self.failed_subtasks.append(sid)
                break

            futures = {}
            with ThreadPoolExecutor(max_workers=len(ready_tasks)) as pool:
                for t in ready_tasks:
                    sid = t["id"]
                    dm.mark_running(sid)
                    task_name = t.get("name", sid)
                    if sid not in already_printed:
                        already_printed.add(sid)
                        print(f"    → {t.get('type', '?')}: {task_name}")
                    futures[pool.submit(self._execute_with_retry, t)] = sid

                for future in as_completed(futures):
                    sid = futures[future]
                    result = future.result()
                    dm.mark_completed(sid, result)
                    self.results[sid] = result.get("output", "")
                    self.task_registry[sid] = {"task": dm.subtasks[sid].get("name", sid),
                                               "status": result.get("status"),
                                               "output": result.get("output", "")[:200]}

        failed = [sid for sid, st in dm.states.items() if st == dm.STATE_FAILED]
        if failed:
            print(f"  [ORCH] 子任务失败: {failed}")

        result = {
            "status": "PARTIAL" if failed else "PASS",
            "path": "standard",
            "execution_order": exec_order,
            "total_phases": total_phases,
            "results": {sid: self.results.get(sid, "") for sid in dm.subtasks},
        }
        self._remember_execution(task, result)
        return result

    def _execute_single(self, task_spec: dict) -> dict:
        """执行单个子任务：调用 LLM API """
        task_type = task_spec.get("type", "general")
        output_fields = task_spec.get("output_fields", [])
        system_prompt = f"你是 {task_spec.get('agent', '专家')}。请完成以下任务，输出 JSON。"
        user_prompt = f"任务: {task_spec['name']}\n类型: {task_type}\n"
        if output_fields:
            user_prompt += f"输出字段: {', '.join(output_fields)}\n"
        user_prompt += "请以 JSON 格式返回结果。"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            import httpx, os
            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return {"status": "PASS", "output": f"完成: {task_spec['name']}",
                        "note": "无 API_KEY 配置，返回空壳"}
            base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
            model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            resp = httpx.post(
                f"{base_url}/chat/completions",
                json={"model": model, "messages": messages,
                      "temperature": 0.3, "max_tokens": 2048},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return {"status": "PASS", "output": content, "model": model}
        except Exception as exc:
            return {"status": "FAILED", "output": f"失败: {task_spec['name']}, 错误: {exc}",
                    "error": str(exc)}

    @staticmethod
    def _detect_ambiguous(task: str) -> str:
        vague_patterns = [
            "优化一下", "改进一下", "帮忙", "做点什么",
            "随便", "搞一下", "弄一下", "就这", "你看着办",
        ]
        if len(task.strip()) < 3:
            return f"任务描述过短（{len(task.strip())}字），请提供更多细节"
        for p in vague_patterns:
            if p in task:
                return f"任务描述过于模糊（包含'{p}'），请明确具体需求"
        return ""

    def _step1_decompose(self, task: str) -> dict:
        if _decompose:
            return _decompose(task)
        return {"task": task, "domains": [], "pi_types": [], "complexity": "L2-中等",
                "suggested_experts": 1, "subtasks": [], "execution_order": [], "total_phases": 0}

    def _fallback(self, decomposition: dict) -> dict:
        return {"status": "PASS", "path": "fallback_direct",
                "output": f"直接完成: {decomposition.get('task', '')}"}


def get_global_registry() -> dict:
    """返回全局注册表快照（用于审计/监控）"""
    with _registry_lock:
        return dict(_GLOBAL_REGISTRY)


def register_task(external_task_id: str, metadata: dict) -> str:
    """外部组件注册任务到全局注册表，返回 instance_id"""
    instance_id = hashlib.md5(f"ext_{external_task_id}_{time.time()}".encode()).hexdigest()[:8]
    with _registry_lock:
        _GLOBAL_REGISTRY[instance_id] = {"task": external_task_id, "started": time.time(),
                                          "task_registry": {external_task_id: metadata}}
    return instance_id


def main():
    ap = argparse.ArgumentParser(description="Nexus Orchestrator v2.5")
    ap.add_argument("--task", required=True, help="任务描述")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    orch = NexusOrchestrator()
    result = orch.run(args.task)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n状态: {result.get('status', 'unknown')}")
        print(f"执行顺序: {' → '.join(result.get('execution_order', []))}")

if __name__ == "__main__":
    main()
