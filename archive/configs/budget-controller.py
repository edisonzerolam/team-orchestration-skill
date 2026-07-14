#!/usr/bin/env python3
"""BudgetController — Token 预算管理与自动降级

使用率 >= 85% 时自动降级到 economy 模式：
  - loaded_agents 只返回 metadata（不读 agent .md 原文）
  - 每个团最多加载 5 个 agent
"""
import json
from pathlib import Path
from dataclasses import dataclass

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
BUDGET_CONFIG_PATH = SKILL_DIR / "shared" / "budget-config.json"
TOKEN_BUDGET_PATH = SKILL_DIR / "shared" / "token-budget.json"
TOKEN_LEDGER_PATH = SKILL_DIR / "shared" / "token-ledger.json"


@dataclass
class BudgetVerdict:
    mode: str
    usage_pct: float
    max_agents_per_team: int
    load_agent_content: bool


class BudgetController:
    def __init__(self):
        self._config = None
        self._budget = None
        self._load()

    def _load(self):
        if BUDGET_CONFIG_PATH.exists():
            try:
                self._config = json.loads(BUDGET_CONFIG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._config = {}
        else:
            self._config = {"budget_type": "standard", "max_tokens_per_task": 32000,
                            "downgrade_threshold": 0.85, "economy_max_agents": 5,
                            "standby_mode": "metadata_only"}

        if TOKEN_BUDGET_PATH.exists():
            try:
                self._budget = json.loads(TOKEN_BUDGET_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._budget = {"total_budget": 100000, "used": 0, "history": []}
        else:
            self._budget = {"total_budget": 100000, "used": 0, "history": []}

    def _save_budget(self):
        from scripts.file_utils import atomic_write
        atomic_write(TOKEN_BUDGET_PATH, self._budget)

    def check_budget(self, team_name: str = None, agent_count: int = 0) -> BudgetVerdict:
        total = self._budget.get("total_budget", 100000)
        used = self._budget.get("used", 0)
        threshold = self._config.get("downgrade_threshold", 0.85)
        usage_pct = used / total if total > 0 else 0

        if usage_pct >= threshold:
            economy_max = self._config.get("economy_max_agents", 5)
            return BudgetVerdict(
                mode="economy",
                usage_pct=round(usage_pct * 100, 1),
                max_agents_per_team=economy_max,
                load_agent_content=agent_count <= economy_max,
            )
        return BudgetVerdict(
            mode="standard",
            usage_pct=round(usage_pct * 100, 1),
            max_agents_per_team=999,
            load_agent_content=True,
        )

    def record_usage(self, tokens: int, task_id: str = None):
        self._budget["used"] += tokens
        entry = {"tokens": tokens, "task_id": task_id}
        history = self._budget.get("history", [])
        history.append(entry)
        self._budget["history"] = history[-100:]  # 保留最近 100 条
        self._save_budget()

    @property
    def usage_pct(self) -> float:
        total = self._budget.get("total_budget", 100000)
        used = self._budget.get("used", 0)
        return round(used / total * 100, 1) if total > 0 else 0


class TokenAccount:
    """Token 记账 — 记录每次执行的 token 消耗"""

    @staticmethod
    def record(tokens: int, team_name: str = None, task_type: str = None, phase: str = None):
        ledger = {"version": "1.0", "entries": [], "total_tokens_used": 0, "total_calls": 0}
        if TOKEN_LEDGER_PATH.exists():
            try:
                ledger = json.loads(TOKEN_LEDGER_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        import time
        entry = {"timestamp": time.time(), "tokens": tokens, "team": team_name, "type": task_type, "phase": phase}
        ledger["entries"].append(entry)
        ledger["total_tokens_used"] = ledger.get("total_tokens_used", 0) + tokens
        ledger["total_calls"] = ledger.get("total_calls", 0) + 1
        from scripts.file_utils import atomic_write
        atomic_write(TOKEN_LEDGER_PATH, ledger)

    @staticmethod
    def summary() -> dict:
        if not TOKEN_LEDGER_PATH.exists():
            return {"entries": 0, "total_tokens": 0}
        try:
            return json.loads(TOKEN_LEDGER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"entries": 0, "total_tokens": 0}


if __name__ == "__main__":
    ctrl = BudgetController()
    verdict = ctrl.check_budget()
    print("模式:", verdict.mode)
    print("使用率:", verdict.usage_pct, "%")
    print("最大agent/团:", verdict.max_agents_per_team)
    print("加载内容:", verdict.load_agent_content)
