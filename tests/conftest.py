"""conftest.py — 全局 test fixtures 配置"""
import sys
from pathlib import Path

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import pytest

from scripts.score_collector import SCORES_FILE as _SCORES_FILE

# D1: 三阶加载测试数据 — 分 light（无 agent_names/capabilities）和 full（含额外字段）
MOCK_TEAMS_LIGHT = {
    "investment-masters-team": {
        "name": "investment-masters-team",
        "display_zh": "投资大师团队",
        "description_zh": "投资分析与研究",
        "category_id": "08-FinanceInvestment",
        "expert_type": "team",
        "lead_name": "贺知衡",
        "agent_count": 22,
    },
    "trading-agent": {
        "name": "trading-agent",
        "display_zh": "交易决策团队",
        "description_zh": "交易决策支持",
        "category_id": "08-FinanceInvestment",
        "expert_type": "team",
        "lead_name": "何执舟",
        "agent_count": 13,
    },
    "a-share-analysis": {
        "name": "a-share-analysis",
        "display_zh": "A股研究团队",
        "description_zh": "A股深度研究",
        "category_id": "08-FinanceInvestment",
        "expert_type": "team",
        "lead_name": "古见远",
        "agent_count": 8,
    },
    "content-creator-team": {
        "name": "content-creator-team",
        "display_zh": "内容创作团队",
        "description_zh": "AI内容与创意生产",
        "category_id": "06-ContentCreative",
        "expert_type": "team",
        "lead_name": "司远",
        "agent_count": 5,
    },
}

# 各团 agents 数量 — 保持与旧测试期望一致
_MOCK_AGENTS = {
    "investment-masters-team": [
        {"id": "risk-manager", "description": "risk manager", "role": "risk-manager"},
        {"id": "market-strategist", "description": "market strategist", "role": "market-strategist"},
    ],
    "trading-agent": [
        {"id": "trader", "description": "trader", "role": "trader"},
    ],
    "a-share-analysis": [
        {"id": "analyst", "description": "analyst", "role": "analyst"},
        {"id": "researcher", "description": "researcher", "role": "researcher"},
    ],
    "content-creator-team": [
        {"id": "writer", "description": "content writer", "role": "writer"},
        {"id": "editor", "description": "editor", "role": "editor"},
    ],
}

MOCK_TEAMS_FULL = {}
for k, v in MOCK_TEAMS_LIGHT.items():
    agents = _MOCK_AGENTS.get(k, [])
    MOCK_TEAMS_FULL[k] = {
        **v,
        "agent_names": [a["id"] for a in agents],
        "capabilities": [a["description"] for a in agents] + ["analysis", "research"],
        "agents": agents,
    }


@pytest.fixture(autouse=True)
def _auto_mocks(monkeypatch):
    """全局自动 mock 文件 I/O 密集型函数"""
    monkeypatch.setattr("scripts.expert_matcher.load_all_experts", lambda: {k: dict(v) for k, v in MOCK_TEAMS_FULL.items()})
    monkeypatch.setattr("scripts.expert_matcher.load_experts_light", lambda: {k: dict(v) for k, v in MOCK_TEAMS_LIGHT.items()})
    monkeypatch.setattr("scripts.expert_matcher.load_experts_detail",
                        lambda team_names: {n: dict(MOCK_TEAMS_FULL[n]) for n in team_names if n in MOCK_TEAMS_FULL})
    monkeypatch.setattr("scripts.expert_matcher.load_performance_scores", lambda: {})
    monkeypatch.setattr("scripts.template_cropper._get_agents_for_team",
                        lambda team_name, base_dir=None: list(MOCK_TEAMS_FULL.get(team_name, {}).get("agents", [])))
    monkeypatch.setattr("scripts.score_collector.SCORES_FILE",
                        _SCORES_FILE.with_suffix(".test.json"))
