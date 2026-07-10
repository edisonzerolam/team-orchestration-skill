"""测试 score_collector.py — 五维专家评分卡"""
from pathlib import Path
import json
import importlib.util

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
spec = importlib.util.spec_from_file_location("sc",
    str(SKILL_DIR / "scripts" / "score_collector.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

TEST_EXPERT = "_test_expert_score"


def setup_module():
    sc.SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    sc.SCORES_FILE.write_text("{}", encoding="utf-8")


def teardown_module():
    data = sc._load()
    if TEST_EXPERT in data:
        del data[TEST_EXPERT]
    sc._save(data)


class TestRecordScore:
    def test_record_single_dimension(self):
        result = sc.record_score(TEST_EXPERT, "delivery_quality", 8)
        assert result["dimension"] == "delivery_quality"
        assert result["recorded_value"] == 0.8
        assert 0 < result["new_avg"] <= 1.0
        assert result["total_count"] == 1

    def test_record_normalizes_correctly(self):
        result = sc.record_score(TEST_EXPERT, "task_completion", 10)
        assert result["recorded_value"] == 1.0

        result = sc.record_score(TEST_EXPERT, "task_completion", 0)
        assert result["recorded_value"] == 0.0

    def test_clamps_out_of_range(self):
        result = sc.record_score(TEST_EXPERT, "response_time", 15)
        assert result["recorded_value"] == 1.0

        result = sc.record_score(TEST_EXPERT, "response_time", -5)
        assert result["recorded_value"] == 0.0

    def test_unknown_dimension_raises(self):
        try:
            sc.record_score(TEST_EXPERT, "nonexistent", 5)
            assert False, "should have raised"
        except ValueError:
            pass


class TestRecordBatch:
    def test_batch_all_dimensions(self):
        result = sc.record_batch(TEST_EXPERT, {
            "task_completion": 9,
            "delivery_quality": 7,
            "response_time": 6,
            "user_feedback": 8,
            "collaboration": 7,
        })
        assert len(result["results"]) == 5
        for dim in sc.DIMENSIONS:
            assert dim in result["results"]

    def test_batch_partial_dimensions(self):
        result = sc.record_batch(TEST_EXPERT, {
            "delivery_quality": 5,
            "user_feedback": 6,
        })
        assert len(result["results"]) == 2


class TestAggregateComputation:
    def test_aggregate_after_single_dim(self):
        sc.SCORES_FILE.write_text("{}", encoding="utf-8")
        sc.record_score(TEST_EXPERT, "delivery_quality", 8)
        profile = sc.get_profile(TEST_EXPERT)
        # single dim at 0.8 → aggregate = 0.8
        assert profile["score"] == 0.8

    def test_aggregate_averages_multi_dim(self):
        sc.SCORES_FILE.write_text("{}", encoding="utf-8")
        sc.record_batch(TEST_EXPERT, {
            "task_completion": 10,
            "delivery_quality": 0,
        })
        profile = sc.get_profile(TEST_EXPERT)
        # avg of (1.0, 0.0) = 0.5
        assert profile["score"] == 0.5

    def test_cold_start_default_score(self):
        profile = sc.get_profile("nonexistent_expert_xyz")
        assert profile == {}


class TestGetDimensionAvg:
    def test_dim_avg_after_multiple_records(self):
        sc.SCORES_FILE.write_text("{}", encoding="utf-8")
        sc.record_score(TEST_EXPERT, "task_completion", 6)
        sc.record_score(TEST_EXPERT, "task_completion", 8)
        avg = sc.get_dimension_avg(TEST_EXPERT, "task_completion")
        # (0.6 + 0.8) / 2 = 0.7
        assert avg == 0.7

    def test_cold_dim_default(self):
        avg = sc.get_dimension_avg("nonexistent_expert_xyz", "collaboration")
        assert avg == 0.5


class TestGetAllScores:
    def test_get_all_scores(self):
        all_scores = sc.get_all_scores()
        assert isinstance(all_scores, dict)
        for name, info in all_scores.items():
            assert "score" in info
            assert "count" in info
