"""测试 template_cropper.py — 模板动态裁剪"""
import pytest
from scripts import template_cropper as tc


class TestCropTeam:
    def test_crop_large_investment_team(self):
        result = tc.crop_team("investment-masters-team", ["analysis_judgment"])
        assert result["total"] == 2
        assert result["cropped"] <= result["total"]
        assert result["cropped"] >= 1
        assert len(result["agents"]) == result["cropped"]

    def test_crop_trading_team(self):
        result = tc.crop_team("trading-agent", ["decision_execution", "analysis_judgment"])
        assert result["total"] == 1
        assert result["cropped"] <= result["total"]
        assert result["cropped"] >= 1

    def test_crop_small_team_skipped(self):
        result = tc.crop_team("rum-fullstack-team", ["analysis_judgment"])
        assert result["mode"] == "no_crop"
        assert result["total"] == 0

    def test_crop_legal_team(self):
        result = tc.crop_team("enterprise-legal-team", ["quality_verification"])
        assert result["total"] == 0
        assert result["mode"] == "no_crop"

    def test_crop_virtual_game_team(self):
        result = tc.crop_team("game-development", ["creation_generation"])
        assert result["total"] == 0
        assert result["mode"] == "no_crop"

    def test_crop_virtual_consulting_team(self):
        result = tc.crop_team("industry-consulting", ["analysis_judgment"])
        assert result["total"] == 0
        assert result["mode"] == "no_crop"

    def test_crop_unknown_team(self):
        result = tc.crop_team("nonexistent-team", ["analysis_judgment"])
        assert result["mode"] == "no_crop"
        assert result["total"] == 0

    def test_crop_empty_subtask_types(self):
        result = tc.crop_team("investment-masters-team", [])
        assert result["cropped"] <= result["total"]

    def test_crop_with_config_override(self):
        override = {
            "base_size": 3, "elastic_ratio": 0.0,
            "min_size": 1, "role_priority": ["risk-manager"],
        }
        result = tc.crop_team("investment-masters-team", ["analysis_judgment"],
                              config_override=override)
        assert result["cropped"] <= result["total"]

    def test_score_agent_function(self):
        agent = {"id": "risk-manager", "description": "manages risk assessment"}
        needed = {"risk", "manager"}
        score = tc._score_agent(agent, needed)
        assert score > 0

    def test_normalize_type_alias(self):
        result = tc._normalize_type("quality_validation")
        assert result == "quality_verification"

    def test_cropping_config_not_empty(self):
        config = tc._load_cropping_config()
        assert len(config) >= 8
