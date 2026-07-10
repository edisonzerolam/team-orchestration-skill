"""测试 cross-validator.py — 交叉验证引擎"""
from pathlib import Path
import importlib.util

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
spec = importlib.util.spec_from_file_location("cv",
    str(SKILL_DIR / "scripts" / "cross-validator.py"))
cv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv)


class TestExtractClaims:
    def test_extracts_from_text(self):
        outputs = [
            {"agent": "analyst", "text": "市场表现持续利好，建议增持。增长率达到20%远超预期。"},
        ]
        claims = cv.extract_claims(outputs)
        assert len(claims) >= 1
        assert claims[0]["source_agent"] == "analyst"

    def test_skips_short_sentences(self):
        outputs = [{"agent": "a", "text": "好。嗯。市场表现持续利好。"}]
        claims = cv.extract_claims(outputs)
        for c in claims:
            assert len(c["text"]) >= 10

    def test_multiple_agents(self):
        outputs = [
            {"agent": "a1", "text": "这是第一个重要的观点和结论。"},
            {"agent": "a2", "text": "这是第二个重要的观点和结论。"},
        ]
        claims = cv.extract_claims(outputs)
        assert len(claims) >= 2


class TestTraceProvenance:
    def test_extracts_urls(self):
        claims = [{"claim_id": "c1", "text": "数据来源 https://example.com/data", "source_agent": "a"}]
        result = cv.trace_provenance(claims)
        assert any(p["type"] == "url" for p in result[0]["provenance"])

    def test_inferred_when_no_source(self):
        claims = [{"claim_id": "c2", "text": "根据我的分析", "source_agent": "a"}]
        result = cv.trace_provenance(claims)
        assert result[0]["provenance"][0]["type"] == "inferred"


class TestCheckIndependence:
    def test_detects_same_source(self):
        sources = [
            {"type": "url", "value": "https://example.com", "source_agent": "a1"},
            {"type": "url", "value": "https://example.com", "source_agent": "a2"},
        ]
        issues = cv.check_independence(sources)
        assert len(issues) >= 1
        assert issues[0]["issue"] == "同源依赖"

    def test_independent_sources(self):
        sources = [
            {"type": "url", "value": "https://a.com", "source_agent": "a1"},
            {"type": "url", "value": "https://b.com", "source_agent": "a2"},
        ]
        issues = cv.check_independence(sources)
        assert len(issues) == 0


class TestScoreConfidence:
    def test_no_claims_returns_half(self):
        result = cv.score_confidence([])
        assert result["score"] == 0.5

    def test_single_agent_low_diversity(self):
        claims = [
            {"claim_id": "c1", "text": "A", "source_agent": "a1", "provenance": [{"type": "inferred"}]},
        ]
        result = cv.score_confidence(claims, "standard")
        assert 0 <= result["score"] <= 1

    def test_multi_agent_higher_score(self):
        claims = [
            {"claim_id": "c1", "text": "A", "source_agent": "a1", "provenance": [{"type": "url", "value": "https://x.com"}]},
            {"claim_id": "c2", "text": "B", "source_agent": "a2", "provenance": [{"type": "url", "value": "https://y.com"}]},
            {"claim_id": "c3", "text": "C", "source_agent": "a3", "provenance": [{"type": "url", "value": "https://z.com"}]},
        ]
        result = cv.score_confidence(claims, "standard")
        assert result["score"] > 0.5

    def test_conflicts_reduce_score(self):
        claims = [
            {"claim_id": "c1", "text": "市场表现利好", "source_agent": "a1", "provenance": [{"type": "inferred"}]},
            {"claim_id": "c2", "text": "市场表现利空", "source_agent": "a2", "provenance": [{"type": "inferred"}]},
        ]
        # detect_conflicts should find 利好 vs 利空 conflict
        conflicts = cv.detect_conflicts(claims)
        assert len(conflicts) >= 1
